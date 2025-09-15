from __future__ import annotations
from typing import Optional

from analyzers.base import Analyzer, AnalysisResult

# Reuse your existing KeyBERT wrapper
from keybert_keyword_extractor import KeyBERTKeywordExtractor


class KeyBERTAnalyzer(Analyzer):
    name = "KeyBERT (keywords)"

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", top_n: int = 5):
        self.impl = KeyBERTKeywordExtractor(model_name=model_name, top_n=top_n)
        self.top_n = top_n

    def extract(self, text: str, title: Optional[str] = None) -> AnalysisResult:
        kws = self.impl.extract_keywords(text)
        return AnalysisResult(keywords=kws[: self.top_n], topics=[])