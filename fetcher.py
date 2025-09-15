import logging
import time
from typing import Optional
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse


NON_HTML_EXTS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg",
    ".pdf", ".zip", ".rar", ".7z", ".tar", ".gz", ".mp3", ".mp4", ".mov",
    ".avi", ".mkv", ".wav", ".flac", ".ico", ".bin"
}


def _looks_like_binary_url(url: str) -> bool:
    try:
        path = urlparse(url).path.lower()
        for ext in NON_HTML_EXTS:
            if path.endswith(ext):
                return True
    except Exception:
        pass
    return False


def fetch_page_text(
    url: str,
    timeout: int = 15,
    max_words: int = 3000,
    sleep_between: float = 0.0,
    user_agent: Optional[str] = None
) -> str:
    """
    Fetch and extract visible text from a web page.
    Only processes HTML; returns "" for non-HTML (images, PDFs, binaries).
    """
    if _looks_like_binary_url(url):
        logging.info("Skipping non-HTML URL by extension: %s", url)
        return ""

    headers = {}
    if user_agent:
        headers["User-Agent"] = user_agent

    try:
        resp = requests.get(url, timeout=timeout, headers=headers)
        resp.raise_for_status()
    except Exception as e:
        logging.error(f"HTTP error for {url}: {e}")
        return ""

    # Guard on content-type
    ctype = (resp.headers.get("Content-Type") or "").lower()
    if "text/html" not in ctype:
        logging.info("Skipping non-HTML content-type (%s) for %s", ctype or "unknown", url)
        return ""

    try:
        soup = BeautifulSoup(resp.content, "html.parser")
        # Remove script/style
        for tag in soup(["script", "style", "noscript"]):
            tag.extract()
        text = soup.get_text(separator=" ", strip=True) or ""
        words = text.split()
        if sleep_between:
            time.sleep(sleep_between)
        return " ".join(words[:max_words])
    except Exception as e:
        logging.error(f"Parsing error for {url}: {e}")
        return ""