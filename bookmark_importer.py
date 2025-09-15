#!/usr/bin/env python3
"""
Import bookmarks from various formats.
"""
import json
import csv
import logging
from bs4 import BeautifulSoup
from typing import List
from bookmark_extractor import Bookmark

logger = logging.getLogger(__name__)

def import_bookmarks(file_path: str) -> List[Bookmark]:
    """
    Import bookmarks from a file (HTML, JSON, or CSV).
    
    Args:
        file_path: Path to the file to import.
        
    Returns:
        List[Bookmark]: Imported bookmarks.
    """
    if file_path.lower().endswith('.html'):
        return _import_html_bookmarks(file_path)
    elif file_path.lower().endswith('.json'):
        return _import_json_bookmarks(file_path)
    elif file_path.lower().endswith('.csv'):
        return _import_csv_bookmarks(file_path)
    else:
        logger.error(f"Unsupported file format for {file_path}")
        return []

def _import_html_bookmarks(file_path: str) -> List[Bookmark]:
    """Import bookmarks from an HTML file (Netscape/Chrome format)."""
    bookmarks = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
        for a_tag in soup.find_all('a'):
            url = a_tag.get('href', '')
            title = a_tag.get_text(strip=True)
            folder_path = ""
            parent = a_tag.find_parent(['dl', 'ul', 'ol'])
            if parent:
                folder = parent.find_previous('h3')
                if folder:
                    folder_path = folder.get_text(strip=True)
            bookmark = Bookmark(
                url=url,
                title=title,
                browser_source="Imported HTML",
                folder_path=folder_path
            )
            bookmarks.append(bookmark)
    except Exception as e:
        logger.error(f"Error importing HTML bookmarks: {e}")
    return bookmarks

def _import_json_bookmarks(file_path: str) -> List[Bookmark]:
    """Import bookmarks from a JSON file."""
    bookmarks = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Expecting a list of dicts with at least url, title
        for entry in data:
            url = entry.get('url', '')
            title = entry.get('title', '')
            folder_path = entry.get('folder_path', '')
            browser_source = entry.get('browser_source', 'Imported JSON')
            bookmark = Bookmark(
                url=url,
                title=title,
                browser_source=browser_source,
                folder_path=folder_path
            )
            bookmarks.append(bookmark)
    except Exception as e:
        logger.error(f"Error importing JSON bookmarks: {e}")
    return bookmarks

def _import_csv_bookmarks(file_path: str) -> List[Bookmark]:
    """Import bookmarks from a CSV file."""
    bookmarks = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row.get('url', '')
                title = row.get('title', '')
                folder_path = row.get('folder_path', '')
                browser_source = row.get('browser_source', 'Imported CSV')
                bookmark = Bookmark(
                    url=url,
                    title=title,
                    browser_source=browser_source,
                    folder_path=folder_path
                )
                bookmarks.append(bookmark)
    except Exception as e:
        logger.error(f"Error importing CSV bookmarks: {e}")
    return bookmarks