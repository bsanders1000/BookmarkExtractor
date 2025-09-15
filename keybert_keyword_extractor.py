from keybert import KeyBERT

class KeyBERTKeywordExtractor:
    def __init__(self, model_name='all-MiniLM-L6-v2', top_n=5):
        self.kw_model = KeyBERT(model_name)
        self.top_n = top_n

    def extract_keywords(self, text: str) -> list:
        if not text or not text.strip():
            return []
        # Extract keywords/phrases
        keywords = self.kw_model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 3),
            stop_words='english',
            top_n=self.top_n,
        )
        # keywords is a list of tuples: (keyword, score)
        return [kw for kw, score in keywords]