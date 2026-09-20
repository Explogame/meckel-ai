from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple
import cv2
import numpy as np
from PIL import Image

@dataclass
class QualityReport:
    ok: bool
    checks: List[Tuple[str, bool, str]]

def check_quality(image: Image.Image) -> QualityReport:
    gray = cv2.cvtColor(np.asarray(image.convert("RGB")), cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    brightness, contrast = float(gray.mean()), float(gray.std())
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    checks = [
        ("Resolution adequate", min(w, h) >= 256, f"{w} x {h} px"),
        ("Brightness in range", 40.0 <= brightness <= 220.0, f"mean {brightness:.0f}"),
        ("Contrast adequate", contrast >= 20.0, f"std {contrast:.0f}"),
        ("Sharpness adequate", sharpness >= 25.0, f"var {sharpness:.0f}"),
    ]
    # Hard blockers are only resolution and contrast
    return QualityReport(ok=(checks[0][1] and checks[2][1]), checks=checks)