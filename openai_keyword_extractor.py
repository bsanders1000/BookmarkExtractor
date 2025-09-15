import openai
import logging
import requests
from bs4 import BeautifulSoup
import time
from typing import List

logger = logging.getLogger(__name__)

class OpenAIKeywordExtractor:
    def __init__(self, api_key, model="gpt-3.5-turbo-0125", max_requests_per_minute=20):
        self.api_key = api_key  # <-- THIS LINE IS REQUIRED
        self.model = model
        self.max_requests_per_minute = max_requests_per_minute
        self.requests_this_minute = 0
        self.minute_start_time = time.time()

    def extract_keywords(self, url: str) -> List[str]:
        now = time.time()
        if now - self.minute_start_time >= 60:
            self.minute_start_time = now
            self.requests_this_minute = 0
        if self.requests_this_minute >= self.max_requests_per_minute:
            sleep_time = 60 - (now - self.minute_start_time)
            logger.info(f"Rate limit reached, sleeping for {sleep_time:.1f} seconds.")
            time.sleep(max(sleep_time, 0))
            self.minute_start_time = time.time()
            self.requests_this_minute = 0

        self.requests_this_minute += 1

        try:
            resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            text = soup.get_text(separator=' ', strip=True)
            text = text[:5000]
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return []

        prompt = (
            "You are an expert web content analyst. "
            "Given the following web page content, respond ONLY with a comma-separated list of 3 to 5 keywords or short phrases that best describe the main themes or topics. "
            "Do not add extra commentary or explanation. Content:\n\n"
            f"{text}"
        )

        try:
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0.3,
            )
            keywords_text = response.choices[0].message.content
            keywords = [k.strip() for k in keywords_text.replace('\n', '').split(',') if k.strip()]
            return keywords[:5]
        except Exception as e:
            logger.error(f"OpenAI API failed for {url}: {e}")
            return []