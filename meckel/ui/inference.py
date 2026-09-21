from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

import numpy as np
from PIL import Image
from ultralytics import YOLO

TARGET_CLASS = "periapical_lesion"


@dataclass
class Detection:
    detection_id: int
    class_name: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int


def load_model(weights_path: str | Path) -> YOLO:
    path = Path(weights_path)
    if not path.is_file():
        raise FileNotFoundError(
            f"Model weights not found at: {path}. "
            "Copy best.pt from your training run into weights/ first."
        )
    return YOLO(str(path))


def run_detection(
    model: YOLO,
    image: Image.Image,
    conf: float,
) -> List[Detection]:
    device = os.environ.get("MECKEL_DEVICE", "cpu")

    results = model.predict(
        source=np.asarray(image.convert("RGB")),
        conf=conf,
        device=device,
        verbose=False,
    )

    names = model.names
    detections: List[Detection] = []

    for result in results:
        boxes = result.boxes
        if boxes is None:
            continue

        xyxy = boxes.xyxy.cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        classes = boxes.cls.cpu().numpy()

        for xy, cf, cl in zip(xyxy, confs, classes):
            class_name = names.get(int(cl), str(int(cl)))
            if class_name != TARGET_CLASS:
                continue

            detections.append(
                Detection(
                    detection_id=0,
                    class_name=class_name,
                    confidence=float(cf),
                    x1=int(round(xy[0])),
                    y1=int(round(xy[1])),
                    x2=int(round(xy[2])),
                    y2=int(round(xy[3])),
                )
            )

    detections.sort(key=lambda d: d.confidence, reverse=True)
    for idx, det in enumerate(detections, start=1):
        det.detection_id = idx

    return detections