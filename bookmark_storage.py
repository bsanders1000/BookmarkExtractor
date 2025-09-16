#!/usr/bin/env python3
"""
Bookmark Storage - Manages persistent storage of bookmarks
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from bookmark_extractor import Bookmark

logger = logging.getLogger(__name__)

class BookmarkStorage:
    """Manages persistent storage and retrieval of bookmarks"""
    
    def __init__(self, storage_path: Path):
        self.path = storage_path
        self.bookmarks: List[Bookmark] = []
        
    def load(self) -> bool:
        """Load bookmarks from storage file"""
        try:
            if not self.path.exists():
                logger.info(f"Storage file {self.path} does not exist, starting fresh")
                return True
                
            with open(self.path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            self.bookmarks = []
            for item in data.get('bookmarks', []):
                bookmark = Bookmark(
                    url=item['url'],
                    title=item['title'],
                    browser_source=item['browser_source'],
                    date_added=item.get('date_added'),
                    folder_path=item.get('folder_path', ''),
                    icon_url=item.get('icon_url'),
                    tags=item.get('tags', []),
                    keywords=item.get('keywords', []),
                    topics=item.get('topics', [])
                )
                bookmark.category = item.get('category', '')
                bookmark.is_valid = item.get('is_valid', True)
                self.bookmarks.append(bookmark)
                
            logger.info(f"Loaded {len(self.bookmarks)} bookmarks from {self.path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load bookmarks from {self.path}: {e}")
            return False
            
    def save(self) -> bool:
        """Save bookmarks to storage file"""
        try:
            # Ensure directory exists
            self.path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'bookmarks': []
            }
            
            for bookmark in self.bookmarks:
                data['bookmarks'].append({
                    'url': bookmark.url,
                    'title': bookmark.title,
                    'browser_source': bookmark.browser_source,
                    'date_added': bookmark.date_added,
                    'folder_path': bookmark.folder_path,
                    'icon_url': bookmark.icon_url,
                    'tags': bookmark.tags,
                    'keywords': bookmark.keywords,
                    'topics': bookmark.topics,
                    'category': bookmark.category,
                    'is_valid': bookmark.is_valid
                })
                
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Saved {len(self.bookmarks)} bookmarks to {self.path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save bookmarks to {self.path}: {e}")
            return False
            
    def get_all(self) -> List[Bookmark]:
        """Get all bookmarks"""
        return self.bookmarks.copy()
        
    def add_bookmark(self, bookmark: Bookmark) -> None:
        """Add a bookmark"""
        self.bookmarks.append(bookmark)
        
    def update_bookmark(self, url: str, **updates) -> bool:
        """Update a bookmark by URL"""
        for bookmark in self.bookmarks:
            if bookmark.url == url:
                for key, value in updates.items():
                    if hasattr(bookmark, key):
                        setattr(bookmark, key, value)
                return True
        return False
        
    def remove_bookmark(self, url: str) -> bool:
        """Remove a bookmark by URL"""
        for i, bookmark in enumerate(self.bookmarks):
            if bookmark.url == url:
                del self.bookmarks[i]
                return True
        return False
        
    def mark_for_reprocessing(self, bookmark: Bookmark) -> None:
        """Mark a bookmark for reprocessing by clearing analysis results"""
        bookmark.keywords = []
        bookmark.topics = []
        logger.info(f"Marked bookmark '{bookmark.title}' for reprocessing")