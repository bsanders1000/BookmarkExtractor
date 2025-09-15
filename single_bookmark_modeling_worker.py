import json
import time
import traceback
from pathlib import Path
from typing import List, Any, Optional

from PyQt5.QtCore import QThread, pyqtSignal

from single_doc_topic import SingleDocBERTopicExtractor


class SingleBookmarkModelingWorker(QThread):
    progress = pyqtSignal(int, str)        # percent, label
    finished_success = pyqtSignal(int)     # processed count
    failed = pyqtSignal(str)

    def __init__(
        self,
        bookmarks: List[Any],
        save_path: str,
        cache_path: Optional[str] = None,
        polite_delay: float = 0.25,
        user_agent: str = "BookmarkTopicBot/1.0",
        embedding_model: str = "all-MiniLM-L6-v2",
        min_topic_size: int = 2,
        top_n_words: int = 10,
        save_every: int = 20,
        parent=None
    ):
        super().__init__(parent)
        self.bookmarks = bookmarks
        self.save_path = save_path
        self.cache_path = cache_path
        self.polite_delay = polite_delay
        self.user_agent = user_agent
        self.embedding_model = embedding_model
        self.min_topic_size = min_topic_size
        self.top_n_words = top_n_words
        self.save_every = save_every

    def _emit_progress(self, i: int, total: int, label: str):
        pct = int((i / max(1, total)) * 100)
        self.progress.emit(pct, label)

    def _load_cache(self) -> dict:
        if not self.cache_path:
            return {}
        p = Path(self.cache_path)
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_cache(self, cache: dict):
        if not self.cache_path:
            return
        p = Path(self.cache_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(cache, indent=2), encoding="utf-8")

    def _save_bookmarks(self):
        # Persist using BookmarkStorage to stay consistent with app serialization
        try:
            from bookmark_storage import BookmarkStorage
            storage = BookmarkStorage(Path(self.save_path))
            storage.bookmarks = self.bookmarks
            storage.save()
        except Exception:
            # As a last resort, write a minimal JSON (keys we know); but prefer BookmarkStorage.
            pass

    def _fetch_text(self, url: str, max_words: int = 3000) -> str:
        """
        Try to use an existing project fetcher if present; fallback to simple requests + BeautifulSoup.
        """
        # Preferred: project fetcher
        try:
            from fetcher import fetch_page_text  # type: ignore
            return fetch_page_text(url, max_words=max_words, sleep_between=self.polite_delay, user_agent=self.user_agent) or ""
        except Exception:
            pass

        # Fallback: simple requests + bs4
        try:
            import requests
            from bs4 import BeautifulSoup  # type: ignore
            headers = {"User-Agent": self.user_agent}
            resp = requests.get(url, headers=headers, timeout=15)
            time.sleep(self.polite_delay)
            if resp.status_code != 200 or not resp.text:
                return ""
            soup = BeautifulSoup(resp.text, "html.parser")
            # Remove script/style
            for tag in soup(["script", "style", "noscript"]):
                tag.extract()
            text = soup.get_text(" ")
            words = text.split()
            if len(words) > max_words:
                words = words[:max_words]
            return " ".join(words)
        except Exception:
            return ""

    def run(self):
        try:
            extractor = SingleDocBERTopicExtractor(
                embedding_model=self.embedding_model,
                min_topic_size=self.min_topic_size,
                top_n_words=self.top_n_words
            )

            cache = self._load_cache()
            total = len(self.bookmarks)
            processed = 0

            for idx, b in enumerate(self.bookmarks, start=1):
                url = getattr(b, "url", None)
                title = getattr(b, "title", "") or ""
                is_valid = getattr(b, "is_valid", True)
                if not url or not is_valid:
                    self._emit_progress(idx, total, f"Skipping invalid ({idx}/{total})")
                    continue

                text = cache.get(url)
                if not text:
                    text = self._fetch_text(url, max_words=3000)
                    if text:
                        cache[url] = text

                if not text:
                    out = extractor._fallback_keywords(title)
                else:
                    out = extractor.extract(text)

                setattr(b, "topics", out.get("topics", []))
                setattr(b, "keywords", out.get("derived_keywords", []))
                # Clear LDA fields if present
                if hasattr(b, "lda_topics"):
                    setattr(b, "lda_topics", [])
                if hasattr(b, "lda_keywords"):
                    setattr(b, "lda_keywords", [])

                processed += 1
                if processed % self.save_every == 0:
                    self._save_bookmarks()
                    self._save_cache(cache)

                self._emit_progress(idx, total, f"Processed {idx}/{total}")

            self._save_bookmarks()
            self._save_cache(cache)
            self._emit_progress(total, total, "Done")
            self.finished_success.emit(processed)

        except Exception as e:
            tb = traceback.format_exc()
            self.failed.emit(f"{e}\n{tb}")