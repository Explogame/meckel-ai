from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any, Dict, List

LOG_PATH = Path("outputs/reviews/review_log.jsonl")


def save_review(image_name: str, payload: Dict[str, Any]) -> Path:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "image_name": image_name,
        **payload,
    }
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
    return LOG_PATH


def load_reviews() -> List[Dict[str, Any]]:
    if not LOG_PATH.is_file():
        return []
    reviews: List[Dict[str, Any]] = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            reviews.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return reviews