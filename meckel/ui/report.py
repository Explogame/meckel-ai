from __future__ import annotations

import datetime
from typing import Dict, List

from .inference import Detection


def build_report(
    image_name: str,
    detections: List[Detection],
    statuses: Dict[int, str],
    meta: Dict[int, Dict],
    conf_threshold: float,
) -> str:
    lines = [
        "# Meckel AI — Analysis Report",
        "",
        f"- Image: {image_name}",
        f"- Generated: {datetime.datetime.now().isoformat(timespec='seconds')}",
        f"- Confidence threshold: {conf_threshold:.2f}",
        "",
        "## Findings",
        "",
    ]

    if not detections:
        lines.append("_No periapical lesions detected above threshold._")
        lines.append("")

    for det in detections:
        m = meta.get(det.detection_id, {})
        lines.append(f"### Finding #{det.detection_id}")
        lines.append(f"- Model label: {det.class_name}")
        lines.append(f"- Review label: {m.get('label', det.class_name)}")
        lines.append(f"- Model confidence: {det.confidence:.0%}")
        lines.append(f"- Clinician confidence: {m.get('confidence', round(det.confidence * 100))}%")
        lines.append(f"- Box (x1, y1, x2, y2): [{det.x1}, {det.y1}, {det.x2}, {det.y2}]")
        lines.append(f"- Review status: {statuses.get(det.detection_id, 'pending')}")
        notes = m.get("notes", "")
        if notes:
            lines.append(f"- Clinician notes: {notes}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("_AI assistance only — not a diagnosis. All findings require clinician confirmation._")
    lines.append("")
    lines.append("_Model trained on dental-xray-dataset by shreku (Roboflow Universe), CC BY 4.0._")

    return "\n".join(lines)