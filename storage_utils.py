import json
import logging
from pathlib import Path
from typing import Any, List


def save_bookmarks(bookmarks: List[Any], path: str):
    """
    Serializes bookmark objects into JSON. Adjust this depending on how your
    bookmark objects are structured. If they are dataclasses, you may need asdict().
    Assumes each bookmark has at least: url, keywords (list), topics (list), is_valid.
    """
    serializable = []
    for b in bookmarks:
        # Adjust attribute access if your bookmark structure differs.
        serializable.append({
            "url": getattr(b, "url", None),
            "keywords": getattr(b, "keywords", []),
            "topics": getattr(b, "topics", []),
            "is_valid": getattr(b, "is_valid", True)
        })
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    with open(path_obj, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2)
    logging.info("Saved %d bookmarks to %s", len(bookmarks), path)


def load_bookmarks(path: str, bookmark_factory=None) -> list:
    """
    Loads bookmarks back. If you want them as objects, provide a bookmark_factory(dict)->object.
    """
    path_obj = Path(path)
    if not path_obj.exists():
        logging.warning("Bookmark file %s not found. Returning empty list.", path)
        return []
    with open(path_obj, "r", encoding="utf-8") as f:
        data = json.load(f)
    if bookmark_factory:
        return [bookmark_factory(d) for d in data]
    return data