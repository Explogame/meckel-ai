from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Dict, List

OVERLAY_PATH = Path("curation/actions.jsonl")


def load_actions(path: Path = OVERLAY_PATH) -> List[dict]:
    if not path.is_file():
        return []
    out: List[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def index_actions(records: List[dict]) -> Dict[str, dict]:
    """
    image key -> {"done": bool, "boxes": {box_index: record}}
    Last record wins, so re-reviewing an image updates its state.
    """
    idx: Dict[str, dict] = {}
    for r in records:
        key = r.get("image")
        if not key:
            continue
        entry = idx.setdefault(key, {"done": False, "boxes": {}})
        action = r.get("action")
        if action == "done":
            entry["done"] = True
        elif r.get("box") is not None:
            entry["boxes"][int(r["box"])] = r
    return idx


def commit_actions(image: str, box_actions: List[dict], path: Path = OVERLAY_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    with path.open("a", encoding="utf-8") as fh:
        for ba in box_actions:
            fh.write(
                json.dumps(
                    {
                        "image": image,
                        "box": ba["box"],
                        "action": ba["action"],
                        "note": ba.get("note", ""),
                        "ts": ts,
                    }
                )
                + "\n"
            )
        fh.write(json.dumps({"image": image, "box": None, "action": "done", "ts": ts}) + "\n")
    return path