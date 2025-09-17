import json
from bookmark_extractor import Bookmark, extract_bookmarks
from analyzers.registry import get_default_analyzer
from bookmark_categorizer import categorize_bookmarks
from collections import defaultdict, Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

OUTPUT_FILE = "topic_candidates.json"
SAMPLE_URLS_PER_TOPIC = 5
N_CLUSTERS = 12  # Coarse topics


def extract_keywords(bookmarks):
    analyzer = get_default_analyzer()
    results = []
    for bm in bookmarks:
        try:
            analysis = analyzer.analyze(bm)
            keywords = analysis.get("keywords", [])
            entities = analysis.get("entities", [])
            results.append({
                "bookmark": bm,
                "keywords": keywords,
                "entities": entities,
            })
        except Exception as e:
            results.append({"bookmark": bm, "keywords": [], "entities": []})
    return results


def cluster_bookmarks(keyword_results, n_clusters=N_CLUSTERS):
    # Flatten keywords/entities for each bookmark
    texts = [" ".join(res["keywords"] + res["entities"]) for res in keyword_results]
    if not any(texts):
        return []
    vectorizer = TfidfVectorizer(max_features=1000)
    X = vectorizer.fit_transform(texts)
    kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
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
    print("Extracting bookmarks...")
    bookmarks = extract_bookmarks()
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
