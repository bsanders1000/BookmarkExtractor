import json
import time
from pathlib import Path

class GeminiUsageManager:
    def __init__(self, usage_path=None):
        self.usage_path = usage_path or Path.home() / ".bookmark_aggregator" / "gemini_usage.json"
        self.reset_if_needed()
        self.load()

    def reset_if_needed(self):
        # Reset daily and minute counters at proper intervals
        now = time.time()
        usage = self.load_raw()
        day_start = usage.get("day_start", 0)
        minute_start = usage.get("minute_start", 0)
        if now - day_start >= 86400:
            self.save_raw({"day_start": now, "minute_start": now,
                          "tokens_today": 0, "tokens_this_minute": 0,
                          "requests_today": 0, "requests_this_minute": 0})
        elif now - minute_start >= 60:
            usage["minute_start"] = now
            usage["tokens_this_minute"] = 0
            usage["requests_this_minute"] = 0
            self.save_raw(usage)

    def load_raw(self):
        if self.usage_path.exists():
            try:
                with open(self.usage_path, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_raw(self, usage):
        self.usage_path.parent.mkdir(exist_ok=True, parents=True)
        with open(self.usage_path, "w") as f:
            json.dump(usage, f, indent=2)

    def load(self):
        usage = self.load_raw()
        self.day_start = usage.get("day_start", time.time())
        self.minute_start = usage.get("minute_start", time.time())
        self.tokens_today = usage.get("tokens_today", 0)
        self.tokens_this_minute = usage.get("tokens_this_minute", 0)
        self.requests_today = usage.get("requests_today", 0)
        self.requests_this_minute = usage.get("requests_this_minute", 0)

    def update(self, tokens_used, request_count=1):
        self.reset_if_needed()
        self.load()
        self.tokens_today += tokens_used
        self.tokens_this_minute += tokens_used
        self.requests_today += request_count
        self.requests_this_minute += request_count
        # Save back
        self.save_raw({
            "day_start": self.day_start,
            "minute_start": self.minute_start,
            "tokens_today": self.tokens_today,
            "tokens_this_minute": self.tokens_this_minute,
            "requests_today": self.requests_today,
            "requests_this_minute": self.requests_this_minute
        })

    def can_request(self, tokens_needed):
        self.reset_if_needed()
        self.load()
        if self.requests_today >= 50 or self.tokens_today + tokens_needed > 1_048_576:
            return False, "Daily Gemini API quota exceeded"
        if self.requests_this_minute >= 2 or self.tokens_this_minute + tokens_needed > 125_000:
            return False, "Per-minute Gemini API quota exceeded"
        return True, ""
