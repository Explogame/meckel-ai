from pathlib import Path
from ultralytics import YOLO
from .config import TrainConfig

def run_training(config: TrainConfig) -> Path:
    """
    Initialize YOLOv8n and run training.
    Returns the directory where results and weights are saved.
    """
    # Downloads yolov8n.pt automatically if not present
    model = YOLO("yolov8n.pt")  
    
    model.train(
        data=config.data_yaml,
        epochs=config.epochs,
        batch=config.batch,
        imgsz=config.imgsz,
        device=config.device,
        project=config.project,
        name=config.name,
        exist_ok=True,
        workers=config.workers,
        patience=config.patience,
    )
    
    save_dir = Path(config.project) / config.name
    return save_dir