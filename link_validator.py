#!/usr/bin/env python3
"""
Bookmark link validation
"""
import logging
import concurrent.futures
import requests
from typing import Dict, List

from bookmark_extractor import Bookmark

logger = logging.getLogger(__name__)

def validate_links(categorized_bookmarks: Dict[str, List[Bookmark]]) -> None:
    """
    Validate links in categorized bookmarks
    
    Args:
        categorized_bookmarks: Dictionary mapping categories to bookmark lists
    """
    logger.info("Starting link validation...")
    
    # Flatten bookmarks list
    all_bookmarks = []
    for category, bookmarks in categorized_bookmarks.items():
        all_bookmarks.extend(bookmarks)
    
    # Validate links in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_bookmark = {
            executor.submit(_validate_link, bookmark): bookmark for bookmark in all_bookmarks
        }
        
        validated_count = 0
        for future in concurrent.futures.as_completed(future_to_bookmark):
            bookmark = future_to_bookmark[future]
            try:
                is_valid = future.result()
                bookmark.is_valid = is_valid
                validated_count += 1
                
                # Log progress every 100 bookmarks
                if validated_count % 100 == 0:
                    logger.info(f"Validated {validated_count}/{len(all_bookmarks)} bookmarks")
            
            except Exception as e:
                logger.error(f"Error validating {bookmark.url}: {e}")
                bookmark.is_valid = False
    
    # Count invalid links
    invalid_count = sum(1 for bookmark in all_bookmarks if not bookmark.is_valid)
    logger.info(f"Link validation complete. Found {invalid_count} invalid links out of {len(all_bookmarks)}")

def _validate_link(bookmark: Bookmark) -> bool:
    """
    Validate a single bookmark link
    
    Args:
        bookmark: Bookmark to validate
        
    Returns:
        bool: True if link is valid, False otherwise
    """
    try:
        # Set a custom user agent to avoid some blocks
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        # Just check the HEAD response to save bandwidth
        response = requests.head(
            bookmark.url, 
            headers=headers, 
            timeout=5,
            allow_redirects=True
        )
        
        # If HEAD request fails, try GET request
        if response.status_code >= 400:
            response = requests.get(
                bookmark.url, 
                headers=headers, 
                timeout=5,
                allow_redirects=True,
                stream=True  # Don't download the whole content
            )
            # Close connection immediately
            response.close()
        
        return response.status_code < 400
    
    except requests.RequestException:
        return False
    except Exception as e:
        logger.error(f"Unexpected error validating {bookmark.url}: {e}")
        return False