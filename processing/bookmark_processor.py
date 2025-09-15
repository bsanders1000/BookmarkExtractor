from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, Optional

from analyzers.base import Analyzer, AnalysisResult


class BookmarkProcessor:
    """
    Orchestrates per-bookmark processing:
      - fetch text (with cache)
      - run analyzer
      - update bookmark fields
    """
    def __init__(
        self,
        fetcher_func,
        analyzer: Analyzer,
        cache_path: Optional[str] = None,
        polite_delay: float = 0.25,
        user_agent: str = "BookmarkTopicBot/1.0",
        max_words: int = 3000,
    ):
        self.fetcher_func = fetcher_func
        self.analyzer = analyzer
        self.cache_path = Path(cache_path) if cache_path else None
        self.polite_delay = polite_delay
        self.user_agent = user_agent
        self.max_words = max_words
        self._cache: Dict[str, str] = self._load_cache()

    def _load_cache(self) -> Dict[str, str]:
        if not self.cache_path or not self.cache_path.exists():
            return {}
        try:
            return json.loads(self.cache_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_cache(self):
        if not self.cache_path:
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(self._cache, indent=2), encoding="utf-8")

    def fetch_text(self, url: str) -> str:
        if url in self._cache:
            return self._cache[url]
        text = self.fetcher_func(
            url,
            timeout=15,
            max_words=self.max_words,
            sleep_between=self.polite_delay,
            user_agent=self.user_agent,
        ) or ""
        if text:
            self._cache[url] = text
        return text

    def analyze_bookmark(self, bookmark) -> bool:
        """
        Returns True if bookmark was updated.
        Bookmark is expected to have: url, title, is_valid, keywords, topics.
        """
        url = getattr(bookmark, "url", None)
        if not url or not getattr(bookmark, "is_valid", True):
            return False

        title = getattr(bookmark, "title", "") or ""
        text = self.fetch_text(url)
        if not text:
            # Fallback: analyze title only
            result = self.analyzer.extract(title, title=title)
        else:
            result = self.analyzer.extract(text, title=title)

        # Update bookmark fields (compatible with existing structure)
        setattr(bookmark, "topics", result.topics or [])
        setattr(bookmark, "keywords", result.keywords or [])

        # Clear legacy fields if present
        if hasattr(bookmark, "lda_topics"):
            setattr(bookmark, "lda_topics", [])
        if hasattr(bookmark, "lda_keywords"):
            setattr(bookmark, "lda_keywords", [])
        if hasattr(bookmark, "needs_reprocess"):
            setattr(bookmark, "needs_reprocess", False)

        return True

    def flush(self):
        self._save_cache()