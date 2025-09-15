import json
import logging
from pathlib import Path
from typing import List, Optional, Any, Dict, Callable

from bookmark_extractor import Bookmark

logger = logging.getLogger(__name__)


class BookmarkStorage:
    """
    Handles persistence of Bookmark objects to a JSON file.
    Supports legacy 'keywords' only mode and extended topic modeling fields:
      - topics (BERTopic per-doc topics)
      - lda_topics (LDA per-doc topics)
      - lda_keywords (shortcut list from top LDA topic)
      - needs_reprocess (flag for future selective rebuild logic)
    """

    def __init__(self, storage_path: Path):
        if not isinstance(storage_path, Path):
            storage_path = Path(storage_path)
        self.storage_path: Path = storage_path
        # For compatibility with code that expects .path
        # (e.g. run_batch_topic_modeling(... save_path=str(self.storage.path) ...))
        # Provide a property below.
        self.bookmarks: List[Bookmark] = []

    # ------------------------------------------------------------------
    # Path property (canonical)
    # ------------------------------------------------------------------
    @property
    def path(self) -> Path:
        """
        Canonical path accessor used by the modeling pipeline.
        (Previously was broken because it referenced a non-existent _file_path.)
        """
        return self.storage_path

    # ------------------------------------------------------------------
    # Load / Save
    # ------------------------------------------------------------------
    def load(self, bookmark_factory: Optional[Callable[[Dict[str, Any]], Bookmark]] = None):
        """
        Load bookmarks from JSON. If bookmark_factory is provided it will be used
        to construct Bookmark objects. Otherwise a default _dict_to_bookmark is used.
        """
        if not self.storage_path.exists():
            logger.info("Storage file %s does not exist. Starting with empty list.", self.storage_path)
            self.bookmarks = []
            return

        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            bms = []
            for entry in data:
                try:
                    if bookmark_factory:
                        bm = bookmark_factory(entry)
                    else:
                        bm = self._dict_to_bookmark(entry)
                    bms.append(bm)
                except Exception as e:
                    logger.warning("Skipping corrupt bookmark entry: %s (err=%s)", entry, e)
            self.bookmarks = bms
            logger.info("Loaded %d bookmarks from %s", len(self.bookmarks), self.storage_path)
        except Exception as e:
            logger.exception("Failed to load bookmarks: %s", e)
            self.bookmarks = []

    def save(self):
        """
        Persist bookmarks to JSON.
        """
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump([self._bookmark_to_dict(b) for b in self.bookmarks], f, indent=2)
            logger.info("Saved %d bookmarks to %s", len(self.bookmarks), self.storage_path)
        except Exception as e:
            logger.exception("Failed to save bookmarks: %s", e)

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------
    def _bookmark_to_dict(self, b: Bookmark) -> Dict[str, Any]:
        return {
            'url': getattr(b, 'url', ''),
            'title': getattr(b, 'title', ''),
            'browser_source': getattr(b, 'browser_source', ''),
            'date_added': getattr(b, 'date_added', None),
            'folder_path': getattr(b, 'folder_path', ''),
            'icon_url': getattr(b, 'icon_url', None),
            'tags': getattr(b, 'tags', []),
            'category': getattr(b, 'category', ''),
            'is_valid': getattr(b, 'is_valid', True),
            'keywords': getattr(b, 'keywords', []),
            # Topic modeling additions:
            'topics': getattr(b, 'topics', []),
            'lda_topics': getattr(b, 'lda_topics', []),
            'lda_keywords': getattr(b, 'lda_keywords', []),
            'needs_reprocess': getattr(b, 'needs_reprocess', False),
        }

    def _dict_to_bookmark(self, d: Dict[str, Any]) -> Bookmark:
        """
        Reconstruct a Bookmark. Adjust this if your Bookmark __init__ signature changes.
        Additional attributes not accepted by __init__ are set afterward.
        """
        bm = Bookmark(
            url=d.get('url', ''),
            title=d.get('title', ''),
            browser_source=d.get('browser_source', ''),
            date_added=d.get('date_added'),
            folder_path=d.get('folder_path', ''),
            icon_url=d.get('icon_url'),
            tags=d.get('tags', []),
            keywords=d.get('keywords', []),
        )
        # Reattach extended attributes:
        bm.category = d.get('category', '')
        bm.is_valid = d.get('is_valid', True)
        bm.topics = d.get('topics', [])
        bm.lda_topics = d.get('lda_topics', [])
        bm.lda_keywords = d.get('lda_keywords', [])
        bm.needs_reprocess = d.get('needs_reprocess', False)
        return bm

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_all(self) -> List[Bookmark]:
        return self.bookmarks

    def get_unprocessed(self, consider_topics: bool = False) -> List[Bookmark]:
        """
        Return bookmarks needing initial processing.
        If consider_topics=True, also flag those without BERTopic topics.
        """
        if consider_topics:
            return [
                b for b in self.bookmarks
                if b.is_valid and not (getattr(b, 'topics', None) or getattr(b, 'keywords', None))
            ]
        return [b for b in self.bookmarks if b.is_valid and not getattr(b, 'keywords', None)]

    def mark_processed(self, bookmark: Bookmark, keywords: List[str]):
        bookmark.keywords = keywords
        bookmark.needs_reprocess = False
        self.save()

    def mark_for_reprocessing(self, bookmark: Bookmark):
        bookmark.keywords = []
        bookmark.topics = []
        bookmark.lda_topics = []
        bookmark.lda_keywords = []
        bookmark.needs_reprocess = True
        self.save()

    # --- Topic modeling update helpers ---
    def update_topics(self, bookmark: Bookmark, topics: List[dict], derived_keywords: List[str]):
        bookmark.topics = topics
        bookmark.keywords = derived_keywords
        bookmark.needs_reprocess = False

    def update_lda_topics(self, bookmark: Bookmark, lda_topics: List[dict], lda_keywords: List[str]):
        bookmark.lda_topics = lda_topics
        bookmark.lda_keywords = lda_keywords

    def bulk_save(self):
        """
        Alias to save() for clarity when batch operations happen.
        """
        self.save()

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------
    def __len__(self):
        return len(self.bookmarks)

    def __repr__(self):
        return f"BookmarkStorage(path={self.storage_path}, count={len(self.bookmarks)})"