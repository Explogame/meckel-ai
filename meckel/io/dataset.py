from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterator, List, Optional

import yaml

from .labels import YoloBox, parse_yolo_label

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
VALID_SPLITS = {"train", "valid", "test"}


def load_data_yaml(dataset_root: Path) -> Dict:
    data_yaml = dataset_root / "data.yaml"

    if not data_yaml.is_file():
        raise FileNotFoundError(f"data.yaml not found at: {data_yaml}")

    return yaml.safe_load(data_yaml.read_text()) or {}


def get_class_names(data_cfg: Dict) -> List[str]:
    names = data_cfg.get("names")

    if isinstance(names, dict):
        return [str(names[idx]) for idx in sorted(names.keys())]

    if isinstance(names, list):
        return [str(name) for name in names]

    raise ValueError("data.yaml must contain class names as a list or dict")


def _candidate_image_dirs(
    dataset_root: Path,
    split: str,
    raw_path: Optional[str],
) -> List[Path]:
    candidates: List[Path] = []

    if raw_path:
        raw = Path(str(raw_path))
        if raw.is_absolute():
            candidates.append(raw)
        else:
            candidates.append((dataset_root / raw).resolve())
            candidates.append((dataset_root.parent / raw).resolve())

    split_names = [split]
    if split == "valid":
        split_names.append("val")

    for name in split_names:
        candidates.extend(
            [
                (dataset_root / name / "images").resolve(),
                (dataset_root / "data" / name / "images").resolve(),
                (dataset_root.parent / name / "images").resolve(),
            ]
        )

    unique: List[Path] = []
    seen = set()

    for candidate in candidates:
        key = str(candidate)
        if key not in seen:
            seen.add(key)
            unique.append(candidate)

    return unique


def resolve_image_dir(dataset_root: Path, split: str, data_cfg: Dict) -> Path:
    if split not in VALID_SPLITS:
        raise ValueError(f"split must be one of: {sorted(VALID_SPLITS)}")

    raw = data_cfg.get(split)
    if split == "valid" and raw is None:
        raw = data_cfg.get("val")

    for candidate in _candidate_image_dirs(dataset_root, split, raw):
        if candidate.is_dir():
            return candidate

    raise FileNotFoundError(
        f"Could not resolve image directory for split '{split}' "
        f"from dataset root: {dataset_root}"
    )


def find_label_dir(image_dir: Path) -> Path:
    """
    Find the corresponding labels directory for an images directory.
    Usually:
        train/images -> train/labels
    """
    if image_dir.name == "images":
        candidate = image_dir.parent / "labels"
        if candidate.is_dir():
            return candidate

    parts = list(image_dir.parts)
    for idx in range(len(parts) - 1, -1, -1):
        if parts[idx] == "images":
            new_parts = parts.copy()
            new_parts[idx] = "labels"

            if len(new_parts) == 1:
                candidate = Path(new_parts[0])
            else:
                candidate = Path(new_parts[0]).joinpath(*new_parts[1:])

            if candidate.is_dir():
                return candidate

    return image_dir.parent / "labels"


def iter_image_paths(image_dir: Path) -> Iterator[Path]:
    paths = [
        path
        for path in image_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]

    for path in sorted(paths, key=lambda p: str(p)):
        yield path


def label_path_for_image(
    image_path: Path,
    image_dir: Path,
    label_dir: Path,
) -> Path:
    relative = image_path.relative_to(image_dir)
    return (label_dir / relative).with_suffix(".txt")


def load_boxes_for_image(
    image_path: Path,
    image_dir: Path,
    label_dir: Path,
) -> tuple[Path, List[YoloBox], bool]:
    """
    Returns:
        label_path, boxes, label_exists
    """
    label_path = label_path_for_image(image_path, image_dir, label_dir)

    if not label_path.exists():
        return label_path, [], False

    return label_path, parse_yolo_label(label_path), True


def contains_class(boxes: List[YoloBox], class_id: int) -> bool:
    return any(box.class_id == class_id for box in boxes)