import sys
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional
import webbrowser
import threading

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QListWidget, QListWidgetItem,
    QLabel, QLineEdit, QPushButton, QMenu, QAction, QMessageBox,
    QDialog, QFormLayout, QComboBox, QSplitter, QStatusBar, QFileDialog, QTabWidget,
    QProgressDialog
)
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QIcon, QFont, QColor

from bookmark_extractor import Bookmark
from credential_manager import CredentialManager
from bookmark_storage import BookmarkStorage
from gui.keyword_browser import KeywordBrowserWidget
# Old keyword extraction (disabled)
# from keyword_batch_processor import batch_extract_keywords
from settings_manager import SettingsManager
from gui.settings_dialog import SettingsDialog

# New BERTopic batch modeling
# from topic_batch_processor import run_batch_topic_modeling

# Per-bookmark BERTopic modeling
from single_bookmark_modeling_worker import SingleBookmarkModelingWorker

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self, categorized_bookmarks: Dict[str, List[Bookmark]], cred_manager: CredentialManager):
        super().__init__()

        self.settings_manager = SettingsManager()

        self.categorized_bookmarks = categorized_bookmarks
        self.cred_manager = cred_manager
        self.current_category = None

        self.setWindowTitle("Browser Bookmark Aggregator")
        self.setMinimumSize(900, 600)

        # Bookmark storage
        self.storage = BookmarkStorage(Path.home() / ".bookmark_aggregator" / "bookmarks_processed.json")
        self.storage.load()
        # On first run, sync extracted bookmarks into storage
        if not self.storage.bookmarks:
            all_bookmarks = []
            for blist in categorized_bookmarks.values():
                all_bookmarks.extend(blist)
            self.storage.bookmarks = all_bookmarks
            self.storage.save()

        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Category/bookmark panel
        cat_panel = QWidget()
        cat_panel_layout = QHBoxLayout(cat_panel)

        # Splitter for category/bookmark view
        splitter = QSplitter(Qt.Horizontal)
        cat_panel_layout.addWidget(splitter)

        # Left panel - Category tree
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.category_search = QLineEdit()
        self.category_search.setPlaceholderText("Search categories...")
        self.category_search.textChanged.connect(self.filter_categories)
        left_layout.addWidget(self.category_search)

        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderLabel("Categories")
        self.category_tree.itemClicked.connect(self.category_selected)
        left_layout.addWidget(self.category_tree)

        self.populate_category_tree()

        # Right panel - Bookmarks list
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.bookmark_search = QLineEdit()
        self.bookmark_search.setPlaceholderText("Search bookmarks...")
        self.bookmark_search.textChanged.connect(self.filter_bookmarks)
        right_layout.addWidget(self.bookmark_search)

        self.bookmark_list = QListWidget()
        self.bookmark_list.setAlternatingRowColors(True)
        self.bookmark_list.itemDoubleClicked.connect(self.open_bookmark)
        self.bookmark_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.bookmark_list.customContextMenuRequested.connect(self.show_bookmark_context_menu)
        right_layout.addWidget(self.bookmark_list)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([200, 700])

        cat_panel.setLayout(cat_panel_layout)
        self.tabs.addTab(cat_panel, "Categories")

        # Keyword browser tab (will show derived keywords from top topic)
        self.keyword_browser = KeywordBrowserWidget(self.storage.get_all())
        self.tabs.addTab(self.keyword_browser, "Keywords")

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.update_status_bar()

        # Menu bar
        self.create_menu_bar()

    def create_menu_bar(self):
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("File")
        export_action = QAction("Export Bookmarks...", self)
        export_action.triggered.connect(self.export_bookmarks)
        file_menu.addAction(export_action)
        import_action = QAction("Import Bookmarks...", self)
        import_action.triggered.connect(self.import_bookmarks)
        file_menu.addAction(import_action)
        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu
        tools_menu = menu_bar.addMenu("Tools")
        validate_action = QAction("Validate All Links", self)
        validate_action.triggered.connect(self.validate_all_links)
        tools_menu.addAction(validate_action)
        recategorize_action = QAction("Recategorize All Bookmarks", self)
        recategorize_action.triggered.connect(self.recategorize_all_bookmarks)
        tools_menu.addAction(recategorize_action)

        # Global (batch) topic modeling
        topic_action = QAction("Build Topics (BERTopic)", self)
        topic_action.triggered.connect(self.build_topics_batch)
        tools_menu.addAction(topic_action)

        # Per-bookmark topic modeling
        single_topic_action = QAction("Build Per-Bookmark Topics (BERTopic)", self)
        single_topic_action.triggered.connect(self.build_single_topics)
        tools_menu.addAction(single_topic_action)

        # Help menu
        help_menu = menu_bar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

        # Settings Menu
        settings_menu = self.menuBar().addMenu("Settings")
        api_key_action = QAction("Set OpenAI API Key", self)
        api_key_action.triggered.connect(self.show_settings_dialog)
        settings_menu.addAction(api_key_action)

    def populate_category_tree(self):
        self.category_tree.clear()
        for category, bookmarks in self.categorized_bookmarks.items():
            if not bookmarks:
                continue
            item = QTreeWidgetItem(self.category_tree)
            item.setText(0, f"{category} ({len(bookmarks)})")
            item.setData(0, Qt.UserRole, category)
            font = item.font(0)
            font.setBold(True)
            item.setFont(0, font)
            browsers = {}
            for bookmark in bookmarks:
                if bookmark.browser_source not in browsers:
                    browsers[bookmark.browser_source] = 0
                browsers[bookmark.browser_source] += 1
            for browser, count in browsers.items():
                browser_item = QTreeWidgetItem(item)
                browser_item.setText(0, f"{browser} ({count})")
                browser_item.setData(0, Qt.UserRole, f"{category}|{browser}")
        self.category_tree.expandAll()

    def category_selected(self, item):
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        if "|" in data:
            category, browser = data.split("|")
            self.current_category = category
            self.populate_bookmark_list(category, browser)
        else:
            self.current_category = data
            self.populate_bookmark_list(data)

    def populate_bookmark_list(self, category, browser=None):
        self.bookmark_list.clear()
        bookmarks = self.categorized_bookmarks[category]
        if browser:
            bookmarks = [b for b in bookmarks if b.browser_source == browser]
        for bookmark in bookmarks:
            item = QListWidgetItem()
            item.setText(bookmark.title or bookmark.url)
            item.setToolTip(
                f"{bookmark.url}\nSource: {bookmark.browser_source}\nFolder: {bookmark.folder_path}"
            )
            item.setData(Qt.UserRole, bookmark)
            if not bookmark.is_valid:
                item.setForeground(QColor("red"))
            self.bookmark_list.addItem(item)
        self.status_bar.showMessage(f"Showing {self.bookmark_list.count()} bookmarks")

    def filter_categories(self):
        search_text = self.category_search.text().lower()
        for i in range(self.category_tree.topLevelItemCount()):
            item = self.category_tree.topLevelItem(i)
            category = item.data(0, Qt.UserRole)
            if not search_text or search_text in category.lower():
                item.setHidden(False)
                for j in range(item.childCount()):
                    item.child(j).setHidden(False)
            else:
                child_match = False
                for j in range(item.childCount()):
                    child = item.child(j)
                    browser = child.text(0).split(" (")[0].lower()
                    if search_text in browser:
                        child.setHidden(False)
                        child_match = True
                    else:
                        child.setHidden(True)
                item.setHidden(not child_match)

    def filter_bookmarks(self):
        search_text = self.bookmark_search.text().lower()
        for i in range(self.bookmark_list.count()):
            item = self.bookmark_list.item(i)
            bookmark = item.data(Qt.UserRole)
            match = (
                not search_text or
                (bookmark.title and search_text in bookmark.title.lower()) or
                search_text in bookmark.url.lower()
            )
            item.setHidden(not match)
        visible_count = sum(
            1 for i in range(self.bookmark_list.count()) if not self.bookmark_list.item(i).isHidden()
        )
        self.status_bar.showMessage(f"Showing {visible_count} of {self.bookmark_list.count()} bookmarks")

    def open_bookmark(self, item):
        bookmark = item.data(Qt.UserRole)
        webbrowser.open(bookmark.url)

    def show_bookmark_context_menu(self, position):
        item = self.bookmark_list.itemAt(position)
        if not item:
            return
        bookmark = item.data(Qt.UserRole)
        menu = QMenu()
        open_action = QAction("Open in Browser", self)
        open_action.triggered.connect(lambda: self.open_bookmark(item))
        menu.addAction(open_action)
        copy_action = QAction("Copy URL", self)
        copy_action.triggered.connect(lambda: QApplication.clipboard().setText(bookmark.url))
        menu.addAction(copy_action)
        menu.addSeparator()
        recategorize_action = QAction("Recategorize", self)
        recategorize_action.triggered.connect(lambda: self.recategorize_bookmark(bookmark))
        menu.addAction(recategorize_action)
        check_action = QAction("Check Link", self)
        check_action.triggered.connect(lambda: self.validate_bookmark(bookmark, item))
        menu.addAction(check_action)
        reprocess_action = QAction("Mark for Topic Rebuild", self)
        reprocess_action.triggered.connect(lambda: self.reprocess_keywords_for_bookmark(bookmark))
        menu.addAction(reprocess_action)
        menu.exec_(self.bookmark_list.mapToGlobal(position))

    def recategorize_bookmark(self, bookmark):
        dialog = QDialog(self)
        dialog.setWindowTitle("Recategorize Bookmark")
        from PyQt5.QtWidgets import QFormLayout, QComboBox
        layout = QFormLayout(dialog)
        title_label = QLabel(bookmark.title)
        layout.addRow("Title:", title_label)
        url_label = QLabel(bookmark.url)
        url_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addRow("URL:", url_label)
        category_combo = QComboBox()
        for category in self.categorized_bookmarks.keys():
            category_combo.addItem(category)
        current_index = category_combo.findText(bookmark.category)
        if current_index >= 0:
            category_combo.setCurrentIndex(current_index)
        layout.addRow("Category:", category_combo)
        button_layout = QHBoxLayout()
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        save_button = QPushButton("Save")
        save_button.clicked.connect(dialog.accept)
        save_button.setDefault(True)
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(save_button)
        layout.addRow("", button_layout)
        if dialog.exec_() == QDialog.Accepted:
            new_category = category_combo.currentText()
            if bookmark in self.categorized_bookmarks[bookmark.category]:
                self.categorized_bookmarks[bookmark.category].remove(bookmark)
            bookmark.category = new_category
            self.categorized_bookmarks[new_category].append(bookmark)
            self.populate_category_tree()
            if self.current_category:
                self.populate_bookmark_list(self.current_category)

    def validate_bookmark(self, bookmark, item):
        self.status_bar.showMessage(f"Validating link: {bookmark.url}...")
        def validate_thread():
            from link_validator import _validate_link
            is_valid = _validate_link(bookmark)
            bookmark.is_valid = is_valid
            if not is_valid:
                item.setForeground(QColor("red"))
            else:
                item.setForeground(QColor("black"))
            self.status_bar.showMessage(
                f"Link validation complete: {'Valid' if is_valid else 'Invalid'} - {bookmark.url}"
            )
        threading.Thread(target=validate_thread).start()

    def validate_all_links(self):
        reply = QMessageBox.question(
            self,
            "Validate Links",
            "This will check all visible bookmarks for dead links. It may take some time. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.status_bar.showMessage("Validating links... Please wait.")
            bookmarks_to_validate = []
            items_map = {}
            for i in range(self.bookmark_list.count()):
                item = self.bookmark_list.item(i)
                if not item.isHidden():
                    bookmark = item.data(Qt.UserRole)
                    bookmarks_to_validate.append(bookmark)
                    items_map[bookmark] = item
            def validate_thread():
                from link_validator import _validate_link
                valid_count = 0
                invalid_count = 0
                for i, bookmark in enumerate(bookmarks_to_validate):
                    is_valid = _validate_link(bookmark)
                    bookmark.is_valid = is_valid
                    if is_valid:
                        valid_count += 1
                    else:
                        invalid_count += 1
                    self.status_bar.showMessage(
                        f"Validating links... {i+1}/{len(bookmarks_to_validate)} complete"
                    )
                    item = items_map[bookmark]
                    if not is_valid:
                        item.setForeground(QColor("red"))
                    else:
                        item.setForeground(QColor("black"))
                self.status_bar.showMessage(
                    f"Link validation complete. {valid_count} valid, {invalid_count} invalid links."
                )
            threading.Thread(target=validate_thread).start()

    def recategorize_all_bookmarks(self):
        reply = QMessageBox.question(
            self,
            "Recategorize Bookmarks",
            "This will recategorize all bookmarks. Any manual categorization will be lost. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.status_bar.showMessage("Recategorizing bookmarks... Please wait.")
            def recategorize_thread():
                all_bookmarks = []
                for bookmarks in self.categorized_bookmarks.values():
                    all_bookmarks.extend(bookmarks)
                for category in self.categorized_bookmarks:
                    self.categorized_bookmarks[category] = []
                from bookmark_categorizer import categorize_bookmarks
                new_categorized = categorize_bookmarks(all_bookmarks)
                self.categorized_bookmarks = new_categorized
                self.populate_category_tree()
                if self.current_category and self.current_category in self.categorized_bookmarks:
                    self.populate_bookmark_list(self.current_category)
                self.status_bar.showMessage("Recategorization complete.")
            threading.Thread(target=recategorize_thread).start()

    def export_bookmarks(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Bookmarks",
            "",
            "HTML Files (*.html);;JSON Files (*.json);;CSV Files (*.csv)"
        )
        if not file_path:
            return
        self.status_bar.showMessage(f"Exporting bookmarks to {file_path}...")
        def export_thread():
            try:
                from bookmark_exporter import export_bookmarks
                all_bookmarks = []
                for category, bookmarks in self.categorized_bookmarks.items():
                    for bookmark in bookmarks:
                        all_bookmarks.append(bookmark)
                export_bookmarks(all_bookmarks, file_path)
                self.status_bar.showMessage(f"Bookmarks exported successfully to {file_path}")
            except Exception as e:
                self.status_bar.showMessage(f"Error exporting bookmarks: {e}")
                logger.error(f"Error exporting bookmarks: {e}")
        threading.Thread(target=export_thread).start()

    def import_bookmarks(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Bookmarks",
            "",
            "HTML Files (*.html);;JSON Files (*.json);;CSV Files (*.csv)"
        )
        if not file_path:
            return
        self.status_bar.showMessage(f"Importing bookmarks from {file_path}...")
        def import_thread():
            try:
                from bookmark_importer import import_bookmarks
                imported_bookmarks = import_bookmarks(file_path)
                from bookmark_categorizer import categorize_bookmarks
                imported_categorized = categorize_bookmarks(imported_bookmarks)
                for category, bookmarks in imported_categorized.items():
                    self.categorized_bookmarks[category].extend(bookmarks)
                self.storage.bookmarks.extend(imported_bookmarks)
                self.storage.save()
                self.populate_category_tree()
                if self.current_category:
                    self.populate_bookmark_list(self.current_category)
                self.keyword_browser.bookmarks = self.storage.get_all()
                self.keyword_browser.keyword_to_bookmarks = self.keyword_browser._compute_keyword_map()
                self.keyword_browser.keyword_list.clear()
                self.keyword_browser._populate_keywords()
                self.status_bar.showMessage(
                    f"Imported {len(imported_bookmarks)} bookmarks successfully from {file_path}"
                )
            except Exception as e:
                self.status_bar.showMessage(f"Error importing bookmarks: {e}")
                logger.error(f"Error importing bookmarks: {e}")
        threading.Thread(target=import_thread).start()

    def show_about_dialog(self):
        QMessageBox.about(
            self,
            "About Browser Bookmark Aggregator",
            "Browser Bookmark Aggregator v1.0\n\n"
            "A utility to aggregate bookmarks from multiple browsers, "
            "categorize them, and provide a unified interface for management.\n\n"
            "© 2025 All rights reserved."
        )

    def update_status_bar(self):
        total_bookmarks = sum(len(bookmarks) for bookmarks in self.categorized_bookmarks.values())
        self.status_bar.showMessage(f"Total bookmarks: {total_bookmarks}")

    # Replaced old OpenAI keyword extraction with BERTopic batch topic modeling
    def build_topics_batch(self):
        bookmarks_all = self.storage.get_all()
        if len(bookmarks_all) < 2:
            QMessageBox.information(
                self, "Insufficient Data",
                "Need at least 2 bookmarks to build topics."
            )
            return
        self.status_bar.showMessage(
            f"Building BERTopic model over {len(bookmarks_all)} bookmarks..."
        )

        def run_batch():
            try:
                cache_path = Path.home() / ".bookmark_aggregator" / "page_content_cache.json"
                run_batch_topic_modeling(
                    bookmarks_all,
                    save_path=str(self.storage.path),
                    content_cache_path=str(cache_path),
                    force_refetch=False,
                    fetch_limit=None,
                    max_words=3000,
                    polite_delay=0.25,
                    user_agent="BookmarkTopicBot/1.0",
                    top_n_per_doc=3,
                    min_topic_probability=0.02,
                    embedding_model="all-MiniLM-L6-v2",
                    nr_topics=None,
                    verbose=False,
                )
                self.storage.save()
                self.keyword_browser.bookmarks = self.storage.get_all()
                self.keyword_browser.keyword_to_bookmarks = self.keyword_browser._compute_keyword_map()
                self.keyword_browser.keyword_list.clear()
                self.keyword_browser._populate_keywords()
                self.status_bar.showMessage("Topic modeling complete.")
            except Exception as e:
                logger.exception("Error during topic modeling")
                self.status_bar.showMessage(f"Topic modeling error: {e}")

        threading.Thread(target=run_batch, daemon=True).start()

    # New: Per-bookmark BERTopic modeling
    def build_single_topics(self):
        bms = self.storage.get_all()
        if len(bms) == 0:
            QMessageBox.information(self, "No Bookmarks", "No bookmarks to process.")
            return

        cache_path = Path.home() / ".bookmark_aggregator" / "page_content_cache.json"
        self.progress_dialog = QProgressDialog("Preparing...", None, 0, 100, self)
        self.progress_dialog.setWindowTitle("Per-Bookmark Topics")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.setAutoReset(False)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.show()

        self.single_worker = SingleBookmarkModelingWorker(
            bookmarks=bms,
            save_path=str(self.storage.path),
            cache_path=str(cache_path),
            polite_delay=0.25,
            user_agent="BookmarkTopicBot/1.0",
            embedding_model="all-MiniLM-L6-v2",
            min_topic_size=2,
            top_n_words=10,
            save_every=20
        )
        self.single_worker.progress.connect(self._on_single_progress)
        self.single_worker.finished_success.connect(self._on_single_success)
        self.single_worker.failed.connect(self._on_single_failure)
        self.single_worker.start()

    def _on_single_progress(self, pct: int, label: str):
        if getattr(self, "progress_dialog", None):
            self.progress_dialog.setValue(pct)
            self.progress_dialog.setLabelText(label)
            if pct >= 100:
                QTimer.singleShot(400, self.progress_dialog.close)

    def _on_single_success(self, count: int):
        self.storage.load()
        self.keyword_browser.bookmarks = self.storage.get_all()
        self.keyword_browser.keyword_to_bookmarks = self.keyword_browser._compute_keyword_map()
        self.keyword_browser.keyword_list.clear()
        self.keyword_browser._populate_keywords()
        QMessageBox.information(self, "Done", f"Processed {count} bookmarks.")
        if getattr(self, "progress_dialog", None) and self.progress_dialog.value() < 100:
            self.progress_dialog.setValue(100)

    def _on_single_failure(self, message: str):
        if getattr(self, "progress_dialog", None):
            self.progress_dialog.close()
        QMessageBox.critical(self, "Error", message)

    def reprocess_keywords_for_bookmark(self, bookmark):
        self.storage.mark_for_reprocessing(bookmark)
        self.status_bar.showMessage(
            f"Bookmark '{bookmark.title}' marked for topic rebuild (run 'Build Per-Bookmark Topics')."
        )

    def show_settings_dialog(self):
        dlg = SettingsDialog(self.settings_manager, self)
        dlg.exec_()

def launch_gui(categorized_bookmarks, cred_manager):
    app = QApplication(sys.argv)
    window = MainWindow(categorized_bookmarks, cred_manager)
    window.show()
    sys.exit(app.exec_())