from dataclasses import dataclass
from typing import Optional

@dataclass
class TrainConfig:
    data_yaml: str
    epochs: int = 100
    batch: int = 8
    imgsz: int = 640
    device: str = "0"
    project: str = "runs/detect"
    name: str = "meckel_v1"
    workers: int = 2
    patience: int = 20
    cache: Optional[str] = "ram"