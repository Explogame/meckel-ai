import argparse
from pathlib import Path
import torch
from meckel.train.config import TrainConfig
from meckel.train.pipeline import run_training

def main() -> None:
    parser = argparse.ArgumentParser(description="Run a 1-epoch smoke test.")
    parser.add_argument("--data", type=str, required=True, help="Absolute path to data.yaml")
    args = parser.parse_args()

    print(f"CUDA available: {torch.cuda.is_available()}")
    if not torch.cuda.is_available():
        print("WARNING: CUDA not found. Training will fall back to CPU and be very slow.")

    config = TrainConfig(
        data_yaml=str(Path(args.data).resolve()),
        epochs=1,
        batch=4,  # Smaller batch for smoke test to be safe on 4GB VRAM
        imgsz=640,
        device="0",
        project="runs/detect",
        name="smoke_test",
        workers=0,
    )
    
    save_dir = run_training(config)
    print(f"Smoke test complete. Results saved to: {save_dir}")
    print("Check the console output above to ensure there were no data loading errors.")

if __name__ == "__main__":
    main()