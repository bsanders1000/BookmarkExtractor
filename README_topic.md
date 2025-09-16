# Batch Topic Modeling Integration (BERTopic + Future LDA)

## Overview
This module batch-processes bookmarks, fetches their page text, fits a BERTopic model, and assigns multiple topics (with probabilities and keywords) to each bookmark. It also saves global topic metadata for exploration, visualization, or downstream clustering.

## Key Modules
- `fetcher.py` — Fetch and extract text from URLs.
- `bertopic_batch_extractor.py` — Wrapper around BERTopic for batch usage.
- `topic_batch_processor.py` — Orchestrates fetching, modeling, assignment, saving.
- `storage_utils.py` — Simple JSON (de)serialization helpers.
- `lda_extractor_placeholder.py` — Guidance for future LDA implementation.

## Per-Bookmark Structure
After running, each bookmark gets:
```json
"topics": [
  {
    "topic_id": 12,
    "probability": 0.34,
    "keywords": [
      {"word": "climate", "score": 0.024},
      {"word": "policy", "score": 0.019},
      ...
    ]
  },
  ...
],
"keywords": ["climate", "policy", ...]  // Derived from the top topic for convenience
```

## Global Topics
Saved to: `bookmarks_with_topics_global_topics.json`
Each entry:
```json
{
  "topic_id": 12,
  "keywords": [{"word": "climate", "score": 0.024}, ...],
  "representation": ["climate", "policy", ...]
}
```

## Multiple Topics per Bookmark
We use document-level probability distributions (enabled by `calculate_probabilities=True`) and:
- Filter by `min_topic_probability`
- Take top `top_n_per_doc` topics

## Outlier Topic (-1)
BERTopic may label some documents with topic `-1` (outliers). We exclude it from multi-topic assignment, but you can modify that behavior.

## Performance Tips
- Cache fetched content (`content_cache_path`) to avoid repeated HTTP requests.
- Adjust `max_words` to control memory/time.
- Use a stronger embedding model (e.g., `all-mpnet-base-v2`) for better semantic grouping (slower).
- Set `nr_topics='auto'` or an int to reduce/infer topics.

## Future LDA Comparison
1. Build a unified corpus (same docs).
2. Fit LDA (see `lda_extractor_placeholder.py`).
3. Store LDA per-document topic distributions alongside BERTopic.
4. Compare overlap: Jaccard similarity between top keywords, KL divergence between distributions, etc.

## Potential Enhancements
- Add language detection and per-language modeling.
- Add HTML cleaning heuristics (remove nav/footer).
- Add progress bars (e.g., `tqdm`) in fetching and modeling.
- Build a visualization dashboard (BERTopic has built-in `.visualize_topics()` etc.).

## Troubleshooting
- If probabilities are `None`, ensure `calculate_probabilities=True`.
- If you see memory issues, reduce `max_words` or use a smaller embedding model.
- If many topics are incoherent, consider:
  - Increasing corpus size
  - Using a better embedding model
  - Reducing topics with `nr_topics`
  - Adjusting `min_topic_probability`

## License
Integrate as needed within your application.