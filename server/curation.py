from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

from meckel.curation.overlay import commit_actions, index_actions, load_actions
from meckel.io.dataset import (
    find_label_dir,
    get_class_names,
    iter_image_paths,
    label_path_for_image,
    load_data_yaml,
    resolve_image_dir,
)
from meckel.io.labels import parse_yolo_label

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Meckel Curation Tool")

_state = {"units": [], "index": {}, "dirs": {}, "class_names": []}


def _dataset_root() -> Path:
    raw = os.environ.get("MECKEL_DATASET", "")
    if not raw:
        raise HTTPException(500, "MECKEL_DATASET environment variable is not set")
    return Path(raw).expanduser().resolve()


def _ensure_loaded() -> None:
    if _state["units"]:
        return
    root = _dataset_root()
    data_cfg = load_data_yaml(root)
    class_names = get_class_names(data_cfg)
    pal_id = class_names.index("periapical_lesion")

    units = []
    dirs = {}
    for split in ("train", "valid"):
        image_dir = resolve_image_dir(root, split, data_cfg)
        label_dir = find_label_dir(image_dir)
        dirs[split] = (image_dir, label_dir)
        for image_path in iter_image_paths(image_dir):
            label_path = label_path_for_image(image_path, image_dir, label_dir)
            if not label_path.exists():
                continue
            boxes = parse_yolo_label(label_path)
            if not boxes:
                continue  # negatives need no curation
            units.append(
                {
                    "key": f"{split}/{image_path.name}",
                    "split": split,
                    "file": image_path.name,
                    "has_pal": any(b.class_id == pal_id for b in boxes),
                    "boxes": [
                        {
                            "idx": i,
                            "class_name": class_names[b.class_id],
                            "box": [b.x_center, b.y_center, b.width, b.height],
                        }
                        for i, b in enumerate(boxes)
                    ],
                }
            )

    units.sort(key=lambda u: (not u["has_pal"], u["split"], u["file"]))
    _state["units"] = units
    _state["index"] = {u["key"]: i for i, u in enumerate(units)}
    _state["dirs"] = dirs
    _state["class_names"] = class_names


@app.get("/")
def root():
    return FileResponse(STATIC_DIR / "curation.html")


@app.get("/capi/meta")
def meta():
    _ensure_loaded()
    idx = index_actions(load_actions())
    reviewed = sum(1 for u in _state["units"] if idx.get(u["key"], {}).get("done"))
    return {
        "total": len(_state["units"]),
        "reviewed": reviewed,
        "class_names": _state["class_names"],
    }


@app.get("/capi/queue")
def queue(filter: str = "pal"):
    _ensure_loaded()
    idx = index_actions(load_actions())
    keys = []
    reviewed = {}
    for u in _state["units"]:
        if filter == "pal" and not u["has_pal"]:
            continue
        keys.append(u["key"])
        reviewed[u["key"]] = idx.get(u["key"], {}).get("done", False)
    return {"keys": keys, "reviewed": reviewed}


@app.get("/capi/unit")
def get_unit(key: str):
    _ensure_loaded()
    if key not in _state["index"]:
        raise HTTPException(404, "unknown image")
    u = _state["units"][_state["index"][key]]
    image_dir, _ = _state["dirs"][u["split"]]
    image_path = image_dir / u["file"]
    with Image.open(image_path) as im:
        width, height = im.size
    entry = index_actions(load_actions()).get(key, {})
    actions = {str(b): rec["action"] for b, rec in entry.get("boxes", {}).items()}
    return {
        "key": key,
        "split": u["split"],
        "file": u["file"],
        "width": width,
        "height": height,
        "boxes": u["boxes"],
        "actions": actions,
        "done": entry.get("done", False),
    }


@app.get("/capi/image/{split}/{name}")
def get_image(split: str, name: str):
    _ensure_loaded()
    if split not in _state["dirs"] or "/" in name or "\\" in name or ".." in name:
        raise HTTPException(404, "not found")
    image_dir, _ = _state["dirs"][split]
    path = (image_dir / name).resolve()
    if not path.is_file() or path.parent != image_dir.resolve():
        raise HTTPException(404, "not found")
    return FileResponse(path)


@app.post("/capi/commit")
def commit(payload: dict):
    key = payload.get("key")
    if not key:
        raise HTTPException(400, "key required")
    commit_actions(key, payload.get("actions", []))
    idx = index_actions(load_actions())
    reviewed = sum(1 for u in _state["units"] if idx.get(u["key"], {}).get("done"))
    return {"ok": True, "reviewed": reviewed, "total": len(_state["units"])}


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")