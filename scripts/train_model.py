import argparse
from pathlib import Path
from meckel.train.config import TrainConfig
from meckel.train.pipeline import run_training

def main() -> None:
    parser = argparse.ArgumentParser(description="Train Meckel AI YOLOv8 model.")
    parser.add_argument("--data", type=str, required=True, help="Absolute path to data.yaml")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", type=str, default="0")
    parser.add_argument("--project", type=str, default="runs/detect")
    parser.add_argument("--name", type=str, default="meckel_v1")
    args = parser.parse_args()

    config = TrainConfig(
        data_yaml=str(Path(args.data).resolve()),
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        device=args.device,
        project=args.project,
        name=args.name,
    )
    
    save_dir = run_training(config)
    print(f"Training complete. Results and weights saved to: {save_dir}")

if __name__ == "__main__":
    main()