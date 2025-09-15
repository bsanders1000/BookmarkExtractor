import google.generativeai as genai
import logging
from gemini_usage_manager import GeminiUsageManager

logger = logging.getLogger(__name__)

class GeminiKeywordExtractor:
    def __init__(self, api_key, model="gemini-1.5-pro-latest", max_words=1500):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.usage_manager = GeminiUsageManager()
        self.max_words = max_words  # Limit input size per request

    def prepare_text_for_llm(self, text):
        words = text.split()
        return " ".join(words[:self.max_words])

    def extract_keywords(self, text: str) -> list:
        short_text = self.prepare_text_for_llm(text)
        tokens_needed = len(short_text.split()) + 50  # Estimate conservatively

        allowed, msg = self.usage_manager.can_request(tokens_needed)
        if not allowed:
            logger.error(f"Gemini API limit: {msg}")
            return []

        prompt = (
            "You are an expert web content analyst. "
            "Given the following web page content, respond ONLY with a comma-separated list of 3 to 5 keywords or short phrases that best describe the main themes or topics. "
            "Do not add extra commentary or explanation. Content:\n\n"
            f"{short_text}"
        )

        try:
            response = self.model.generate_content(prompt)
            tokens_used = (
                response.prompt_feedback.input_token_count +
                response.prompt_feedback.output_token_count
            )
            self.usage_manager.update(tokens_used)
            keywords_text = response.text
            keywords = [k.strip() for k in keywords_text.replace('\n', '').split(',') if k.strip()]
            return keywords[:5]
        except Exception as e:
            logger.error(f"Gemini API failed: {e}")
            return []