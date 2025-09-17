from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QHBoxLayout, QLineEdit, QMessageBox
from PyQt5.QtCore import Qt
import json
import os

class TopicSuggestionTab(QWidget):
    def __init__(self, json_path, parent=None):
        super().__init__(parent)
        self.json_path = json_path
        self.topics = []
        self.init_ui()
        self.load_topics()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.topic_list = QListWidget()
        layout.addWidget(QLabel("Suggested Topics (click to review/edit):"))
        layout.addWidget(self.topic_list)
        self.edit_box = QLineEdit()
        self.edit_box.setPlaceholderText("Edit topic name or keywords...")
        layout.addWidget(self.edit_box)
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Changes")
        self.merge_btn = QPushButton("Merge Selected")
        self.add_btn = QPushButton("Add New Topic")
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.merge_btn)
        btn_layout.addWidget(self.add_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        self.topic_list.itemClicked.connect(self.on_topic_selected)
        self.save_btn.clicked.connect(self.save_changes)
        self.merge_btn.clicked.connect(self.merge_selected)
        self.add_btn.clicked.connect(self.add_new_topic)
        self.selected_index = None

    def load_topics(self):
        if not os.path.exists(self.json_path):
            QMessageBox.warning(self, "No Data", f"Topic file not found: {self.json_path}")
            return
        with open(self.json_path, "r") as f:
            self.topics = json.load(f)
        self.topic_list.clear()
        for topic in self.topics:
            item = QListWidgetItem(f"{topic['topic_id']}: {', '.join([kw for kw, _ in topic['keywords']])}")
            self.topic_list.addItem(item)

    def on_topic_selected(self, item):
        idx = self.topic_list.row(item)
        self.selected_index = idx
        topic = self.topics[idx]
        self.edit_box.setText(", ".join([kw for kw, _ in topic['keywords']]))

    def save_changes(self):
        if self.selected_index is None:
            return
        new_keywords = [kw.strip() for kw in self.edit_box.text().split(",") if kw.strip()]
        self.topics[self.selected_index]['keywords'] = [(kw, 1) for kw in new_keywords]
        self.load_topics()
        self.topic_list.setCurrentRow(self.selected_index)
        with open(self.json_path, "w") as f:
            json.dump(self.topics, f, indent=2)

    def merge_selected(self):
        selected = self.topic_list.selectedItems()
        if len(selected) < 2:
            QMessageBox.information(self, "Merge Topics", "Select at least two topics to merge.")
            return
        idxs = [self.topic_list.row(item) for item in selected]
        merged_keywords = set()
        merged_sample_urls = []
        for idx in idxs:
            merged_keywords.update([kw for kw, _ in self.topics[idx]['keywords']])
            merged_sample_urls.extend(self.topics[idx]['sample_urls'])
        new_topic = {
            "topic_id": min([self.topics[idx]['topic_id'] for idx in idxs]),
            "keywords": [(kw, 1) for kw in merged_keywords],
            "entities": [],
            "sample_urls": merged_sample_urls[:5],
            "evidence_count": sum([self.topics[idx]['evidence_count'] for idx in idxs]),
        }
        for idx in sorted(idxs, reverse=True):
            del self.topics[idx]
        self.topics.append(new_topic)
        with open(self.json_path, "w") as f:
            json.dump(self.topics, f, indent=2)
        self.load_topics()

    def add_new_topic(self):
        new_keywords = [kw.strip() for kw in self.edit_box.text().split(",") if kw.strip()]
        if not new_keywords:
            return
        new_topic = {
            "topic_id": max([t['topic_id'] for t in self.topics]+[0])+1,
            "keywords": [(kw, 1) for kw in new_keywords],
            "entities": [],
            "sample_urls": [],
            "evidence_count": 0,
        }
        self.topics.append(new_topic)
        with open(self.json_path, "w") as f:
            json.dump(self.topics, f, indent=2)
        self.load_topics()
