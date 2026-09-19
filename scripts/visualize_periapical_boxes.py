#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

from PIL import Image

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
from meckel.viz.draw import draw_yolo_boxes


def collect_candidates(
    image_dir: Path,
    label_dir: Path,
    target_class_id: int,
):
    candidates = []
    errors = []

    for image_path in iter_image_paths(image_dir):
        label_path = label_path_for_image(image_path, image_dir, label_dir)

        if not label_path.exists():
            continue

        try:
            boxes = parse_yolo_label(label_path)
        except Exception as exc:
            errors.append(str(exc))
            continue

        if any(box.class_id == target_class_id for box in boxes):
            candidates.append((image_path, label_path, boxes))

    candidates.sort(key=lambda item: str(item[0]))
    return candidates, errors


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Visualize sampled images containing periapical_lesion boxes "
            "for manual annotation review."
        )
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
    parser.add_argument(
        "--target-class",
        default="periapical_lesion",
    )
    parser.add_argument(
        "--num-images",
        type=int,
        default=20,
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/verification"),
    )
    parser.add_argument(
        "--draw-classes",
        default="all",
        choices=["all", "target"],
        help=(
            "Draw all boxes or only the target class. "
            "Default is all, so you can see context."
        ),
    )

    args = parser.parse_args()

    if args.num_images <= 0:
        parser.error("--num-images must be greater than 0")

    dataset_root = args.dataset.expanduser().resolve()

    data_cfg = load_data_yaml(dataset_root)
    class_names = get_class_names(data_cfg)

    if args.target_class not in class_names:
        raise SystemExit(
            f"ERROR: target class '{args.target_class}' not found in data.yaml. "
            f"Available classes: {class_names}"
        )

    target_class_id = class_names.index(args.target_class)

    image_dir = resolve_image_dir(dataset_root, args.split, data_cfg)
    label_dir = find_label_dir(image_dir)

    if not label_dir.is_dir():
        raise SystemExit(f"ERROR: label directory not found: {label_dir}")

    print("Bounding box verification")
    print(f"  dataset_root: {dataset_root}")
    print(f"  split: {args.split}")
    print(f"  image_dir: {image_dir}")
    print(f"  label_dir: {label_dir}")
    print(f"  target_class: {args.target_class}")
    print(f"  target_class_id: {target_class_id}")

    candidates, parse_errors = collect_candidates(
        image_dir=image_dir,
        label_dir=label_dir,
        target_class_id=target_class_id,
    )

    if parse_errors:
        print(f"  parse_errors: {len(parse_errors)}")
        for error in parse_errors[:5]:
            print(f"    {error}")

    if not candidates:
        raise SystemExit(
            "ERROR: no images found containing the target class. "
            "Check the split, class name, and label contents."
        )

    selected = candidates
    if len(candidates) > args.num_images:
        selected = random.Random(args.seed).sample(candidates, args.num_images)
        selected.sort(key=lambda item: str(item[0]))

    output_dir = args.output.expanduser().resolve() / f"{args.split}_{args.target_class}"
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = output_dir / "manifest.csv"

    print(f"  candidates_found: {len(candidates)}")
    print(f"  images_selected: {len(selected)}")
    print(f"  output_dir: {output_dir}")

    written = 0

    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "index",
                "image_path",
                "label_path",
                "output_image",
                "all_boxes",
                "target_boxes",
                "class_summary",
            ]
        )

        for image_path, label_path, boxes in selected:
            try:
                image = Image.open(image_path).convert("RGB")
            except Exception as exc:
                print(f"WARNING: could not open image {image_path}: {exc}")
                continue

            if args.draw_classes == "all":
                boxes_to_draw = boxes
            else:
                boxes_to_draw = [
                    box for box in boxes if box.class_id == target_class_id
                ]

            annotated = draw_yolo_boxes(
                image=image,
                boxes=boxes_to_draw,
                class_names=class_names,
                target_class_id=target_class_id,
            )

            written += 1
            output_image = output_dir / f"{written:02d}_{image_path.stem}.png"
            annotated.save(output_image)

            counts = count_boxes_by_class(boxes)
            target_box_count = sum(
                1 for box in boxes if box.class_id == target_class_id
            )

            class_summary_parts = []
            for class_id in sorted(counts.keys()):
                if 0 <= class_id < len(class_names):
                    name = class_names[class_id]
                else:
                    name = f"class_{class_id}"
                class_summary_parts.append(f"{name}={counts[class_id]}")

            class_summary = ";".join(class_summary_parts)

            writer.writerow(
                [
                    written,
                    image_path,
                    label_path,
                    output_image,
                    len(boxes),
                    target_box_count,
                    class_summary,
                ]
            )

    if written == 0:
        raise SystemExit("ERROR: no annotated images were written.")

    print(f"Saved {written} annotated images to: {output_dir}")
    print(f"Manifest written to: {manifest_path}")
    print("Review question: are the green boxes tight around true periapical lesions?")


if __name__ == "__main__":
    main()