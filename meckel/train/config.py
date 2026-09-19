from dataclasses import dataclass

@dataclass
class TrainConfig:
    data_yaml: str
    epochs: int = 50
    batch: int = 8
    imgsz: int = 640
    device: str = "0"  # "0" for first GPU, "cpu" for CPU
    project: str = "runs/detect"
    name: str = "meckel_v1"
    workers: int = 0   # 0 is safest for Windows multiprocessing to avoid BrokenPipeError
    patience: int = 15 # early stopping patience