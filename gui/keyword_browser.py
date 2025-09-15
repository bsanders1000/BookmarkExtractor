from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QLabel, QSplitter, QListWidgetItem
from PyQt5.QtCore import Qt
from bookmark_extractor import Bookmark

class KeywordBrowserWidget(QWidget):
    def __init__(self, bookmarks):
        super().__init__()
        self.bookmarks = bookmarks
        self.keyword_to_bookmarks = self._compute_keyword_map()
        layout = QVBoxLayout(self)
        self.splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(self.splitter)
        self.keyword_list = QListWidget()
        self.splitter.addWidget(self.keyword_list)
        self.bookmark_list = QListWidget()
        self.splitter.addWidget(self.bookmark_list)
        self.keyword_list.itemClicked.connect(self.show_bookmarks_for_keyword)
        self._populate_keywords()

    def _compute_keyword_map(self):
        keyword_map = {}
        for b in self.bookmarks:
            for kw in b.keywords:
                kw_lower = kw.lower()
                if kw_lower not in keyword_map:
                    keyword_map[kw_lower] = []
                keyword_map[kw_lower].append(b)
        return keyword_map

    def _populate_keywords(self):
        keywords = sorted(self.keyword_to_bookmarks.keys())
        for kw in keywords:
            self.keyword_list.addItem(kw)

    def show_bookmarks_for_keyword(self, item):
        kw = item.text()
        self.bookmark_list.clear()
        for b in self.keyword_to_bookmarks.get(kw, []):
            lw_item = QListWidgetItem(f"{b.title} ({b.url})")
            lw_item.setToolTip(b.url)
            self.bookmark_list.addItem(lw_item)