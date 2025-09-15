import json
from pathlib import Path

class SettingsManager:
    def __init__(self, settings_path=None):
        self.settings_path = settings_path or Path.home() / ".bookmark_aggregator" / "settings.json"
        self.settings = {}
        self.load()

    def load(self):
        try:
            if self.settings_path.exists():
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    self.settings = json.load(f)
            else:
                self.settings = {}
        except Exception:
            self.settings = {}

    def save(self):
        self.settings_path.parent.mkdir(exist_ok=True, parents=True)
        with open(self.settings_path, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=2)

    def get_api_key(self):
        return self.settings.get("api_key", "")

    def set_api_key(self, api_key):
        self.settings["api_key"] = api_key
        self.save()