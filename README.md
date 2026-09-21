# Meckel AI

AI-assisted dental radiograph analysis copilot for dentists.

Live demo: (paste your Streamlit Cloud URL here after deploying)

## V1 workflow

Detect -> Localize -> Present (human-in-the-loop review)

Measurement is deferred and may be added later.

## Product constraints

- Human-in-the-loop only: every finding is Confirmed / Dismissed / Adjusted by a clinician
- No autonomous diagnosis
- No LLM dependency in the core detection pipeline

## Model

- Architecture: YOLOv8n (Ultralytics)
- Target class: periapical_lesion (caries predictions ignored at inference)
- Validation (best epoch 65): periapical_lesion P 0.532 / R 0.726 / mAP50 0.578

## Dataset & attribution

- dental-xray-dataset by shreku, Roboflow Universe
  https://universe.roboflow.com/shreku/dental-xray-dataset
- License: CC BY 4.0
- Model weights committed in this repo are derived from that dataset.

## Run locally

    python -m venv .venv
    # activate it, then:
    python -m pip install -e ".[train]"
    python -m pip install -e ".[demo]"
    streamlit run app.py

## Repo layout

- meckel/io: label + dataset parsing
- meckel/viz: annotation drawing for label review
- meckel/train: training pipeline
- meckel/ui: inference, overlay, quality, report, review helpers
- scripts/: runnable entrypoints
- app.py: Streamlit demo