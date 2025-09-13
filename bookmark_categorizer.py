#!/usr/bin/env python3
"""
Automatic bookmark categorization
"""
import concurrent.futures
import logging
import urllib.parse
from typing import List, Dict

import requests
from bs4 import BeautifulSoup

from dead_links_manager import DeadLinksManager
from bookmark_extractor import Bookmark
dead_links_manager = DeadLinksManager()

logger = logging.getLogger(__name__)

# Predefined categories with related keywords and domain patterns
CATEGORIES = {
    "News & Media": {
        "keywords": ["news", "media", "journalism", "magazine", "newspaper", "press", "article"],
        "domains": ["cnn.com", "nytimes.com", "bbc.com", "reuters.com", "washingtonpost.com", "news"]
    },
    "Social Media": {
        "keywords": ["social", "network", "community", "share", "connect", "friend"],
        "domains": ["facebook.com", "twitter.com", "linkedin.com", "instagram.com", "tiktok.com", "social"]
    },
    "Shopping & Retail": {
        "keywords": ["shop", "store", "buy", "purchase", "product", "retail", "price", "discount", "deal"],
        "domains": ["amazon.com", "ebay.com", "walmart.com", "etsy.com", "shop", "store"]
    },
    "Technology": {
        "keywords": ["tech", "programming", "software", "hardware", "developer", "code", "computer", "digital"],
        "domains": ["github.com", "stackoverflow.com", "techcrunch.com", "wired.com", "cnet.com", "tech"]
    },
    "Education & Reference": {
        "keywords": ["learn", "course", "tutorial", "education", "academic", "university", "college", "school", "study"],
        "domains": ["wikipedia.org", "coursera.org", "edx.org", "udemy.com", "edu", "ac."]
    },
    "Entertainment": {
        "keywords": ["entertainment", "movie", "film", "tv", "television", "stream", "video", "game", "gaming", "music"],
        "domains": ["netflix.com", "youtube.com", "spotify.com", "twitch.tv", "imdb.com", "hulu.com"]
    },
    "Finance & Banking": {
        "keywords": ["finance", "bank", "invest", "money", "stock", "trading", "insurance", "loan", "credit"],
        "domains": ["paypal.com", "chase.com", "bankofamerica.com", "schwab.com", "bank", "finance"]
    },
    "Travel & Transportation": {
        "keywords": ["travel", "flight", "hotel", "vacation", "trip", "booking", "transport", "car", "rental"],
        "domains": ["booking.com", "airbnb.com", "expedia.com", "tripadvisor.com", "travel"]
    },
    "Health & Fitness": {
        "keywords": ["health", "fitness", "medical", "doctor", "workout", "exercise", "nutrition", "diet"],
        "domains": ["webmd.com", "mayoclinic.org", "healthline.com", "fitness", "health"]
    },
    "Productivity & Tools": {
        "keywords": ["productivity", "tool", "utility", "app", "organize", "note", "calendar", "reminder"],
        "domains": ["notion.so", "trello.com", "asana.com", "evernote.com", "todoist.com"]
    },
    "Uncategorized": {
        "keywords": [],
        "domains": []
    },
    "dead link": {
        "keywords": [],
        "domains": []
    }
}

def categorize_bookmarks(bookmarks: List[Bookmark]) -> Dict[str, List[Bookmark]]:
    """
    Categorize bookmarks based on URL, title, and optionally content
    
    Args:
        bookmarks: List of bookmarks to categorize
        
    Returns:
        Dict[str, List[Bookmark]]: Dictionary mapping categories to bookmark lists
    """
    categorized = {category: [] for category in CATEGORIES.keys()}
    
    # First pass: categorize based on URL and title
    uncategorized = []
    for bookmark in bookmarks:
        category = _categorize_bookmark(bookmark)
        if category != "Uncategorized":
            bookmark.category = category
            categorized[category].append(bookmark)
        else:
            uncategorized.append(bookmark)
    
    # Second pass for uncategorized: fetch page content for better categorization
    # Using a thread pool to speed up the process
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_bookmark = {
            executor.submit(_fetch_and_categorize, bookmark): bookmark 
            for bookmark in uncategorized[:100]  # Limit to first 100 to avoid excessive requests
        }
        
        for future in concurrent.futures.as_completed(future_to_bookmark):
            bookmark = future_to_bookmark[future]
            try:
                category = future.result()
                bookmark.category = category
                categorized[category].append(bookmark)
            except Exception as e:
                logger.error(f"Error categorizing {bookmark.url}: {e}")
                bookmark.category = "Uncategorized"
                categorized["Uncategorized"].append(bookmark)
    
    # Add remaining uncategorized bookmarks
    for bookmark in uncategorized[100:]:
        bookmark.category = "Uncategorized"
        categorized["Uncategorized"].append(bookmark)
    
    # Sort each category by title
    for category in categorized:
        categorized[category].sort(key=lambda b: b.title.lower())
    
    logger.info(f"Categorized {len(bookmarks)} bookmarks into {len(CATEGORIES)} categories")
    
    return categorized

def _categorize_bookmark(bookmark: Bookmark) -> str:
    """
    Categorize a single bookmark based on URL and title
    
    Args:
        bookmark: Bookmark to categorize
        
    Returns:
        str: Category name
    """
    url = bookmark.url.lower()
    title = bookmark.title.lower()

    if dead_links_manager.is_dead(bookmark.url):
        return "dead link"

    # Extract domain from URL
    try:
        parsed_url = urllib.parse.urlparse(url)
        domain = parsed_url.netloc
    except:
        domain = ""
    
    # Check domain patterns first
    for category, data in CATEGORIES.items():
        for domain_pattern in data["domains"]:
            if domain_pattern in domain:
                return category
    
    # Check keywords in title and URL
    scores = {category: 0 for category in CATEGORIES.keys()}
    
    for category, data in CATEGORIES.items():
        for keyword in data["keywords"]:
            if keyword in title:
                scores[category] += 2  # Title matches are weighted more
            if keyword in url:
                scores[category] += 1
    
    # Get category with highest score
    max_score = max(scores.values())
    if max_score > 0:
        for category, score in scores.items():
            if score == max_score:
                return category
    
    return "Uncategorized"

def _fetch_and_categorize(bookmark: Bookmark) -> str:
    """
    Fetch page content and categorize based on it
    
    Args:
        bookmark: Bookmark to categorize
        
    Returns:
        str: Category name
    """
    try:
        # First try basic categorization
        category = _categorize_bookmark(bookmark)
        if category != "Uncategorized":
            return category
        
        # Fetch page content with timeout
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(bookmark.url, headers=headers, timeout=5)
        response.raise_for_status()
        
        # Parse content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title, meta description, keywords, and body text
        page_title = soup.title.string if soup.title else ""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = meta_desc['content'] if meta_desc else ""
        
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        keywords = meta_keywords['content'] if meta_keywords else ""
        
        # Extract visible text (simplified)
        visible_text = soup.get_text()[:1000]  # First 1000 chars
        
        # Combine all text
        all_text = f"{page_title} {description} {keywords} {visible_text}".lower()
        
        # Score categories based on content
        scores = {category: 0 for category in CATEGORIES.keys()}
        
        for category, data in CATEGORIES.items():
            for keyword in data["keywords"]:
                scores[category] += all_text.count(keyword)
        
        # Get category with highest score
        max_score = max(scores.values())
        if max_score > 0:
            for category, score in scores.items():
                if score == max_score:
                    return category
        
        return "Uncategorized"
    
    except Exception as e:
        logger.error(f"Error fetching content for {bookmark.url}: {e}")
        if str(e).startswith("404"):
            dead_links_manager.add(bookmark.url)
        if str(e).startswith("403"):
            dead_links_manager.add(bookmark.url)
        return "Uncategorized"