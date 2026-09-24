from __future__ import annotations

import io
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

from meckel.ui.inference import (
    DEFAULT_THRESHOLDS,
    Detection,
    load_model,
    run_detection,
)
from meckel.ui.quality import check_quality
from meckel.ui.report import build_report
from meckel.ui.review import load_reviews, save_review

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
SAMPLE_DIR = BASE_DIR / "samples"
WEIGHTS_PATH = BASE_DIR / "weights" / "meckel_v1_best.pt"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png"}

state: Dict = {"model": None}


@asynccontextmanager
async def lifespan(app: FastAPI):
    state["model"] = load_model(WEIGHTS_PATH)
    yield
    state["model"] = None


app = FastAPI(title="Meckel AI API", lifespan=lifespan)


def _load_input(file: Optional[UploadFile], sample: str) -> Image.Image:
    if sample:
        path = (SAMPLE_DIR / sample).resolve()
        if not path.is_file() or path.parent != SAMPLE_DIR.resolve():
            raise HTTPException(status_code=404, detail="Sample not found")
        data = path.read_bytes()
    else:
        if file is None:
            raise HTTPException(status_code=400, detail="No image provided")
        data = file.file.read()

    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")

    try:
        return Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Unsupported or corrupt image")


@app.get("/api/health")
def health():
    return {"status": "ok", "model_loaded": state["model"] is not None}


@app.get("/api/samples")
def list_samples():
    if not SAMPLE_DIR.is_dir():
        return {"samples": []}
    names = sorted(
        p.name for p in SAMPLE_DIR.iterdir() if p.suffix.lower() in ALLOWED_SUFFIXES
    )
    return {"samples": names}


@app.get("/api/samples/{name}")
def get_sample(name: str):
    path = (SAMPLE_DIR / name).resolve()
    if not path.is_file() or path.parent != SAMPLE_DIR.resolve():
        raise HTTPException(status_code=404, detail="Sample not found")
    return FileResponse(path)


@app.post("/api/quality")
async def quality(file: Optional[UploadFile] = File(None), sample: str = Form("")):
    image = _load_input(file, sample)
    report = check_quality(image)
    return {
        "ok": report.ok,
        "checks": [
            {"name": n, "passed": p, "detail": d} for (n, p, d) in report.checks
        ],
    }


@app.post("/api/predict")
async def predict(
    file: Optional[UploadFile] = File(None),
    sample: str = Form(""),
    pal_threshold: float = Form(DEFAULT_THRESHOLDS["periapical_lesion"]),
    car_threshold: float = Form(DEFAULT_THRESHOLDS["caries"]),
):
    image = _load_input(file, sample)
    thresholds = {
        "periapical_lesion": pal_threshold,
        "caries": car_threshold,
    }
    detections = run_detection(state["model"], image, thresholds)
    return {
        "image_name": sample if sample else (file.filename if file else "upload"),
        "width": image.width,
        "height": image.height,
        "detections": [
            {
                "id": d.detection_id,
                "class_name": d.class_name,
                "confidence": round(d.confidence, 4),
                "box": [d.x1, d.y1, d.x2, d.y2],
            }
            for d in detections
        ],
    }


@app.post("/api/reviews")
def create_review(payload: dict):
    image_name = payload.get("image_name")
    if not image_name:
        raise HTTPException(status_code=400, detail="image_name required")
    path = save_review(image_name, payload)
    return {"ok": True, "log": str(path)}


@app.get("/api/reviews")
def get_reviews():
    return {"reviews": load_reviews()}


@app.post("/api/report")
def create_report(payload: dict):
    findings = payload.get("findings", [])
    detections = [
        Detection(
            detection_id=f.get("detection_id", 0),
            class_name=f.get("class", f.get("class_name", "periapical_lesion")),
            confidence=float(f.get("model_confidence", 0.0)),
            x1=int(f["box"][0]),
            y1=int(f["box"][1]),
            x2=int(f["box"][2]),
            y2=int(f["box"][3]),
        )
        for f in findings
    ]
    statuses = {
        d.detection_id: f.get("status", "pending")
        for d, f in zip(detections, findings)
    }
    meta = {
        d.detection_id: {k: f[k] for k in ("label", "confidence", "notes") if k in f}
        for d, f in zip(detections, findings)
    }
    markdown = build_report(
        payload.get("image_name", "upload"),
        detections,
        statuses,
        meta,
        payload.get("thresholds", DEFAULT_THRESHOLDS),
    )
    return {"markdown": markdown}


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")