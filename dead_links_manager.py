import json
from pathlib import Path

class DeadLinksManager:
    def __init__(self, dead_links_path=None):
        self.dead_links_path = dead_links_path or Path.home() / ".bookmark_aggregator" / "dead_links.json"
        self.dead_links = set()
        self.load()

    def load(self):
        if self.dead_links_path.exists():
            try:
                with open(self.dead_links_path, "r", encoding="utf-8") as f:
                    self.dead_links = set(json.load(f))
            except Exception:
                self.dead_links = set()
        else:
            self.dead_links = set()

    def save(self):
        self.dead_links_path.parent.mkdir(exist_ok=True, parents=True)
        with open(self.dead_links_path, "w", encoding="utf-8") as f:
            json.dump(list(self.dead_links), f, indent=2)

    def add(self, url):
        self.dead_links.add(url)
        self.save()

    def is_dead(self, url):
        return url in self.dead_links