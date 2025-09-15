import re
from typing import List, Dict, Any, Optional, Tuple

from bertopic import BERTopic
from sklearn.feature_extraction.text import CountVectorizer


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

    segments = [s for s in segments if len(s) >= max(100, min_chars // 2)]
    uniq = []
    seen = set()
    for s in segments:
        sig = re.sub(r"\W+", " ", s.lower()).strip()[:200]
        if sig in seen:
            continue
        seen.add(sig)
        uniq.append(s)
    return uniq[:200]


class SingleDocBERTopicExtractor:
    """
    Build topics within ONE document by clustering its segments using BERTopic.
    Returns a few topics and derived keywords for that bookmark.
    """

    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        nr_topics: Optional[int] = "auto",
        min_topic_size: int = 2,
        top_n_words: int = 10,
        vectorizer_max_df: float = 0.95,
        vectorizer_min_df: int = 1,
        ngram_range: Tuple[int, int] = (1, 2),
    ):
        self.embedding_model = embedding_model
        self.nr_topics = nr_topics
        self.min_topic_size = min_topic_size
        self.top_n_words = top_n_words
        self.vectorizer = CountVectorizer(
            stop_words="english",
            lowercase=True,
            max_df=vectorizer_max_df,
            min_df=vectorizer_min_df,
            ngram_range=ngram_range,
            token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z\-]+\b",
        )

    def extract(self, raw_text: str) -> Dict[str, Any]:
        text = re.sub(r"\s+", " ", raw_text or "").strip()
        if not text or len(text) < 50:
            return {"topics": [], "derived_keywords": []}

        segments = _simple_segments(text)
        if len(segments) < max(3, self.min_topic_size + 1):
            return self._fallback_keywords(text)

        model = BERTopic(
            embedding_model=self.embedding_model,
            nr_topics=self.nr_topics,
            calculate_probabilities=False,
            verbose=False,
            vectorizer_model=self.vectorizer,
            min_topic_size=self.min_topic_size,
            top_n_words=self.top_n_words,
        )

        topic_ids, _ = model.fit_transform(segments)
        topic_info = model.get_topic_info()
        topic_info = topic_info[topic_info.Topic != -1]
        if topic_info.empty:
            return self._fallback_keywords(text)

        topic_info = topic_info.sort_values(by="Count", ascending=False)

        topics_out = []
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
        return {"topics": topics_out, "derived_keywords": derived_keywords}

    def _fallback_keywords(self, text: str) -> Dict[str, Any]:
        analyzer = self.vectorizer.build_analyzer()
        tokens = analyzer(text)
        if not tokens:
            return {"topics": [], "derived_keywords": []}
        from collections import Counter
        counts = Counter(tokens)
        common = [t for t, _ in counts.most_common(10)]
        return {"topics": [], "derived_keywords": common[:5]}