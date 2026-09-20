from __future__ import annotations
from typing import Dict, List
from PIL import Image, ImageDraw, ImageFont
from .inference import Detection

STATUS_COLORS = {
    "pending": "#FF3B30", "confirmed": "#34C759",
    "dismissed": "#8E8E93", "adjusted": "#FF9500",
}

def draw_detections(image: Image.Image, detections: List[Detection], statuses: Dict[int, str]) -> Image.Image:
    annotated = image.copy()
    draw = ImageDraw.Draw(annotated)
    try: font = ImageFont.load_default(size=max(12, min(image.width, image.height) // 55))
    except TypeError: font = ImageFont.load_default()
    
    line_width = max(2, min(image.width, image.height) // 350)

    for det in detections:
        status = statuses.get(det.detection_id, "pending")
        color = STATUS_COLORS.get(status, STATUS_COLORS["pending"])
        draw.rectangle([det.x1, det.y1, det.x2, det.y2], outline=color, width=line_width)
        
        label = f"#{det.detection_id} {det.confidence:.0%}"
        try:
            bbox = draw.textbbox((det.x1, det.y1), label, font=font)
            text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            text_y = max(0, det.y1 - text_h - 2)
            draw.rectangle([det.x1, text_y, det.x1 + text_w + 2, text_y + text_h + 2], fill=color)
            draw.text((det.x1 + 1, text_y + 1), label, fill="white", font=font)
        except Exception:
            draw.text((det.x1 + 1, max(0, det.y1 - 12)), label, fill=color, font=font)

    return annotated