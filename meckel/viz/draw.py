from __future__ import annotations

from typing import Sequence

from PIL import Image, ImageDraw, ImageFont

from meckel.io.labels import YoloBox, yolo_box_to_xyxy

CLASS_COLORS = {
    "periapical_lesion": "#00FF00",
    "caries": "#FF9500",
}

FALLBACK_COLORS = [
    "#00C7FF",
    "#FF3B30",
    "#FFD60A",
    "#BF5AF2",
    "#30D158",
]


def _font_for_image(image: Image.Image):
    min_side = min(image.width, image.height)
    font_size = max(12, min_side // 55)

    try:
        return ImageFont.load_default(size=font_size)
    except TypeError:
        return ImageFont.load_default()


def _line_width_for_image(image: Image.Image) -> int:
    return max(2, min(image.width, image.height) // 350)


def draw_yolo_boxes(
    image: Image.Image,
    boxes: Sequence[YoloBox],
    class_names: Sequence[str],
    target_class_id: int | None = None,
) -> Image.Image:
    """
    Draw YOLO boxes onto a copy of the image.
    """
    annotated = image.copy()
    draw = ImageDraw.Draw(annotated)
    font = _font_for_image(annotated)
    line_width = _line_width_for_image(annotated)

    for box in boxes:
        x1, y1, x2, y2 = yolo_box_to_xyxy(
            box,
            annotated.width,
            annotated.height,
        )

        if 0 <= box.class_id < len(class_names):
            class_name = class_names[box.class_id]
        else:
            class_name = f"class_{box.class_id}"

        color = CLASS_COLORS.get(
            class_name,
            FALLBACK_COLORS[box.class_id % len(FALLBACK_COLORS)],
        )

        if target_class_id is not None and box.class_id == target_class_id:
            color = CLASS_COLORS.get("periapical_lesion", color)

        draw.rectangle([x1, y1, x2, y2], outline=color, width=line_width)

        label = class_name

        try:
            text_bbox = draw.textbbox((x1, y1), label, font=font)
            text_w = text_bbox[2] - text_bbox[0]
            text_h = text_bbox[3] - text_bbox[1]
            text_y = max(0, y1 - text_h - 2)

            draw.rectangle(
                [x1, text_y, x1 + text_w + 2, text_y + text_h + 2],
                fill=color,
            )
            draw.text((x1 + 1, text_y + 1), label, fill="black", font=font)
        except Exception:
            draw.text((x1 + 1, max(0, y1 - 12)), label, fill=color, font=font)

    return annotated