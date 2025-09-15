from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Protocol


@dataclass
class AnalysisResult:
    keywords: List[str]
    topics: List[Dict[str, Any]]  # Keep same structure used elsewhere for compatibility


class Analyzer(Protocol):
    name: str

    def extract(self, text: str, title: Optional[str] = None) -> AnalysisResult:
        """
        Return AnalysisResult for a single document's text.
        Implementations may ignore title.
        """
        ...