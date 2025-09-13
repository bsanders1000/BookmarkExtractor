#!/usr/bin/env python3
"""
Extract bookmarks from various browsers
"""
import os
import json
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from browser_detector import BrowserInfo

logger = logging.getLogger(__name__)

class Bookmark:
    def __init__(self, url: str, title: str, browser_source: str,
                 date_added: Optional[int] = None,
                 folder_path: Optional[str] = None,
                 icon_url: Optional[str] = None,
                 tags: Optional[List[str]] = None,
                 keywords: Optional[List[str]] = None,
                 topics: Optional[List[str]] = None):
        self.url = url
        self.title = title
        self.browser_source = browser_source
        self.date_added = date_added
        self.folder_path = folder_path or ""
        self.icon_url = icon_url
        self.tags = tags or []
        self.category = ""
        self.is_valid = True
        # self.keywords = keywords or []
        # Avoid mutable default pitfalls
        self.keywords = keywords if keywords is not None else []
        self.topics = topics if topics is not None else []

def extract_bookmarks(browser: BrowserInfo, credentials: Optional[Dict[str, str]] = None) -> List[Bookmark]:
    """
    Extract bookmarks from a browser
    
    Args:
        browser: Browser information
        credentials: Optional credentials for accessing browser data
        
    Returns:
        List[Bookmark]: List of extracted bookmarks
    """
    logger.info(f"Extracting bookmarks from {browser.name}")
    
    if browser.id == "chrome" or browser.id == "edge" or browser.id == "brave":
        return _extract_chrome_bookmarks(browser)
    elif browser.id == "firefox":
        return _extract_firefox_bookmarks(browser)
    elif browser.id == "safari":
        return _extract_safari_bookmarks(browser, credentials)
    else:
        logger.warning(f"Unsupported browser: {browser.id}")
        return []

def _extract_chrome_bookmarks(browser: BrowserInfo) -> List[Bookmark]:
    """Extract bookmarks from Chrome, Edge, or other Chromium-based browsers"""
    bookmarks = []
    
    # Chrome stores bookmarks in a JSON file
    bookmarks_file = browser.profile_path / "Default" / "Bookmarks"
    if not bookmarks_file.exists():
        # Try to find other profile folders
        profiles = [p for p in browser.profile_path.glob("*") if p.is_dir() and p.name.startswith("Profile")]
        for profile in profiles:
            bookmarks_file = profile / "Bookmarks"
            if bookmarks_file.exists():
                break
    
    if not bookmarks_file.exists():
        logger.warning(f"No bookmarks file found for {browser.name}")
        return bookmarks
    
    try:
        with open(bookmarks_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Process bookmark folders
        roots = data.get('roots', {})
        for root_name, root in roots.items():
            _process_chrome_bookmark_node(root, bookmarks, browser.name, [root_name])
        
        logger.info(f"Extracted {len(bookmarks)} bookmarks from {browser.name}")
        return bookmarks
    
    except Exception as e:
        logger.error(f"Error extracting bookmarks from {browser.name}: {e}")
        return bookmarks

def _process_chrome_bookmark_node(node: Dict[str, Any], bookmarks: List[Bookmark], 
                                 browser_name: str, folder_path: List[str]) -> None:
    """Process a node in the Chrome bookmarks tree recursively"""
    if node.get('type') == 'url':
        # This is a bookmark
        bookmark = Bookmark(
            url=node.get('url', ''),
            title=node.get('name', ''),
            browser_source=browser_name,
            date_added=node.get('date_added'),
            folder_path='/'.join(folder_path),
            icon_url=None
        )
        bookmarks.append(bookmark)
    
    elif node.get('type') == 'folder':
        # This is a folder, process its children
        children = node.get('children', [])
        for child in children:
            _process_chrome_bookmark_node(
                child, 
                bookmarks, 
                browser_name, 
                folder_path + [node.get('name', 'Unnamed Folder')]
            )

def _extract_firefox_bookmarks(browser: BrowserInfo) -> List[Bookmark]:
    """Extract bookmarks from all available Firefox profiles"""
    bookmarks = []
    profiles_dir = browser.profile_path

    # Read profiles.ini to find all profiles
    profiles_ini = profiles_dir / "profiles.ini"
    profile_paths = []
    if profiles_ini.exists():
        import configparser
        config = configparser.ConfigParser()
        config.read(str(profiles_ini))
        for section in config.sections():
            if config.has_option(section, "Path"):
                rel_path = config.get(section, "Path")
                is_relative = config.get(section, "IsRelative", fallback="1") == "1"
                profile_path = profiles_dir / rel_path if is_relative else Path(rel_path)
                if (profile_path / "places.sqlite").exists():
                    profile_paths.append(profile_path)
    else:
        # Fallback: any subdirectory with places.sqlite
        profile_paths = [p for p in profiles_dir.glob("*") if (p / "places.sqlite").exists()]

    for profile_dir in profile_paths:
        places_db = profile_dir / "places.sqlite"
        try:
            import tempfile, shutil, sqlite3
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = temp_file.name
            shutil.copy2(places_db, temp_path)
            conn = sqlite3.connect(f"file:{temp_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            # FIXED QUERY: removed p.favicon_id
            query = """
            SELECT b.title, p.url, b.dateAdded, b.parent
            FROM moz_bookmarks b
            JOIN moz_places p ON b.fk = p.id
            WHERE b.type = 1
            """
            cursor.execute(query)
            bookmark_rows = cursor.fetchall()
            # Get folder structure for paths
            query = """
            SELECT id, title, parent
            FROM moz_bookmarks
            WHERE type = 2
            """
            cursor.execute(query)
            folder_rows = cursor.fetchall()
            folder_map = {row[0]: (row[1], row[2]) for row in folder_rows}
            for row in bookmark_rows:
                title, url, date_added, parent = row
                folder_path = []
                current_parent = parent
                while current_parent in folder_map:
                    folder_name, current_parent = folder_map[current_parent]
                    folder_path.insert(0, folder_name)
                bookmark = Bookmark(
                    url=url,
                    title=title or "",
                    browser_source=browser.name,
                    date_added=date_added,
                    folder_path='/'.join(folder_path),
                    icon_url=None
                )
                bookmarks.append(bookmark)
            conn.close()
            os.unlink(temp_path)
        except Exception as e:
            logger.error(f"Error extracting bookmarks from profile {profile_dir}: {e}")
    logger.info(f"Extracted {len(bookmarks)} bookmarks from Firefox")
    return bookmarks

def _extract_safari_bookmarks(browser: BrowserInfo, credentials: Optional[Dict[str, str]]) -> List[Bookmark]:
    """Extract bookmarks from Safari"""
    bookmarks = []
    
    # Safari bookmarks are stored in a plist file
    bookmarks_file = browser.profile_path / "Bookmarks.plist"
    
    if not bookmarks_file.exists():
        logger.warning(f"No bookmarks file found for {browser.name}")
        return bookmarks
    
    try:
        # Use plistlib to parse Safari bookmarks
        import plistlib
        
        with open(bookmarks_file, 'rb') as f:
            data = plistlib.load(f)
        
        # Process Safari bookmarks recursively
        _process_safari_bookmark_node(data, bookmarks, browser.name, [])
        
        logger.info(f"Extracted {len(bookmarks)} bookmarks from {browser.name}")
        return bookmarks
    
    except Exception as e:
        logger.error(f"Error extracting bookmarks from {browser.name}: {e}")
        return bookmarks

def _process_safari_bookmark_node(node: Dict[str, Any], bookmarks: List[Bookmark], 
                                 browser_name: str, folder_path: List[str]) -> None:
    """Process a node in the Safari bookmarks tree recursively"""
    # Safari bookmark structure is different from Chrome/Firefox
    # This is a simplified implementation
    if node.get('WebBookmarkType') == 'WebBookmarkTypeLeaf':
        # This is a bookmark
        url = node.get('URLString')
        if url:
            bookmark = Bookmark(
                url=url,
                title=node.get('Title', ''),
                browser_source=browser_name,
                date_added=node.get('DateAdded'),
                folder_path='/'.join(folder_path),
                icon_url=None
            )
            bookmarks.append(bookmark)
    
    elif node.get('WebBookmarkType') == 'WebBookmarkTypeList':
        # This is a folder
        children = node.get('Children', [])
        for child in children:
            _process_safari_bookmark_node(
                child, 
                bookmarks, 
                browser_name, 
                folder_path + [node.get('Title', 'Unnamed Folder')] if 'Title' in node else folder_path
            )