from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class YoloBox:
    class_id: int
    x_center: float
    y_center: float
    width: float
    height: float

    def is_valid(self) -> bool:
        return (
            self.class_id >= 0
            and self.width > 0.0
            and self.height > 0.0
            and self.x_center >= -0.001
            and self.x_center <= 1.001
            and self.y_center >= -0.001
            and self.y_center <= 1.001
        )


def parse_yolo_label(path: Path) -> List[YoloBox]:
    """
    Parse one YOLO-format label file.

    Expected values per box:
        class_id x_center y_center width height

    Some files in this dataset wrap multiple boxes onto a single line
    (tokens re-flowed at arbitrary line breaks), so we parse the whole
    file as a flat token stream and chunk it in groups of 5.
    """
    if not path.exists():
        return []

    tokens = path.read_text().split()

    if not tokens:
        return []

    if len(tokens) % 5 != 0:
        raise ValueError(
            f"{path}: token count {len(tokens)} is not a multiple of 5"
        )

    boxes: List[YoloBox] = []

    for start in range(0, len(tokens), 5):
        chunk = tokens[start:start + 5]

        try:
            class_id = int(chunk[0])
            x_center, y_center, width, height = (float(value) for value in chunk[1:])
        except ValueError as exc:
            raise ValueError(
                f"{path}: invalid YOLO box values in tokens {start + 1}-{start + 5}"
            ) from exc

        box = YoloBox(
            class_id=class_id,
            x_center=x_center,
            y_center=y_center,
            width=width,
            height=height,
        )

        if not box.is_valid():
            raise ValueError(
                f"{path}: invalid YOLO box in tokens {start + 1}-{start + 5}: {box}"
            )

        boxes.append(box)

    return boxes


def yolo_box_to_xyxy(
    box: YoloBox,
    image_width: int,
    image_height: int,
) -> tuple[int, int, int, int]:
    """
    Convert YOLO normalized box format to pixel coordinates:
        (x1, y1, x2, y2)
    """
    if image_width <= 0 or image_height <= 0:
        raise ValueError("Image width and height must be positive")

    x_center = min(max(box.x_center, 0.0), 1.0)
    y_center = min(max(box.y_center, 0.0), 1.0)
    width = min(max(box.width, 0.0), 1.0)
    height = min(max(box.height, 0.0), 1.0)

    half_w = width / 2.0
    half_h = height / 2.0

    x1 = (x_center - half_w) * image_width
    y1 = (y_center - half_h) * image_height
    x2 = (x_center + half_w) * image_width
    y2 = (y_center + half_h) * image_height

    x1 = min(max(int(round(x1)), 0), image_width - 1)
    y1 = min(max(int(round(y1)), 0), image_height - 1)
    x2 = min(max(int(round(x2)), 0), image_width - 1)
    y2 = min(max(int(round(y2)), 0), image_height - 1)

    if x2 <= x1:
        x2 = min(x1 + 1, image_width - 1)
    if y2 <= y1:
        y2 = min(y1 + 1, image_height - 1)

    return x1, y1, x2, y2


def count_boxes_by_class(boxes: Iterable[YoloBox]) -> Dict[int, int]:
    counts: Dict[int, int] = {}
    for box in boxes:
        counts[box.class_id] = counts.get(box.class_id, 0) + 1
    return counts