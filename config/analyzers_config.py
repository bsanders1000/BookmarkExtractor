from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any

CONFIG_PATH = Path.home() / ".bookmark_aggregator" / "analyzers_config.json"


def default_config() -> Dict[str, Any]:
    return {
        "bertopic": {
            "embedding_model": "all-MiniLM-L6-v2",
            "nr_topics": "auto",           # "auto" or integer
            "min_topic_size": 2,
            "top_n_words": 10,
            "vectorizer_max_df": 0.95,
            "vectorizer_min_df": 1,
            "ngram_range": (1, 2),
        },
        "lda": {
            "n_topics": 5,
            "max_features": 20000,
            "top_n_words": 10,
            "min_df": 1,
            "max_df": 0.95,
            "ngram_range": (1, 2),
            "random_state": 42,
            "max_iter": 15,
            "learning_method": "batch",
        },
        "keybert": {
            "model_name": "all-MiniLM-L6-v2",
            "top_n": 5,
        },
        "gemini": {
            "api_key": "",
            "model": "gemini-1.5-pro-latest",
            "top_n": 5,
            "max_words": 1500,
        },
    }


def load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            # Ensure defaults for any missing keys
            cfg = default_config()
            for k, v in cfg.items():
                if k not in data or not isinstance(data[k], dict):
                    data[k] = v
                else:
                    # merge nested dicts
                    for nk, nv in v.items():
                        data[k].setdefault(nk, nv)
            return data
        except Exception:
            pass
    return default_config()


def save_config(cfg: Dict[str, Any]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")