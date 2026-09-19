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


def _polygon_to_box(class_id: int, coords: List[float]) -> YoloBox:
    """
    Convert YOLO-seg polygon coordinates (x1 y1 x2 y2 ... xn yn)
    into an axis-aligned bounding box.
    """
    xs = coords[0::2]
    ys = coords[1::2]

    x_min = min(xs)
    x_max = max(xs)
    y_min = min(ys)
    y_max = max(ys)

    return YoloBox(
        class_id=class_id,
        x_center=(x_min + x_max) / 2.0,
        y_center=(y_min + y_max) / 2.0,
        width=x_max - x_min,
        height=y_max - y_min,
    )


def parse_yolo_label(path: Path) -> List[YoloBox]:
    """
    Parse one YOLO-format label file.

    This dataset mixes two line formats:
      1. Detection box:   class_id x_center y_center width height
      2. Polygon (seg):   class_id x1 y1 x2 y2 ... xn yn

    Polygon lines are converted to axis-aligned bounding boxes
    using the min/max of the polygon coordinates.
    """
    if not path.exists():
        return []

    boxes: List[YoloBox] = []

    for line_number, raw_line in enumerate(path.read_text().splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        tokens = line.split()

        try:
            class_id = int(tokens[0])
            coords = [float(value) for value in tokens[1:]]
        except ValueError as exc:
            raise ValueError(
                f"{path}:{line_number} could not parse YOLO values"
            ) from exc

        if len(coords) == 4:
            box = YoloBox(
                class_id=class_id,
                x_center=coords[0],
                y_center=coords[1],
                width=coords[2],
                height=coords[3],
            )
        elif len(coords) >= 6 and len(coords) % 2 == 0:
            box = _polygon_to_box(class_id, coords)
        else:
            raise ValueError(
                f"{path}:{line_number} unsupported YOLO line format "
                f"({len(coords)} coordinate values)"
            )

        if not box.is_valid():
            raise ValueError(f"{path}:{line_number} invalid YOLO box: {box}")

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