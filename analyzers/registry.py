from __future__ import annotations
from typing import Dict, Callable, Any, List

from analyzers.base import Analyzer
from analyzers.bertopic_single import BERTopicSingleDocAnalyzer

# Optional adapters (import guarded)
try:
    from analyzers.keybert_adapter import KeyBERTAnalyzer
except Exception:  # pragma: no cover
    KeyBERTAnalyzer = None  # type: ignore

try:
    from analyzers.gemini_adapter import GeminiAnalyzer
except Exception:  # pragma: no cover
    GeminiAnalyzer = None  # type: ignore

try:
    from analyzers.lda_single import LDASingleDocAnalyzer
except Exception:  # pragma: no cover
    LDASingleDocAnalyzer = None  # type: ignore


def build_registry(config: Dict[str, Any]) -> Dict[str, Callable[[], Analyzer]]:
    """
    Returns a factory registry of available analyzers.
    Config can include:
      - keybert.model_name, keybert.top_n
      - bertopic.embedding_model, bertopic.min_topic_size, bertopic.top_n_words
      - lda.n_topics, lda.max_features, lda.top_n_words, lda.min_df, lda.max_df, lda.ngram_range
      - gemini.api_key, gemini.model, gemini.top_n, gemini.max_words
    """
    reg: Dict[str, Callable[[], Analyzer]] = {}

    # BERTopic per-document
    def _mk_bertopic() -> Analyzer:
        bert_cfg = config.get("bertopic", {})
        return BERTopicSingleDocAnalyzer(
            embedding_model=bert_cfg.get("embedding_model", "all-MiniLM-L6-v2"),
            nr_topics=bert_cfg.get("nr_topics", "auto"),
            min_topic_size=bert_cfg.get("min_topic_size", 2),
            top_n_words=bert_cfg.get("top_n_words", 10),
            vectorizer_max_df=bert_cfg.get("vectorizer_max_df", 0.95),
            vectorizer_min_df=bert_cfg.get("vectorizer_min_df", 1),
            ngram_range=tuple(bert_cfg.get("ngram_range", (1, 2))),
        )
    reg["BERTopic (per-bookmark)"] = _mk_bertopic

    # LDA per-document (optional if sklearn present)
    if LDASingleDocAnalyzer is not None:
        def _mk_lda() -> Analyzer:
            lda_cfg = config.get("lda", {})
            return LDASingleDocAnalyzer(
                n_topics=lda_cfg.get("n_topics", 5),
                max_features=lda_cfg.get("max_features", 20000),
                top_n_words=lda_cfg.get("top_n_words", 10),
                min_df=lda_cfg.get("min_df", 1),
                max_df=lda_cfg.get("max_df", 0.95),
                ngram_range=tuple(lda_cfg.get("ngram_range", (1, 2))),
                random_state=lda_cfg.get("random_state", 42),
                max_iter=lda_cfg.get("max_iter", 15),
                learning_method=lda_cfg.get("learning_method", "batch"),
            )
        reg["LDA (per-bookmark)"] = _mk_lda

    # KeyBERT (optional)
    if KeyBERTAnalyzer is not None:
        def _mk_keybert() -> Analyzer:
            kb_cfg = config.get("keybert", {})
            return KeyBERTAnalyzer(
                model_name=kb_cfg.get("model_name", "all-MiniLM-L6-v2"),
                top_n=kb_cfg.get("top_n", 5),
            )
        reg["KeyBERT (keywords)"] = _mk_keybert

    # Gemini (optional, needs API key)
    if GeminiAnalyzer is not None:
        api_key = (config.get("gemini", {}) or {}).get("api_key")
        if api_key:
            def _mk_gemini() -> Analyzer:
                gm_cfg = config.get("gemini", {})
                return GeminiAnalyzer(
                    api_key=gm_cfg["api_key"],
                    model=gm_cfg.get("model", "gemini-1.5-pro-latest"),
                    top_n=gm_cfg.get("top_n", 5),
                    max_words=gm_cfg.get("max_words", 1500),
                )
            reg["Gemini (keywords)"] = _mk_gemini

    return reg


def list_analyzer_names(config: Dict[str, Any]) -> List[str]:
    return list(build_registry(config).keys())


def create_analyzer(name: str, config: Dict[str, Any]) -> Analyzer:
    reg = build_registry(config)
    if name not in reg:
        raise ValueError(f"Analyzer '{name}' is not available.")
    return reg[name]()