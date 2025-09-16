#!/usr/bin/env python3
"""
Analysis Worker - Handles bookmark analysis in background thread
"""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from PyQt5.QtCore import QThread, pyqtSignal

from bookmark_extractor import Bookmark
from bookmark_storage import BookmarkStorage
from analyzers.registry import get_analyzer_by_name

logger = logging.getLogger(__name__)

class AnalysisWorker(QThread):
    """Background worker for bookmark analysis"""
    
    # Signals
    progress = pyqtSignal(int, str)  # progress percentage, status message
    finished_success = pyqtSignal(int)  # number of bookmarks processed
    failed = pyqtSignal(str)  # error message
    
    def __init__(self, bookmarks: List[Bookmark], storage_path: str, 
                 analyzer_name: str, analyzer_config: Dict[str, Any],
                 cache_path: str, polite_delay: float = 0.25,
                 user_agent: str = "BookmarkTopicBot/1.0",
                 save_every: int = 20, max_words: int = 3000):
        super().__init__()
        self.bookmarks = bookmarks
        self.storage_path = Path(storage_path)
        self.analyzer_name = analyzer_name
        self.analyzer_config = analyzer_config
        self.cache_path = cache_path
        self.polite_delay = polite_delay
        self.user_agent = user_agent
        self.save_every = save_every
        self.max_words = max_words
        
    def run(self):
        """Run the analysis"""
        try:
            # Get analyzer
            analyzer = get_analyzer_by_name(self.analyzer_name)
            if not analyzer:
                self.failed.emit(f"Analyzer '{self.analyzer_name}' not found")
                return
                
            # Initialize storage
            storage = BookmarkStorage(self.storage_path)
            storage.load()
            
            self.progress.emit(0, "Starting analysis...")
            
            # Get analyzer settings from config
            analyzer_settings = self.analyzer_config.get(self.analyzer_name, {})
            
            # Run analysis
            try:
                from credential_manager import CredentialManager
                cred_manager_path = Path.home() / ".bookmark_aggregator" / "credentials.enc"
                cred_manager = None
                if cred_manager_path.exists():
                    cred_manager = CredentialManager(cred_manager_path)
                    # Note: We can't ask for password in background thread
                    # so credential manager won't be initialized
            except Exception:
                cred_manager = None
                
            self.progress.emit(10, f"Running {self.analyzer_name}...")
            
            # Filter bookmarks that need analysis (don't have topics/keywords)
            bookmarks_to_analyze = []
            for bookmark in self.bookmarks:
                if not bookmark.topics and not bookmark.keywords:
                    bookmarks_to_analyze.append(bookmark)
                    
            if not bookmarks_to_analyze:
                self.progress.emit(100, "No bookmarks need analysis")
                self.finished_success.emit(0)
                return
                
            self.progress.emit(20, f"Analyzing {len(bookmarks_to_analyze)} bookmarks...")
            
            # Run analyzer
            results = analyzer.analyze(bookmarks_to_analyze, analyzer_settings, cred_manager)
            
            self.progress.emit(80, "Saving results...")
            
            # Update storage with analyzed bookmarks
            for bookmark in bookmarks_to_analyze:
                storage.update_bookmark(bookmark.url, 
                                      topics=bookmark.topics,
                                      keywords=bookmark.keywords)
                                      
            # Save storage
            storage.save()
            
            processed = results.get("processed", 0)
            self.progress.emit(100, f"Analysis complete. Processed {processed} bookmarks.")
            self.finished_success.emit(processed)
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            self.failed.emit(str(e))