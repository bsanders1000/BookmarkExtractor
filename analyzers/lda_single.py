from __future__ import annotations
import re
from typing import List, Dict, Any, Optional, Tuple

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation

from analyzers.base import Analyzer, AnalysisResult


def _simple_segments(text: str, min_chars: int = 200, max_chars: int = 1200) -> List[str]:
    """
    Split text into paragraph-ish segments, then merge small ones and cap overly long ones.
    """
    paras = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    segments: List[str] = []

    def _yield_chunks(p: str):
        if len(p) <= max_chars:
            return [p]
        chunks = []
        start = 0
        while start < len(p):
            end = min(start + max_chars, len(p))
            cut = p.rfind(". ", start, end)
            if cut == -1 or cut < start + int(0.5 * max_chars):
                cut = end
            else:
                cut = cut + 2
            chunks.append(p[start:cut].strip())
            start = cut
        return chunks

    small_buffer = []
    for p in paras:
        chunks = _yield_chunks(p)
        for c in chunks:
            if len(c) < min_chars:
                small_buffer.append(c)
                joined = " ".join(small_buffer)
                if len(joined) >= min_chars:
                    segments.append(joined)
                    small_buffer = []
            else:
                if small_buffer:
                    joined = " ".join([*small_buffer, c])
                    if len(joined) <= max_chars * 1.5:
                        segments.append(joined)
                        small_buffer = []
                    else:
                        segments.append(" ".join(small_buffer))
                        segments.append(c)
                        small_buffer = []
                else:
                    segments.append(c)
    if small_buffer:
        segments.append(" ".join(small_buffer))

    segments = [s for s in segments if len(s) >= 100]
    uniq = []
    seen = set()
    for s in segments:
        sig = re.sub(r"\W+", " ", s.lower()).strip()[:200]
        if sig in seen:
            continue
        seen.add(sig)
        uniq.append(s)
    return uniq[:200]


class LDASingleDocAnalyzer(Analyzer):
    """
    Per-bookmark LDA: treat a single page's segments as documents, fit LDA,
    and return dominant topics with keywords. Keywords are taken from the
    highest-mass topic as the bookmark's derived keywords.
    """
    name = "LDA (per-bookmark)"

    def __init__(
        self,
        n_topics: int = 5,
        max_features: int = 20000,
        top_n_words: int = 10,
        min_df: int = 1,
        max_df: float = 0.95,
        ngram_range: Tuple[int, int] = (1, 2),
        random_state: int = 42,
        max_iter: int = 15,
        learning_method: str = "batch",
    ):
        if n_topics < 2:
            n_topics = 2
        self.n_topics = n_topics
        self.max_features = max_features
        self.top_n_words = top_n_words
        self.random_state = random_state
        self.max_iter = max_iter
        self.learning_method = learning_method
        self.vectorizer = CountVectorizer(
            stop_words="english",
            lowercase=True,
            max_df=max_df,
            min_df=min_df,
            max_features=max_features,
            ngram_range=ngram_range,
            token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z\-]+\b",
        )

    def extract(self, text: str, title: Optional[str] = None) -> AnalysisResult:
        clean = re.sub(r"\s+", " ", text or "").strip()
        if not clean or len(clean) < 50:
            return self._fallback(title or "")

        segments = _simple_segments(clean)
        if len(segments) < max(3, self.n_topics):
            return self._fallback(clean)

        # Vectorize segments
        X = self.vectorizer.fit_transform(segments)
        if X.shape[0] < 2 or X.shape[1] == 0:
            return self._fallback(clean)

        # Fit LDA (evaluate_every must be an int on some sklearn versions; 0 disables eval)
        lda = LatentDirichletAllocation(
            n_components=min(self.n_topics, max(2, X.shape[0] - 1)),
            max_iter=self.max_iter,
            learning_method=self.learning_method,
            random_state=self.random_state,
            evaluate_every=0,  # was None; 0 works across sklearn versions
        )
        try:
            lda.fit(X)
        except Exception:
            # If anything goes wrong (e.g., degenerate vocab), gracefully fall back
            return self._fallback(clean)

        # Soft topic mass across segments
        import numpy as np
        doc_topic = lda.transform(X)  # shape: (n_segments, n_topics)
        topic_mass = doc_topic.sum(axis=0)  # (n_topics,)
        total_mass = float(topic_mass.sum()) or 1.0

        # Build per-topic keyword lists
        feature_names = self.vectorizer.get_feature_names_out()
        topics_out: List[Dict[str, Any]] = []
        order = np.argsort(-topic_mass)  # descending by mass

        for rank, tid in enumerate(order):
            comp = lda.components_[tid]
            top_idx = comp.argsort()[::-1][: self.top_n_words]
            keywords = [{"word": str(feature_names[i]), "score": float(comp[i])} for i in top_idx]
            prob = float(topic_mass[tid] / total_mass)
            topics_out.append(
                {
                    "topic_id": int(tid),
                    "probability": prob,
                    "keywords": keywords,
                    "representation": [kw["word"] for kw in keywords],
                }
            )

        derived_keywords = topics_out[0]["representation"][:5] if topics_out else []
        return AnalysisResult(keywords=derived_keywords, topics=topics_out)

    def _fallback(self, text: str) -> AnalysisResult:
        analyzer = self.vectorizer.build_analyzer()
        tokens = analyzer(text)
        if not tokens:
            return AnalysisResult(keywords=[], topics=[])
        from collections import Counter
        common = [t for t, _ in Counter(tokens).most_common(10)]
        return AnalysisResult(keywords=common[:5], topics=[])