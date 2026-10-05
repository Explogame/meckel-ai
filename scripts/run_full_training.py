import argparse
from pathlib import Path
from meckel.train.config import TrainConfig
from meckel.train.pipeline import run_training

def main() -> None:
    parser = argparse.ArgumentParser(description="Run full Meckel AI training.")
    parser.add_argument("--data", type=str, required=True, help="Absolute path to data.yaml")
    parser.add_argument("--name", type=str, default="meckel_v1_full")
    args = parser.parse_args()

    config = TrainConfig(
        data_yaml=str(Path(args.data).resolve()),
        epochs=100,
        batch=8,
        imgsz=640,
        device="0",
        project="runs/detect",
        name=args.name,
        workers=0,
        patience=20,
        cache=False,
    )
    
    print(f"Starting training run '{args.name}': {config.epochs} epochs, batch {config.batch}")
    save_dir = run_training(config)
    print(f"Training complete. Best weights saved to: {save_dir}/weights/best.pt")

if __name__ == "__main__":
    main()