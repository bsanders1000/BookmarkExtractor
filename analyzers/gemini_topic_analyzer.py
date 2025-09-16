#!/usr/bin/env python3
"""
Gemini Topic Analyzer - LLM-based topic and keyword extraction using Google Gemini
"""
import os
import json
import time
import sqlite3
import logging
import hashlib
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from bookmark_extractor import Bookmark
from credential_manager import CredentialManager

logger = logging.getLogger(__name__)

class GeminiTopicAnalyzer:
    """LLM-based topic and keyword analyzer using Google Gemini"""
    
    def __init__(self):
        self.name = "Gemini Topic/Keyword Analyzer"
        self.cache_dir = Path.home() / ".bookmark_aggregator" / "gemini_cache"
        self.rate_limit_db = Path.home() / ".bookmark_aggregator" / "gemini_rate_limit.db"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limit_db.parent.mkdir(parents=True, exist_ok=True)
        self._init_rate_limit_db()
        
    def get_name(self) -> str:
        """Get analyzer name"""
        return self.name
        
    def get_settings_schema(self) -> Dict[str, Any]:
        """Get settings schema for GUI configuration"""
        return {
            "gemini_api_key": {
                "type": "password",
                "label": "Gemini API Key",
                "description": "Google AI Studio API key (optional if using env var or credential manager)",
                "required": False
            },
            "use_free_tier": {
                "type": "boolean",
                "label": "Use Free Tier Limits",
                "description": "Enable rate limiting for free tier usage",
                "default": True
            },
            "batch_delay_sec": {
                "type": "float",
                "label": "Batch Delay (seconds)",
                "description": "Delay between API calls",
                "default": 4.0,
                "min": 1.0,
                "max": 60.0
            },
            "max_retries": {
                "type": "integer",
                "label": "Max Retries",
                "description": "Maximum retry attempts for failed calls",
                "default": 3,
                "min": 1,
                "max": 10
            },
            "max_chars_per_doc": {
                "type": "integer",
                "label": "Max Characters per Document",
                "description": "Maximum characters to send to API",
                "default": 10000,
                "min": 1000,
                "max": 50000
            },
            "min_text_length": {
                "type": "integer",
                "label": "Minimum Text Length",
                "description": "Skip documents shorter than this",
                "default": 600,
                "min": 100,
                "max": 5000
            },
            "top_keywords": {
                "type": "integer",
                "label": "Top Keywords Count",
                "description": "Number of top keywords to extract",
                "default": 10,
                "min": 5,
                "max": 20
            }
        }
        
    def analyze(self, bookmarks: List[Bookmark], settings: Optional[Dict] = None, 
                cred_manager: Optional[CredentialManager] = None) -> Dict[str, Any]:
        """Analyze bookmarks to extract topics and keywords"""
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai package not available")
            
        settings = settings or {}
        api_key = self._get_api_key(settings, cred_manager)
        
        if not api_key:
            raise ValueError("No Gemini API key found. Set GEMINI_API_KEY env var, "
                           "provide in settings, or configure in credential manager")
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # Settings
        use_free_tier = settings.get("use_free_tier", True)
        batch_delay = settings.get("batch_delay_sec", 4.0)
        max_retries = settings.get("max_retries", 3)
        max_chars = settings.get("max_chars_per_doc", 10000)
        min_text_length = settings.get("min_text_length", 600)
        top_keywords = settings.get("top_keywords", 10)
        
        results = {
            "processed": 0,
            "skipped": 0,
            "errors": 0,
            "cached": 0,
            "api_calls": 0
        }
        
        for bookmark in bookmarks:
            try:
                # Check rate limits
                if use_free_tier and not self._check_rate_limit():
                    logger.warning("Rate limit exceeded, skipping remaining bookmarks")
                    break
                
                # Get page content
                content = self._fetch_page_content(bookmark.url, max_chars)
                if not content or len(content) < min_text_length:
                    results["skipped"] += 1
                    continue
                
                # Check cache
                cache_key = self._get_cache_key(bookmark.url, content[:500])
                cached_result = self._get_cached_result(cache_key)
                
                if cached_result:
                    bookmark.topics = cached_result.get("topics", [])
                    bookmark.keywords = cached_result.get("keywords", [])
                    results["cached"] += 1
                    results["processed"] += 1
                    continue
                
                # Analyze with Gemini
                analysis = self._analyze_with_gemini(content, top_keywords, max_retries)
                
                if analysis:
                    bookmark.topics = analysis.get("topics", [])
                    bookmark.keywords = analysis.get("keywords", [])
                    
                    # Cache result
                    self._cache_result(cache_key, analysis)
                    
                    # Record API call
                    self._record_api_call()
                    
                    results["api_calls"] += 1
                    results["processed"] += 1
                    
                    # Rate limiting delay
                    if use_free_tier:
                        time.sleep(batch_delay)
                else:
                    results["errors"] += 1
                    
            except Exception as e:
                logger.error(f"Error analyzing bookmark {bookmark.url}: {e}")
                results["errors"] += 1
                
        return results
        
    def _get_api_key(self, settings: Dict[str, Any], cred_manager: Optional[CredentialManager]) -> Optional[str]:
        """Get API key from various sources"""
        # 1. Analyzer settings
        api_key = settings.get("gemini_api_key")
        if api_key:
            return api_key
            
        # 2. Environment variable
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            return api_key
            
        # 3. Credential manager
        if cred_manager:
            try:
                creds = cred_manager.get_credentials("gemini")
                if creds:
                    return creds.get("password") or creds.get("api_key")
            except Exception:
                pass
                
        return None
        
    def _init_rate_limit_db(self):
        """Initialize rate limiting database"""
        try:
            with sqlite3.connect(self.rate_limit_db) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS api_calls (
                        timestamp INTEGER PRIMARY KEY,
                        tokens_used INTEGER DEFAULT 0
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize rate limit DB: {e}")
            
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits (15 RPM for free tier)"""
        try:
            current_time = int(time.time())
            minute_ago = current_time - 60
            
            with sqlite3.connect(self.rate_limit_db) as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM api_calls WHERE timestamp > ?",
                    (minute_ago,)
                )
                calls_last_minute = cursor.fetchone()[0]
                
            return calls_last_minute < 15  # Free tier limit
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return True  # Allow if we can't check
            
    def _record_api_call(self, tokens_used: int = 0):
        """Record an API call for rate limiting"""
        try:
            with sqlite3.connect(self.rate_limit_db) as conn:
                conn.execute(
                    "INSERT INTO api_calls (timestamp, tokens_used) VALUES (?, ?)",
                    (int(time.time()), tokens_used)
                )
                conn.commit()
                
                # Clean up old records (older than 1 hour)
                hour_ago = int(time.time()) - 3600
                conn.execute("DELETE FROM api_calls WHERE timestamp < ?", (hour_ago,))
                conn.commit()
        except Exception as e:
            logger.error(f"Error recording API call: {e}")
            
    def _fetch_page_content(self, url: str, max_chars: int) -> Optional[str]:
        """Fetch and clean page content"""
        try:
            # Skip known binary/document formats
            if any(url.lower().endswith(ext) for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', 
                                                         '.ppt', '.pptx', '.zip', '.rar', '.exe',
                                                         '.jpg', '.jpeg', '.png', '.gif', '.svg']):
                return None
                
            headers = {
                'User-Agent': 'BookmarkTopicBot/1.0 (Content Analysis)'
            }
            
            response = requests.get(url, headers=headers, timeout=10, stream=True)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if not any(ct in content_type for ct in ['text/html', 'text/plain', 'application/xhtml']):
                return None
                
            # Get content with size limit
            content = ""
            for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
                if chunk:
                    content += chunk
                    if len(content) > max_chars:
                        content = content[:max_chars]
                        break
                        
            # Basic HTML cleaning using simple text extraction
            if 'html' in content_type:
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Remove script and style elements
                    for script in soup(["script", "style", "nav", "header", "footer"]):
                        script.decompose()
                        
                    text = soup.get_text()
                    # Clean up whitespace
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    content = ' '.join(chunk for chunk in chunks if chunk)
                except ImportError:
                    # Fallback basic cleaning without BeautifulSoup
                    import re
                    content = re.sub(r'<[^>]+>', '', content)
                    content = re.sub(r'\s+', ' ', content).strip()
                    
            return content[:max_chars] if content else None
            
        except Exception as e:
            logger.debug(f"Failed to fetch content for {url}: {e}")
            return None
            
    def _get_cache_key(self, url: str, content_sample: str) -> str:
        """Generate cache key for content"""
        combined = f"{url}:{content_sample}"
        return hashlib.md5(combined.encode()).hexdigest()
        
    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached analysis result"""
        try:
            cache_file = self.cache_dir / f"{cache_key}.json"
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.debug(f"Error reading cache for {cache_key}: {e}")
        return None
        
    def _cache_result(self, cache_key: str, result: Dict[str, Any]):
        """Cache analysis result"""
        try:
            cache_file = self.cache_dir / f"{cache_key}.json"
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error caching result for {cache_key}: {e}")
            
    def _analyze_with_gemini(self, content: str, top_keywords: int, max_retries: int) -> Optional[Dict[str, Any]]:
        """Analyze content with Gemini API"""
        prompt = f"""
        Analyze the following web page content and extract:
        1. Primary topic (main subject/theme)
        2. Secondary topics (2-3 related themes)
        3. Top {top_keywords} most relevant keywords

        Return the analysis as a JSON object with this exact structure:
        {{
            "topics": ["primary topic", "secondary topic 1", "secondary topic 2"],
            "keywords": ["keyword1", "keyword2", "keyword3", ...]
        }}

        Content to analyze:
        {content[:8000]}
        """
        
        for attempt in range(max_retries):
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                response = model.generate_content(
                    prompt,
                    safety_settings={
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                    }
                )
                
                if response.text:
                    # Try to extract JSON from response
                    text = response.text.strip()
                    
                    # Find JSON in response (might be wrapped in markdown)
                    import re
                    json_match = re.search(r'\{.*\}', text, re.DOTALL)
                    if json_match:
                        json_text = json_match.group()
                        try:
                            result = json.loads(json_text)
                            
                            # Validate structure
                            if "topics" in result and "keywords" in result:
                                # Ensure topics and keywords are lists of strings
                                result["topics"] = [str(t) for t in result["topics"][:3]]  # Max 3 topics
                                result["keywords"] = [str(k) for k in result["keywords"][:top_keywords]]
                                return result
                        except json.JSONDecodeError:
                            pass
                            
                    # Fallback: try to parse the response directly
                    try:
                        result = json.loads(text)
                        if "topics" in result and "keywords" in result:
                            result["topics"] = [str(t) for t in result["topics"][:3]]
                            result["keywords"] = [str(k) for k in result["keywords"][:top_keywords]]
                            return result
                    except json.JSONDecodeError:
                        pass
                        
            except Exception as e:
                logger.warning(f"Gemini API attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    
        logger.error("Failed to get valid response from Gemini API after all retries")
        return None