from __future__ import annotations
from typing import Optional

from analyzers.base import Analyzer, AnalysisResult

# Reuse your existing Gemini wrapper
from gemini_keyword_extractor import GeminiKeywordExtractor


class GeminiAnalyzer(Analyzer):
    name = "Gemini (keywords)"

    def __init__(self, api_key: str, model: str = "gemini-1.5-pro-latest", top_n: int = 5, max_words: int = 1500):
        # GeminiKeywordExtractor already manages quotas via GeminiUsageManager
        self.impl = GeminiKeywordExtractor(api_key=api_key, model=model, max_words=max_words)
        self.top_n = top_n

    def extract(self, text: str, title: Optional[str] = None) -> AnalysisResult:
        kws = self.impl.extract_keywords(text) or []
        return AnalysisResult(keywords=kws[: self.top_n], topics=[])