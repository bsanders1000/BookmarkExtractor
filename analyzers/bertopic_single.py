from __future__ import annotations
import re
import logging
from typing import List, Dict, Any, Optional, Tuple

from bertopic import BERTopic
from sklearn.feature_extraction.text import CountVectorizer
from umap import UMAP

from analyzers.base import Analyzer, AnalysisResult

logger = logging.getLogger(__name__)


def _simple_segments(text: str, min_chars: int = 200, max_chars: int = 1200) -> List[str]:
    # ... keep your existing implementation ...
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


class BERTopicSingleDocAnalyzer(Analyzer):
    name = "BERTopic (per-bookmark)"

    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        nr_topics: Optional[int] = "auto",
        min_topic_size: int = 2,
        top_n_words: int = 10,
        vectorizer_max_df: float = 0.95,
        vectorizer_min_df: int = 1,
        ngram_range: Tuple[int, int] = (1, 2),
        min_segments_for_bertopic: int = 3,  # NEW: configurable threshold
    ):
        self.embedding_model = embedding_model
        self.nr_topics = nr_topics
        self.min_topic_size = min_topic_size
        self.top_n_words = top_n_words
        self.min_segments_for_bertopic = min_segments_for_bertopic
        self.vectorizer = CountVectorizer(
            stop_words="english",
            lowercase=True,
            max_df=vectorizer_max_df,
            min_df=vectorizer_min_df,
            ngram_range=ngram_range,
            token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z\-]+\b",
        )

    def extract(self, text: str, title: Optional[str] = None) -> AnalysisResult:
        clean = re.sub(r"\s+", " ", text or "").strip()
        if not clean or len(clean) < 50:
            return self._fallback(title or "")

        segments = _simple_segments(clean)
        n = len(segments)
        logger.debug("BERTopicSingleDocAnalyzer: segments=%d", n)

        if n < max(self.min_segments_for_bertopic, self.min_topic_size + 1):
            return self._fallback(clean)

        # Ensure we never hit UMAP spectral k >= N issues; also bypass spectral with init="random".
        umap_n_components = min(5, max(2, n - 2))     # ensures (n_components + 1) <= n - 1 < n
        umap_n_neighbors = min(15, max(2, n - 1))
        umap_model = UMAP(
            n_neighbors=umap_n_neighbors,
            n_components=umap_n_components,
            metric="cosine",
            random_state=42,
            init="random",
        )
        logger.debug("UMAP params: n_neighbors=%d n_components=%d", umap_n_neighbors, umap_n_components)

        model = BERTopic(
            embedding_model=self.embedding_model,
            nr_topics=self.nr_topics,
            calculate_probabilities=False,
            verbose=False,
            vectorizer_model=self.vectorizer,
            min_topic_size=self.min_topic_size,
            top_n_words=self.top_n_words,
            umap_model=umap_model,
        )

        try:
            _, _ = model.fit_transform(segments)
        except Exception as e:
            # Last-resort fallback in case UMAP/BERTopic fails for tiny or weird inputs
            logger.warning("BERTopic fit failed for single doc: %s; falling back to keywords.", e)
            return self._fallback(clean)

        topic_info = model.get_topic_info()
        topic_info = topic_info[topic_info.Topic != -1]
        if topic_info.empty:
            return self._fallback(clean)

        topic_info = topic_info.sort_values(by="Count", ascending=False)

        topics_out: List[Dict[str, Any]] = []
        total = int(topic_info["Count"].sum()) or 1
        for _, row in topic_info.iterrows():
            tid = int(row["Topic"])
            words = model.get_topic(tid) or []
            keywords = [{"word": w, "score": float(s)} for w, s in words[: self.top_n_words]]
            prob = float(row["Count"]) / float(total)
            topics_out.append(
                {
                    "topic_id": tid,
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
        from collections import Counter
        common = [t for t, _ in Counter(tokens).most_common(10)] if tokens else []
        return AnalysisResult(keywords=common[:5], topics=[])