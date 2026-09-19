from pathlib import Path
from typing import Any, Dict
from ultralytics import YOLO
from .config import TrainConfig

def run_training(config: TrainConfig) -> Path:
    """
    Initialize YOLOv8n and run training.
    Returns the exact directory where results and weights are saved.
    """
    model = YOLO("yolov8n.pt")  
    
    kwargs: Dict[str, Any] = dict(
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
    
    if config.cache is not None:
        kwargs["cache"] = config.cache
        
    model.train(**kwargs)
    
    # Ultralytics stores the exact path used internally
    save_dir = Path(model.trainer.save_dir)
    return save_dir