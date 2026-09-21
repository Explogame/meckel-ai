#!/usr/bin/env python
from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path

from meckel.io.dataset import (
    find_label_dir,
    get_class_names,
    iter_image_paths,
    label_path_for_image,
    load_data_yaml,
    resolve_image_dir,
)
from meckel.io.labels import parse_yolo_label


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Copy sample images containing periapical_lesion into samples/ for demo testing."
    )
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--split", default="valid")
    parser.add_argument("--target-class", default="periapical_lesion")
    parser.add_argument("--num-images", type=int, default=6)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--output", type=Path, default=Path("samples"))
    args = parser.parse_args()

    dataset_root = args.dataset.expanduser().resolve()
    data_cfg = load_data_yaml(dataset_root)
    class_names = get_class_names(data_cfg)
    target_id = class_names.index(args.target_class)

    image_dir = resolve_image_dir(dataset_root, args.split, data_cfg)
    label_dir = find_label_dir(image_dir)

    candidates = []
    for image_path in iter_image_paths(image_dir):
        label_path = label_path_for_image(image_path, image_dir, label_dir)
        if not label_path.exists():
            continue
        boxes = parse_yolo_label(label_path)
        if any(b.class_id == target_id for b in boxes):
            candidates.append(image_path)

    if not candidates:
        raise SystemExit("No candidate images found.")

    selected = random.Random(args.seed).sample(candidates, min(args.num_images, len(candidates)))

    args.output.mkdir(parents=True, exist_ok=True)
    for image_path in selected:
        shutil.copy2(image_path, args.output / image_path.name)
        print(f"copied: {args.output / image_path.name}")

    print(f"Done. {len(selected)} sample images in {args.output}/")


if __name__ == "__main__":
    main()