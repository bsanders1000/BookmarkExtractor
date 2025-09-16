#!/usr/bin/env python3
"""
Keyword Browser Widget - Widget for browsing bookmark keywords and topics
"""
import logging
from typing import List, Dict

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QLineEdit, QPushButton, QSplitter
)
from PyQt5.QtCore import Qt, pyqtSignal

from bookmark_extractor import Bookmark

logger = logging.getLogger(__name__)

class KeywordBrowserWidget(QWidget):
    """Widget for browsing and filtering bookmarks by keywords and topics"""
    
    bookmark_selected = pyqtSignal(object)  # Bookmark selected signal
    
    def __init__(self, parent=None, *, bookmarks=None):
        super().__init__(parent)
        self.bookmarks: List[Bookmark] = []
        self.filtered_bookmarks: List[Bookmark] = []
        
        self.init_ui()
        
        # Set bookmarks if provided
        if bookmarks:
            self.set_bookmarks(bookmarks)
        
    def init_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout()
        
        # Search bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search keywords, topics, or titles...")
        self.search_edit.textChanged.connect(self.filter_bookmarks)
        search_layout.addWidget(self.search_edit)
        
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear_search)
        search_layout.addWidget(clear_button)
        
        layout.addLayout(search_layout)
        
        # Splitter for topics/keywords and bookmarks
        splitter = QSplitter(Qt.Horizontal)
        
        # Topics and Keywords panel
        topics_widget = QWidget()
        topics_layout = QVBoxLayout()
        
        topics_layout.addWidget(QLabel("Topics:"))
        self.topics_list = QListWidget()
        self.topics_list.itemClicked.connect(self.on_topic_selected)
        topics_layout.addWidget(self.topics_list)
        
        topics_layout.addWidget(QLabel("Keywords:"))
        self.keywords_list = QListWidget()
        self.keywords_list.itemClicked.connect(self.on_keyword_selected)
        topics_layout.addWidget(self.keywords_list)
        
        topics_widget.setLayout(topics_layout)
        splitter.addWidget(topics_widget)
        
        # Bookmarks panel
        bookmarks_widget = QWidget()
        bookmarks_layout = QVBoxLayout()
        
        bookmarks_layout.addWidget(QLabel("Bookmarks:"))
        self.bookmarks_list = QListWidget()
        self.bookmarks_list.itemClicked.connect(self.on_bookmark_selected)
        bookmarks_layout.addWidget(self.bookmarks_list)
        
        bookmarks_widget.setLayout(bookmarks_layout)
        splitter.addWidget(bookmarks_widget)
        
        # Set splitter proportions
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        layout.addWidget(splitter)
        self.setLayout(layout)
        
    def set_bookmarks(self, bookmarks: List[Bookmark]):
        """Set the bookmarks to display"""
        self.bookmarks = bookmarks
        self.filtered_bookmarks = bookmarks.copy()
        self.update_displays()
        
    def update_displays(self):
        """Update all display lists"""
        self.update_topics_list()
        self.update_keywords_list()
        self.update_bookmarks_list()
        
    def update_topics_list(self):
        """Update the topics list"""
        self.topics_list.clear()
        
        # Collect all topics
        topics_count = {}
        for bookmark in self.filtered_bookmarks:
            for topic in bookmark.topics:
                topics_count[topic] = topics_count.get(topic, 0) + 1
                
        # Sort by frequency
        sorted_topics = sorted(topics_count.items(), key=lambda x: x[1], reverse=True)
        
        for topic, count in sorted_topics:
            item = QListWidgetItem(f"{topic} ({count})")
            item.setData(Qt.UserRole, topic)
            self.topics_list.addItem(item)
            
    def update_keywords_list(self):
        """Update the keywords list"""
        self.keywords_list.clear()
        
        # Collect all keywords
        keywords_count = {}
        for bookmark in self.filtered_bookmarks:
            for keyword in bookmark.keywords:
                keywords_count[keyword] = keywords_count.get(keyword, 0) + 1
                
        # Sort by frequency
        sorted_keywords = sorted(keywords_count.items(), key=lambda x: x[1], reverse=True)
        
        for keyword, count in sorted_keywords[:50]:  # Limit to top 50
            item = QListWidgetItem(f"{keyword} ({count})")
            item.setData(Qt.UserRole, keyword)
            self.keywords_list.addItem(item)
            
    def update_bookmarks_list(self):
        """Update the bookmarks list"""
        self.bookmarks_list.clear()
        
        for bookmark in self.filtered_bookmarks:
            title = bookmark.title or "Untitled"
            if len(title) > 60:
                title = title[:57] + "..."
                
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, bookmark)
            item.setToolTip(f"URL: {bookmark.url}\\nTopics: {', '.join(bookmark.topics)}\\nKeywords: {', '.join(bookmark.keywords[:5])}")
            self.bookmarks_list.addItem(item)
            
    def filter_bookmarks(self):
        """Filter bookmarks based on search text"""
        search_text = self.search_edit.text().lower()
        
        if not search_text:
            self.filtered_bookmarks = self.bookmarks.copy()
        else:
            self.filtered_bookmarks = []
            for bookmark in self.bookmarks:
                # Search in title, keywords, and topics
                searchable_text = " ".join([
                    bookmark.title.lower(),
                    " ".join(bookmark.keywords).lower(),
                    " ".join(bookmark.topics).lower()
                ])
                
                if search_text in searchable_text:
                    self.filtered_bookmarks.append(bookmark)
                    
        self.update_displays()
        
    def clear_search(self):
        """Clear search and show all bookmarks"""
        self.search_edit.clear()
        self.filtered_bookmarks = self.bookmarks.copy()
        self.update_displays()
        
    def on_topic_selected(self, item):
        """Handle topic selection"""
        topic = item.data(Qt.UserRole)
        # Filter bookmarks that have this topic
        self.filtered_bookmarks = [b for b in self.bookmarks if topic in b.topics]
        self.update_bookmarks_list()
        
    def on_keyword_selected(self, item):
        """Handle keyword selection"""
        keyword = item.data(Qt.UserRole)
        # Filter bookmarks that have this keyword
        self.filtered_bookmarks = [b for b in self.bookmarks if keyword in b.keywords]
        self.update_bookmarks_list()
        
    def on_bookmark_selected(self, item):
        """Handle bookmark selection"""
        bookmark = item.data(Qt.UserRole)
        self.bookmark_selected.emit(bookmark)