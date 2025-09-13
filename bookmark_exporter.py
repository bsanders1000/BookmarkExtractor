#!/usr/bin/env python3
"""
Export bookmarks to various formats
"""
import csv
import json
import logging
from typing import List
from pathlib import Path
from datetime import datetime

from bookmark_extractor import Bookmark

logger = logging.getLogger(__name__)

def export_bookmarks(bookmarks: List[Bookmark], output_path: str) -> bool:
    """
    Export bookmarks to a file
    
    Args
    """