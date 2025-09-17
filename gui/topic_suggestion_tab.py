from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton,
    QHBoxLayout, QLineEdit, QMessageBox, QApplication, QSplitter
)
from PyQt5.QtCore import Qt
import json
import os
import webbrowser

class TopicSuggestionTab(QWidget):
    def __init__(self, json_path, parent=None):
        super().__init__(parent)
        self.json_path = json_path
        self.topics = []
        self.init_ui()
        self.load_topics()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Search/filter
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter topics by keyword or entity…")
        self.search_box.textChanged.connect(self.apply_filter)
        layout.addWidget(self.search_box)

        # Main splitter: left topics, right details
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # Left: topics list + edit controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        self.topic_list = QListWidget()
        left_layout.addWidget(QLabel("Suggested Topics (click to review/edit):"))
        left_layout.addWidget(self.topic_list)
        self.edit_box = QLineEdit()
        self.edit_box.setPlaceholderText("Edit topic name or keywords...")
        left_layout.addWidget(self.edit_box)
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Changes")
        self.merge_btn = QPushButton("Merge Selected")
        self.add_btn = QPushButton("Add New Topic")
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.merge_btn)
        btn_layout.addWidget(self.add_btn)
        left_layout.addLayout(btn_layout)

        # Right: details panel (keywords, entities, urls)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Keywords
        self.kw_header = QLabel("Keywords:")
        right_layout.addWidget(self.kw_header)
        self.keyword_list = QListWidget()
        right_layout.addWidget(self.keyword_list)

        # Entities
        self.ent_header = QLabel("Entities:")
        right_layout.addWidget(self.ent_header)
        self.entity_list = QListWidget()
        right_layout.addWidget(self.entity_list)

        # URL section
        self.url_header = QLabel("URLs: (select a topic to view)")
        right_layout.addWidget(self.url_header)
        self.url_list = QListWidget()
        self.url_list.setSelectionMode(QListWidget.ExtendedSelection)
        right_layout.addWidget(self.url_list)
        url_btns = QHBoxLayout()
        self.open_url_btn = QPushButton("Open Selected")
        self.copy_url_btn = QPushButton("Copy Selected")
        self.add_url_edit = QLineEdit()
        self.add_url_edit.setPlaceholderText("Add URL to this topic…")
        self.add_url_btn = QPushButton("Add URL")
        self.remove_url_btn = QPushButton("Remove Selected")
        url_btns.addWidget(self.open_url_btn)
        url_btns.addWidget(self.copy_url_btn)
        url_btns.addWidget(self.add_url_edit, stretch=1)
        url_btns.addWidget(self.add_url_btn)
        url_btns.addWidget(self.remove_url_btn)
        right_layout.addLayout(url_btns)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)

        self.setLayout(layout)
        self.topic_list.itemClicked.connect(self.on_topic_selected)
        self.save_btn.clicked.connect(self.save_changes)
        self.merge_btn.clicked.connect(self.merge_selected)
        self.add_btn.clicked.connect(self.add_new_topic)
        self.open_url_btn.clicked.connect(self.open_selected_urls)
        self.copy_url_btn.clicked.connect(self.copy_selected_urls)
        self.add_url_btn.clicked.connect(self.add_url_to_topic)
        self.remove_url_btn.clicked.connect(self.remove_selected_urls)
        self.url_list.itemDoubleClicked.connect(self.on_url_double_clicked)
        self.selected_index = None

    def load_topics(self):
        if not os.path.exists(self.json_path):
            QMessageBox.warning(self, "No Data", f"Topic file not found: {self.json_path}")
            return
        with open(self.json_path, "r") as f:
            self.topics = json.load(f)
        self.topic_list.clear()
        for idx, topic in enumerate(self.topics):
            kws = ", ".join([kw for kw, _ in topic.get('keywords', [])])
            item = QListWidgetItem(f"{topic.get('topic_id', idx)}: {kws}")
            item.setData(Qt.UserRole, idx)
            self.topic_list.addItem(item)
        self.apply_filter(self.search_box.text())

    def on_topic_selected(self, item):
        idx = item.data(Qt.UserRole)
        self.selected_index = int(idx)
        topic = self.topics[self.selected_index]
        self.edit_box.setText(", ".join([kw for kw, _ in topic['keywords']]))
        self.populate_keywords_entities(topic)
        self.populate_urls_for_topic(topic)

    def populate_keywords_entities(self, topic):
        kws = topic.get('keywords', []) or []
        ents = topic.get('entities', []) or []
        self.keyword_list.clear()
        for kw, count in kws:
            self.keyword_list.addItem(QListWidgetItem(f"{kw} ({count})"))
        self.entity_list.clear()
        for ent, count in ents:
            self.entity_list.addItem(QListWidgetItem(f"{ent} ({count})"))

    def populate_urls_for_topic(self, topic):
        urls = topic.get('sample_urls', []) or []
        evidence = topic.get('evidence_count', len(urls))
        self.url_header.setText(f"URLs: showing {len(urls)} | evidence {evidence}")
        self.url_list.clear()
        for url in urls:
            self.url_list.addItem(QListWidgetItem(url))

    def on_url_double_clicked(self, item):
        url = item.text()
        if url:
            webbrowser.open(url)

    def open_selected_urls(self):
        items = self.url_list.selectedItems()
        for it in items:
            url = it.text()
            if url:
                webbrowser.open(url)

    def copy_selected_urls(self):
        items = self.url_list.selectedItems()
        urls = [it.text() for it in items if it.text()]
        if urls:
            QApplication.clipboard().setText("\n".join(urls))

    def add_url_to_topic(self):
        if self.selected_index is None:
            return
        url = (self.add_url_edit.text() or "").strip()
        if not url:
            return
        # Basic validation
        if not (url.startswith("http://") or url.startswith("https://")):
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid http(s) URL.")
            return
        topic = self.topics[self.selected_index]
        urls = topic.setdefault('sample_urls', [])
        if url in urls:
            QMessageBox.information(self, "Duplicate", "This URL is already in the topic.")
            return
        urls.append(url)
        self.save_topics()
        self.populate_urls_for_topic(topic)
        self.add_url_edit.clear()

    def remove_selected_urls(self):
        if self.selected_index is None:
            return
        topic = self.topics[self.selected_index]
        urls = topic.setdefault('sample_urls', [])
        selected = [it.text() for it in self.url_list.selectedItems()]
        if not selected:
            return
        topic['sample_urls'] = [u for u in urls if u not in selected]
        self.save_topics()
        self.populate_urls_for_topic(topic)

    def save_changes(self):
        if self.selected_index is None:
            return
        new_keywords = [kw.strip() for kw in self.edit_box.text().split(",") if kw.strip()]
        self.topics[self.selected_index]['keywords'] = [(kw, 1) for kw in new_keywords]
        self.save_topics()
        # Refresh lists but maintain selection
        self.load_topics()
        # Restore selection by finding item with matching data
        for i in range(self.topic_list.count()):
            if self.topic_list.item(i).data(Qt.UserRole) == self.selected_index:
                self.topic_list.setCurrentRow(i)
                break
        self.populate_keywords_entities(self.topics[self.selected_index])

    def merge_selected(self):
        selected = self.topic_list.selectedItems()
        if len(selected) < 2:
            QMessageBox.information(self, "Merge Topics", "Select at least two topics to merge.")
            return
        idxs = [int(item.data(Qt.UserRole)) for item in selected]
        merged_keywords = set()
        merged_sample_urls = []
        for idx in idxs:
            merged_keywords.update([kw for kw, _ in self.topics[idx]['keywords']])
            merged_sample_urls.extend(self.topics[idx]['sample_urls'])
        new_topic = {
            "topic_id": min([self.topics[idx]['topic_id'] for idx in idxs]),
            "keywords": [(kw, 1) for kw in merged_keywords],
            "entities": [],  # could merge too; keeping simple for now
            "sample_urls": merged_sample_urls[:5],
            "evidence_count": sum([self.topics[idx]['evidence_count'] for idx in idxs]),
        }
        for idx in sorted(idxs, reverse=True):
            del self.topics[idx]
        self.topics.append(new_topic)
        self.save_topics()
        self.load_topics()

    def add_new_topic(self):
        new_keywords = [kw.strip() for kw in self.edit_box.text().split(",") if kw.strip()]
        if not new_keywords:
            return
        new_topic = {
            "topic_id": max([t.get('topic_id', 0) for t in self.topics]+[0])+1,
            "keywords": [(kw, 1) for kw in new_keywords],
            "entities": [],
            "sample_urls": [],
            "evidence_count": 0,
        }
        self.topics.append(new_topic)
        self.save_topics()
        self.load_topics()

    def save_topics(self):
        try:
            with open(self.json_path, "w") as f:
                json.dump(self.topics, f, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save topics: {e}")

    def apply_filter(self, text: str):
        text = (text or "").strip().lower()
        for i in range(self.topic_list.count()):
            item = self.topic_list.item(i)
            idx = int(item.data(Qt.UserRole))
            topic = self.topics[idx]
            kws = [kw for kw, _ in topic.get('keywords', [])]
            ents = [en for en, _ in topic.get('entities', [])]
            hay = " ".join(kws + ents).lower()
            item.setHidden(bool(text) and text not in hay)
