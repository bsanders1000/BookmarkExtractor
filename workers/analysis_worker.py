from __future__ import annotations
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt5.QtCore import QThread, pyqtSignal

from analyzers.registry import create_analyzer
from processing.bookmark_processor import BookmarkProcessor


class AnalysisWorker(QThread):
    progress = pyqtSignal(int, str)        # percent, label
    finished_success = pyqtSignal(int)     # processed count
    failed = pyqtSignal(str)

    def __init__(
        self,
        bookmarks: List[Any],
        storage_path: str,
        analyzer_name: str,
        analyzer_config: Dict[str, Any],
        cache_path: Optional[str] = None,
        polite_delay: float = 0.25,
        user_agent: str = "BookmarkTopicBot/1.0",
        save_every: int = 20,
        max_words: int = 3000,
        parent=None
    ):
        super().__init__(parent)
        self.bookmarks = bookmarks
        self.storage_path = storage_path
        self.analyzer_name = analyzer_name
        self.analyzer_config = analyzer_config
        self.cache_path = cache_path
        self.polite_delay = polite_delay
        self.user_agent = user_agent
        self.save_every = save_every
        self.max_words = max_words

    def _save_bookmarks(self):
        try:
            from bookmark_storage import BookmarkStorage
            storage = BookmarkStorage(Path(self.storage_path))
            storage.bookmarks = self.bookmarks
            storage.save()
        except Exception:
            pass

    def _emit_progress(self, i: int, total: int, label: str):
        pct = int((i / max(1, total)) * 100)
        self.progress.emit(pct, label)

    def run(self):
        try:
            # Build analyzer
            analyzer = create_analyzer(self.analyzer_name, self.analyzer_config)

            # Wire project fetcher
            from fetcher import fetch_page_text
            processor = BookmarkProcessor(
                fetcher_func=fetch_page_text,
                analyzer=analyzer,
                cache_path=self.cache_path,
                polite_delay=self.polite_delay,
                user_agent=self.user_agent,
                max_words=self.max_words,
            )

            total = len(self.bookmarks)
            processed = 0
            for idx, b in enumerate(self.bookmarks, start=1):
                ok = processor.analyze_bookmark(b)
                if ok:
                    processed += 1
                    if processed % self.save_every == 0:
                        self._save_bookmarks()
                        processor.flush()
                self._emit_progress(idx, total, f"Processed {idx}/{total}")

            self._save_bookmarks()
            processor.flush()
            self._emit_progress(total, total, "Done")
            self.finished_success.emit(processed)

        except Exception as e:
            tb = traceback.format_exc()
            self.failed.emit(f"{e}\n{tb}")