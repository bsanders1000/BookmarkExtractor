import json
from pathlib import Path
from urllib.parse import urlparse
from collections import defaultdict, Counter

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

from bookmark_storage import BookmarkStorage
from browser_detector import detect_browsers
from bookmark_extractor import extract_bookmarks

OUTPUT_FILE = "topic_candidates.json"
SAMPLE_URLS_PER_TOPIC = 5
N_CLUSTERS = 12  # Coarse topics


def _text_for_bookmark(bm):
    parts = []
    if bm.title:
        parts.append(bm.title)
    if bm.folder_path:
        parts.append(bm.folder_path.replace('/', ' '))
    try:
        netloc = urlparse(bm.url).netloc
        parts.append(netloc.replace('.', ' '))
    except Exception:
        pass
    return ' '.join(parts)

def extract_keywords(bookmarks):
    """Lightweight keyword/entity extraction using TF-IDF tokens.
    Returns list of dicts with bookmark, keywords, and entities (empty).
    """
    texts = [_text_for_bookmark(bm) for bm in bookmarks]
    if not any(texts):
        return [{"bookmark": bm, "keywords": [], "entities": []} for bm in bookmarks]
    vectorizer = TfidfVectorizer(max_features=2000, ngram_range=(1, 2), stop_words='english')
    X = vectorizer.fit_transform(texts)
    feature_names = vectorizer.get_feature_names_out()
    results = []
    for i, bm in enumerate(bookmarks):
        row = X.getrow(i)
        if row.nnz == 0:
            results.append({"bookmark": bm, "keywords": [], "entities": []})
            continue
        # Top 10 tokens for this bookmark
        top_idx = row.toarray().ravel().argsort()[-10:][::-1]
        kws = [feature_names[j] for j in top_idx if row[0, j] > 0]
        results.append({"bookmark": bm, "keywords": kws, "entities": []})
    return results


def cluster_bookmarks(keyword_results, n_clusters=N_CLUSTERS):
    # Flatten keywords/entities for each bookmark
    texts = [" ".join(res["keywords"] + res["entities"]) for res in keyword_results]
    if not any(texts):
        return []
    vectorizer = TfidfVectorizer(max_features=1000)
    X = vectorizer.fit_transform(texts)
    kmeans = KMeans(n_clusters=min(n_clusters, max(1, len(keyword_results))), n_init=10, random_state=42)
    labels = kmeans.fit_predict(X)
    return labels, vectorizer, kmeans


def build_topic_candidates(keyword_results, labels):
    topics = defaultdict(list)
    for res, label in zip(keyword_results, labels):
        topics[label].append(res)
    topic_candidates = []
    for label, items in topics.items():
        all_keywords = [kw for res in items for kw in res["keywords"]]
        all_entities = [en for res in items for en in res["entities"]]
        keyword_counts = Counter(all_keywords)
        entity_counts = Counter(all_entities)
        sample_urls = [res["bookmark"].url for res in items[:SAMPLE_URLS_PER_TOPIC]]
        topic_candidates.append({
            "topic_id": int(label),
            "keywords": keyword_counts.most_common(10),
            "entities": entity_counts.most_common(10),
            "sample_urls": sample_urls,
            "evidence_count": len(items),
        })
    return topic_candidates


def main():
    # Prefer existing stored bookmarks
    storage_path = Path.home() / ".bookmark_aggregator" / "bookmarks_processed.json"
    storage = BookmarkStorage(storage_path)
    storage.load()
    bookmarks = storage.get_all()

    if not bookmarks:
        print("No stored bookmarks found. Extracting from browsers...")
        bookmarks = []
        for browser in detect_browsers():
            try:
                bookmarks.extend(extract_bookmarks(browser))
            except Exception:
                continue
    print(f"Found {len(bookmarks)} bookmarks.")
    print("Extracting keywords and entities...")
    keyword_results = extract_keywords(bookmarks)
    print("Clustering bookmarks...")
    labels, _, _ = cluster_bookmarks(keyword_results)
    print("Building topic candidates...")
    topic_candidates = build_topic_candidates(keyword_results, labels)
    print(f"Writing {len(topic_candidates)} topic candidates to {OUTPUT_FILE}")
    with open(OUTPUT_FILE, "w") as f:
        json.dump(topic_candidates, f, indent=2)
    print("Done.")


if __name__ == "__main__":
    main()
