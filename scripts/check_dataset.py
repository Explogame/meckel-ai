#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path

from meckel.io.dataset import (
    VALID_SPLITS,
    find_label_dir,
    get_class_names,
    iter_image_paths,
    label_path_for_image,
    load_data_yaml,
    resolve_image_dir,
)
from meckel.io.labels import count_boxes_by_class, parse_yolo_label


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check dataset paths, labels, and class counts."
    )
    parser.add_argument(
        "--dataset",
        required=True,
        type=Path,
        help="Folder containing data.yaml",
    )
    parser.add_argument(
        "--split",
        default="train",
        choices=sorted(VALID_SPLITS),
    )
    args = parser.parse_args()

    dataset_root = args.dataset.expanduser().resolve()

    try:
        data_cfg = load_data_yaml(dataset_root)
        class_names = get_class_names(data_cfg)
        image_dir = resolve_image_dir(dataset_root, args.split, data_cfg)
    except Exception as exc:
        raise SystemExit(f"ERROR: {exc}")

    label_dir = find_label_dir(image_dir)

    print("Dataset check")
    print(f"  dataset_root: {dataset_root}")
    print(f"  split: {args.split}")
    print(f"  image_dir: {image_dir}")
    print(f"  label_dir: {label_dir}")
    print(f"  classes: {class_names}")

    if not label_dir.is_dir():
        raise SystemExit("ERROR: label directory was not found.")

    image_paths = list(iter_image_paths(image_dir))
    print(f"  images_found: {len(image_paths)}")

    missing_labels = 0
    empty_labels = 0
    total_boxes = 0
    class_counts: dict[int, int] = {}
    parse_errors: list[str] = []

    for image_path in image_paths:
        label_path = label_path_for_image(image_path, image_dir, label_dir)

        if not label_path.exists():
            missing_labels += 1
            continue

        try:
            boxes = parse_yolo_label(label_path)
        except Exception as exc:
            parse_errors.append(str(exc))
            continue

        if not boxes:
            empty_labels += 1

        total_boxes += len(boxes)

        for class_id, count in count_boxes_by_class(boxes).items():
            class_counts[class_id] = class_counts.get(class_id, 0) + count

    print(f"  labels_missing: {missing_labels}")
    print(f"  labels_empty: {empty_labels}")
    print(f"  boxes_total: {total_boxes}")
    print("  boxes_by_class:")

    for class_id, name in enumerate(class_names):
        print(f"    {class_id} {name}: {class_counts.get(class_id, 0)}")

    if parse_errors:
        print(f"  parse_errors: {len(parse_errors)}")
        for error in parse_errors[:5]:
            print(f"    {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()