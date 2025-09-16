import sys
import logging
import webbrowser
import threading
from pathlib import Path
from typing import Dict, List

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QListWidget, QListWidgetItem,
    QLabel, QLineEdit, QPushButton, QMenu, QAction, QMessageBox,
    QDialog, QFormLayout, QComboBox, QSplitter, QStatusBar, QFileDialog, QTabWidget,
    QProgressDialog, QInputDialog
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor

from bookmark_extractor import Bookmark, extract_bookmarks
from browser_detector import detect_browsers
from bookmark_categorizer import categorize_bookmarks
from credential_manager import CredentialManager
from bookmark_storage import BookmarkStorage
from gui.keyword_browser import KeywordBrowserWidget
from settings_manager import SettingsManager
from gui.settings_dialog import SettingsDialog

# New per-bookmark analysis (pluggable analyzers)
from workers.analysis_worker import AnalysisWorker
from analyzers.registry import list_analyzer_names
from config.analyzers_config import load_config
from gui.analyzer_settings_dialog import AnalyzerSettingsDialog

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self, categorized_bookmarks: Dict[str, List[Bookmark]], 
                 cred_manager: CredentialManager):
        super().__init__()

        self.settings_manager = SettingsManager()
        self.categorized_bookmarks = categorized_bookmarks
        self.cred_manager = cred_manager
        self.current_category = None

        self.setWindowTitle("Browser Bookmark Aggregator")
        self.setMinimumSize(900, 600)

        # Bookmark storage
        storage_path = Path.home() / ".bookmark_aggregator" / "bookmarks_processed.json"
        self.storage = BookmarkStorage(storage_path)
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

        # Keyword browser tab (shows derived keywords)
        self.keyword_browser = KeywordBrowserWidget(parent=self, bookmarks=self.storage.get_all())
        # self.keyword_browser = KeywordBrowserWidget(self.storage.get_all())
        self.tabs.addTab(self.keyword_browser, "Keywords")

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.update_status_bar()

        # Menu bar
        self.create_menu_bar()

    # ------------------------- Menu -------------------------

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
        extract_action = QAction("Extract Bookmarks...", self)
        extract_action.triggered.connect(self.extract_bookmarks_from_browsers)
        tools_menu.addAction(extract_action)
        tools_menu.addSeparator()
        validate_action = QAction("Validate All Links", self)
        validate_action.triggered.connect(self.validate_all_links)
        tools_menu.addAction(validate_action)
        recategorize_action = QAction("Recategorize All Bookmarks", self)
        recategorize_action.triggered.connect(self.recategorize_all_bookmarks)
        tools_menu.addAction(recategorize_action)

        # Per-bookmark analysis (pluggable analyzers)
        analyze_action = QAction("Analyze Bookmarks…", self)
        analyze_action.triggered.connect(self.run_analysis)
        tools_menu.addAction(analyze_action)

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

        analyzer_settings_action = QAction("Analyzer Settings…", self)
        analyzer_settings_action.triggered.connect(self.show_analyzer_settings_dialog)
        settings_menu.addAction(analyzer_settings_action)

    # ------------------------- Category / Bookmarks UI -------------------------

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
            # Per-browser counts
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
            category, browser = data.split("|", 1)
            self.current_category = category
            self.populate_bookmark_list(category, browser)
        else:
            self.current_category = data
            self.populate_bookmark_list(data)

    def populate_bookmark_list(self, category, browser=None):
        self.bookmark_list.clear()
        bookmarks = self.categorized_bookmarks.get(category, [])
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
        search_text = self.category_search.text().lower().strip()
        for i in range(self.category_tree.topLevelItemCount()):
            item = self.category_tree.topLevelItem(i)
            category = item.data(0, Qt.UserRole)
            if not category:
                continue
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
        search_text = self.bookmark_search.text().lower().strip()
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
            1 for i in range(self.bookmark_list.count()) 
            if not self.bookmark_list.item(i).isHidden()
        )
        self.status_bar.showMessage(
            f"Showing {visible_count} of {self.bookmark_list.count()} bookmarks"
        )

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

    # ------------------------- Actions -------------------------

    def extract_bookmarks_from_browsers(self):
        """Extract bookmarks from all detected browsers with GUI prompts"""
        try:
            # Step 1: Get master password for credential manager
            if not self.cred_manager.initialized:
                master_password, ok = QInputDialog.getText(
                    self,
                    "Master Password",
                    "Enter master password (or press OK to create one):",
                    QLineEdit.Password
                )
                if not ok:
                    return

                if not self.cred_manager.initialize(master_password):
                    QMessageBox.critical(self, "Error", 
                                       "Failed to initialize credential manager.")
                    return
            
            # Step 2: Detect installed browsers
            self.status_bar.showMessage("Detecting installed browsers...")
            installed_browsers = detect_browsers()

            if not installed_browsers:
                QMessageBox.information(self, "No Browsers", 
                                      "No supported browsers found on this system.")
                return

            logger.info(f"Found {len(installed_browsers)} browser installations")
            
            # Step 3: Prompt for missing credentials
            for browser in installed_browsers:
                if (browser.requires_credentials and 
                    not self.cred_manager.has_credentials(browser.id)):
                    username, ok = QInputDialog.getText(
                        self,
                        "Browser Credentials",
                        f"Enter username for {browser.name}:"
                    )
                    if not ok:
                        continue

                    password, ok = QInputDialog.getText(
                        self,
                        "Browser Credentials",
                        f"Enter password for {browser.name}:",
                        QLineEdit.Password
                    )
                    if not ok:
                        continue

                    self.cred_manager.store_credentials(browser.id, username, password)
            
            # Step 4: Show progress dialog and extract in background thread
            progress_range = len(installed_browsers)
            self.progress_dialog = QProgressDialog("Extracting bookmarks...", "Cancel", 
                                                  0, progress_range, self)
            self.progress_dialog.setWindowTitle("Extracting Bookmarks")
            self.progress_dialog.setWindowModality(Qt.WindowModal)
            self.progress_dialog.setAutoClose(False)
            self.progress_dialog.setAutoReset(False)
            self.progress_dialog.setMinimumDuration(0)
            self.progress_dialog.show()
            
            # Extract bookmarks in background thread
            def extraction_thread():
                all_bookmarks = []
                try:
                    for i, browser in enumerate(installed_browsers):
                        if self.progress_dialog.wasCanceled():
                            break

                        QTimer.singleShot(
                            0, 
                            lambda b=browser, idx=i: self._update_extraction_progress(
                                idx, f"Extracting from {b.name}..."
                            )
                        )

                        logger.info(f"Extracting bookmarks from {browser.name} {browser.version}")
                        credentials = (self.cred_manager.get_credentials(browser.id) 
                                     if browser.requires_credentials else None)
                        bookmarks = extract_bookmarks(browser, credentials)
                        all_bookmarks.extend(bookmarks)

                        QTimer.singleShot(
                            0, 
                            lambda idx=i+1: self._update_extraction_progress(
                                idx, f"Extracted {len(all_bookmarks)} bookmarks..."
                            )
                        )
                    
                    if not self.progress_dialog.wasCanceled() and all_bookmarks:
                        # Step 5: Categorize bookmarks
                        QTimer.singleShot(
                            0, 
                            lambda: self._update_extraction_progress(
                                len(installed_browsers), "Categorizing bookmarks..."
                            )
                        )
                        logger.info("Categorizing bookmarks...")
                        categorized_bookmarks = categorize_bookmarks(all_bookmarks)

                        # Step 6: Update storage and UI on main thread
                        QTimer.singleShot(
                            0, 
                            lambda: self._finish_extraction(categorized_bookmarks, all_bookmarks)
                        )
                    else:
                        QTimer.singleShot(0, lambda: self._close_progress_dialog())
                        
                except Exception as e:
                    logger.exception(f"Error during bookmark extraction: {e}")
                    QTimer.singleShot(0, lambda err=str(e): self._show_extraction_error(err))
            
            threading.Thread(target=extraction_thread, daemon=True).start()
            
        except Exception as e:
            logger.error(f"Error in extract_bookmarks_from_browsers: {e}")
            QMessageBox.critical(self, "Error", f"Failed to extract bookmarks: {e}")
    
    def _update_extraction_progress(self, value, message):
        """Update progress dialog from main thread"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.setValue(value)
            self.progress_dialog.setLabelText(message)
            self.status_bar.showMessage(message)
    
    def _close_progress_dialog(self):
        """Close progress dialog from main thread"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
    
    def _show_extraction_error(self, error_message):
        """Show extraction error from main thread"""
        self._close_progress_dialog()
        QMessageBox.critical(self, "Extraction Error", 
                           f"Failed to extract bookmarks: {error_message}")
    
    def _apply_recategorization_results(self, new_categorized):
        """Apply recategorization results on main thread"""
        try:
            self.categorized_bookmarks = new_categorized
            self.populate_category_tree()
            if self.current_category and self.current_category in self.categorized_bookmarks:
                self.populate_bookmark_list(self.current_category)
            self.status_bar.showMessage("Recategorization complete.")
        except Exception as e:
            logger.exception(f"Error applying recategorization results: {e}")
            self.status_bar.showMessage("Error applying recategorization results")
    
    def _apply_import_results(self, imported_categorized, imported_bookmarks, file_path):
        """Apply import results and update UI on main thread"""
        try:
            for category, bookmarks in imported_categorized.items():
                self.categorized_bookmarks.setdefault(category, []).extend(bookmarks)
            self.storage.bookmarks.extend(imported_bookmarks)
            self.storage.save()
            self.populate_category_tree()
            if self.current_category:
                self.populate_bookmark_list(self.current_category)
            # Refresh keyword browser
            if hasattr(self, 'keyword_browser'):
                self.keyword_browser.bookmarks = self.storage.get_all()
                self.keyword_browser.keyword_to_bookmarks = self.keyword_browser._compute_keyword_map()
                self.keyword_browser.keyword_list.clear()
                self.keyword_browser._populate_keywords()
            success_msg = f"Imported {len(imported_bookmarks)} bookmarks successfully from {file_path}"
            self.status_bar.showMessage(success_msg)
        except Exception as e:
            logger.exception(f"Error applying import results: {e}")
            self.status_bar.showMessage("Error applying import results")
    
    def _finish_extraction(self, categorized_bookmarks, all_bookmarks):
        """Finish extraction process and update UI from main thread"""
        try:
            self._close_progress_dialog()
            
            # Merge new bookmarks into existing categorized bookmarks
            for category, bookmarks in categorized_bookmarks.items():
                if category in self.categorized_bookmarks:
                    # Avoid duplicates by checking URLs
                    existing_urls = {b.url for b in self.categorized_bookmarks[category]}
                    new_bookmarks = [b for b in bookmarks if b.url not in existing_urls]
                    self.categorized_bookmarks[category].extend(new_bookmarks)
                else:
                    self.categorized_bookmarks[category] = bookmarks
            
            # Update storage
            existing_urls = {b.url for b in self.storage.bookmarks}
            new_bookmarks = [b for b in all_bookmarks if b.url not in existing_urls]
            self.storage.bookmarks.extend(new_bookmarks)
            self.storage.save()
            
            # Refresh UI
            self.populate_category_tree()
            if self.current_category and self.current_category in self.categorized_bookmarks:
                self.populate_bookmark_list(self.current_category)
            
            # Refresh keyword browser tab
            self.keyword_browser.bookmarks = self.storage.get_all()
            self.keyword_browser.keyword_to_bookmarks = self.keyword_browser._compute_keyword_map()
            self.keyword_browser.keyword_list.clear()
            self.keyword_browser._populate_keywords()
            
            # Update status
            total_new = len(new_bookmarks)
            total_bookmarks = sum(len(bookmarks) 
                                for bookmarks in self.categorized_bookmarks.values())
            self.status_bar.showMessage(
                f"Extraction complete. Added {total_new} new bookmarks. Total: {total_bookmarks}"
            )

            if total_new > 0:
                QMessageBox.information(self, "Extraction Complete", 
                                      f"Successfully extracted {total_new} new bookmarks!")
            else:
                QMessageBox.information(self, "Extraction Complete", 
                                      "No new bookmarks found (all bookmarks already exist).")
                
        except Exception as e:
            logger.error(f"Error finishing extraction: {e}")
            QMessageBox.critical(self, "Error", f"Failed to complete extraction: {e}")

    def recategorize_bookmark(self, bookmark):
        dialog = QDialog(self)
        dialog.setWindowTitle("Recategorize Bookmark")
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
        button_row = QHBoxLayout()
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        save_button = QPushButton("Save")
        save_button.clicked.connect(dialog.accept)
        save_button.setDefault(True)
        button_row.addWidget(cancel_button)
        button_row.addWidget(save_button)
        row = QWidget()
        row.setLayout(button_row)
        layout.addRow("", row)
        if dialog.exec_() == QDialog.Accepted:
            new_category = category_combo.currentText()
            if bookmark in self.categorized_bookmarks.get(bookmark.category, []):
                self.categorized_bookmarks[bookmark.category].remove(bookmark)
            bookmark.category = new_category
            self.categorized_bookmarks.setdefault(new_category, []).append(bookmark)
            self.populate_category_tree()
            if self.current_category:
                self.populate_bookmark_list(self.current_category)

    def validate_bookmark(self, bookmark, item):
        self.status_bar.showMessage(f"Validating link: {bookmark.url}...")

        def validate_thread():
            try:
                from link_validator import _validate_link
                is_valid = _validate_link(bookmark)
                bookmark.is_valid = is_valid
                
                # Route UI updates to main thread
                QTimer.singleShot(0, lambda: item.setForeground(QColor("black" if is_valid else "red")))
                QTimer.singleShot(0, lambda: self.status_bar.showMessage(
                    f"Link validation complete: {'Valid' if is_valid else 'Invalid'} - {bookmark.url}"
                ))
            except Exception as e:
                logger.exception(f"Error validating bookmark {bookmark.url}: {e}")
                QTimer.singleShot(0, lambda: self.status_bar.showMessage(
                    f"Error validating link: {bookmark.url}"
                ))

        threading.Thread(target=validate_thread, daemon=True).start()

    def validate_all_links(self):
        reply = QMessageBox.question(
            self,
            "Validate Links",
            "This will check all visible bookmarks for dead links. " + 
            "It may take some time. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

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
            try:
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
                    
                    # Route status update to main thread
                    progress_msg = (f"Validating links... " + 
                                  f"{i + 1}/{len(bookmarks_to_validate)} complete")
                    QTimer.singleShot(0, lambda msg=progress_msg: 
                                    self.status_bar.showMessage(msg))

                    # Route item color update to main thread
                    item = items_map[bookmark]
                    color = QColor("black" if is_valid else "red")
                    QTimer.singleShot(0, lambda i=item, c=color: i.setForeground(c))

                # Route final status message to main thread
                final_msg = (f"Link validation complete. {valid_count} valid, " + 
                           f"{invalid_count} invalid links.")
                QTimer.singleShot(0, lambda: self.status_bar.showMessage(final_msg))
            except Exception as e:
                logger.exception(f"Error during link validation: {e}")
                QTimer.singleShot(
                    0, 
                    lambda: self.status_bar.showMessage("Error occurred during link validation")
                )

        threading.Thread(target=validate_thread, daemon=True).start()

    def recategorize_all_bookmarks(self):
        reply = QMessageBox.question(
            self,
            "Recategorize Bookmarks",
            "This will recategorize all bookmarks. " + 
            "Any manual categorization will be lost. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        self.status_bar.showMessage("Recategorizing bookmarks... Please wait.")

        def recategorize_thread():
            try:
                all_bookmarks = []
                for bookmarks in self.categorized_bookmarks.values():
                    all_bookmarks.extend(bookmarks)
                for category in list(self.categorized_bookmarks.keys()):
                    self.categorized_bookmarks[category] = []
                from bookmark_categorizer import categorize_bookmarks
                new_categorized = categorize_bookmarks(all_bookmarks)
                
                # Route UI updates to main thread
                QTimer.singleShot(
                    0, 
                    lambda: self._apply_recategorization_results(new_categorized)
                )
            except Exception as e:
                logger.exception(f"Error during recategorization: {e}")
                QTimer.singleShot(
                    0, 
                    lambda: self.status_bar.showMessage("Error occurred during recategorization")
                )

        threading.Thread(target=recategorize_thread, daemon=True).start()

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
                    all_bookmarks.extend(bookmarks)
                export_bookmarks(all_bookmarks, file_path)
                
                # Route status update to main thread
                success_msg = f"Bookmarks exported successfully to {file_path}"
                QTimer.singleShot(0, lambda: self.status_bar.showMessage(success_msg))
            except Exception as e:
                logger.exception(f"Error exporting bookmarks: {e}")
                # Route error message to main thread
                error_msg = f"Error exporting bookmarks: {e}"
                QTimer.singleShot(0, lambda: self.status_bar.showMessage(error_msg))

        threading.Thread(target=export_thread, daemon=True).start()

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
                
                # Route UI updates to main thread
                QTimer.singleShot(0, lambda: self._apply_import_results(imported_categorized, imported_bookmarks, file_path))
            except Exception as e:
                logger.exception(f"Error importing bookmarks: {e}")
                # Route error message to main thread
                error_msg = f"Error importing bookmarks: {e}"
                QTimer.singleShot(0, lambda: self.status_bar.showMessage(error_msg))

        threading.Thread(target=import_thread, daemon=True).start()

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

    # ------------------------- Analysis (Pluggable) -------------------------

    def show_analyzer_settings_dialog(self):
        dlg = AnalyzerSettingsDialog(self)
        dlg.exec_()

    def run_analysis(self):
        bms = self.storage.get_all()
        if len(bms) == 0:
            QMessageBox.information(self, "No Bookmarks", "No bookmarks to process.")
            return

        # Load current analyzer config
        config = load_config()
        available = list_analyzer_names(config)
        if not available:
            QMessageBox.warning(
                self,
                "No Analyzers",
                "No analyzers are available (missing dependencies or API keys).\n"
                "Open Settings → Analyzer Settings… to configure."
            )
            return

        choice, ok = QInputDialog.getItem(self, "Select Analyzer", "Analyzer:", available, 0, False)
        if not ok or not choice:
            return

        cache_path = Path.home() / ".bookmark_aggregator" / "page_content_cache.json"
        self.progress_dialog = QProgressDialog("Preparing...", None, 0, 100, self)
        self.progress_dialog.setWindowTitle("Analyzing Bookmarks")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.setAutoReset(False)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.show()

        self.analysis_worker = AnalysisWorker(
            bookmarks=bms,
            storage_path=str(self.storage.path),
            analyzer_name=choice,
            analyzer_config=config,
            cache_path=str(cache_path),
            polite_delay=0.25,
            user_agent="BookmarkTopicBot/1.0",
            save_every=20,
            max_words=3000,
        )
        self.analysis_worker.progress.connect(self._on_analysis_progress)
        self.analysis_worker.finished_success.connect(self._on_analysis_success)
        self.analysis_worker.failed.connect(self._on_analysis_failure)
        self.analysis_worker.start()

    def _on_analysis_progress(self, pct: int, label: str):
        if getattr(self, "progress_dialog", None):
            self.progress_dialog.setValue(pct)
            self.progress_dialog.setLabelText(label)
            if pct >= 100:
                QTimer.singleShot(400, self.progress_dialog.close)

    def _on_analysis_success(self, count: int):
        # Reload storage and refresh keyword browser
        self.storage.load()
        self.keyword_browser.bookmarks = self.storage.get_all()
        self.keyword_browser.keyword_to_bookmarks = self.keyword_browser._compute_keyword_map()
        self.keyword_browser.keyword_list.clear()
        self.keyword_browser._populate_keywords()
        QMessageBox.information(self, "Done", f"Processed {count} bookmarks.")
        if getattr(self, "progress_dialog", None) and self.progress_dialog.value() < 100:
            self.progress_dialog.setValue(100)

    def _on_analysis_failure(self, message: str):
        if getattr(self, "progress_dialog", None):
            self.progress_dialog.close()
        QMessageBox.critical(self, "Error", message)

    def reprocess_keywords_for_bookmark(self, bookmark):
        self.storage.mark_for_reprocessing(bookmark)
        self.status_bar.showMessage(
            f"Bookmark '{bookmark.title}' marked for rebuild. Run 'Analyze Bookmarks…'."
        )

    # ------------------------- Settings -------------------------

    def show_settings_dialog(self):
        dlg = SettingsDialog(self.settings_manager, self)
        dlg.exec_()


def launch_gui(categorized_bookmarks, cred_manager):
    app = QApplication(sys.argv)
    window = MainWindow(categorized_bookmarks, cred_manager)
    window.show()
    sys.exit(app.exec_())
