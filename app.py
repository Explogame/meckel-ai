from __future__ import annotations

from pathlib import Path

import streamlit as st
from PIL import Image

from meckel.ui.inference import DEFAULT_THRESHOLDS, load_model, run_detection
from meckel.ui.overlay import draw_detections
from meckel.ui.quality import check_quality
from meckel.ui.report import build_report
from meckel.ui.review import load_reviews, save_review

st.set_page_config(page_title="Meckel AI", page_icon="🦷", layout="wide")

WEIGHTS_PATH = "weights/meckel_v1_best.pt"
SAMPLE_DIR = Path("samples")
MAX_UPLOAD_MB = 10

DENTAL_TIPS = [
    "Periapical radiolucencies often appear as dark, round or oval areas at the tip of the tooth root.",
    "The periodontal ligament space surrounds the tooth root and can mimic early radiolucencies when widened.",
    "Cervical burnout is a normal dark band at the tooth neck and is a common false-positive mimic.",
    "Horizontal bone loss is assessed by comparing the crestal bone level to the cementoenamel junction.",
    "Always correlate radiographic findings with clinical symptoms before confirming a diagnosis.",
]

LABEL_OPTIONS = ["periapical_lesion", "caries", "not_a_finding"]


@st.cache_resource
def get_model():
    return load_model(WEIGHTS_PATH)


def init_state() -> None:
    # Handle pending navigation before widgets are instantiated
    if "pending_page" in st.session_state:
        st.session_state.page = st.session_state.pop("pending_page")
    defaults = {
        "detections": [],
        "statuses": {},
        "meta": {},
        "image_name": None,
        "reviewed": False,
        "tip_index": 0,
        "thresholds": dict(DEFAULT_THRESHOLDS),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_scan() -> None:
    st.session_state.detections = []
    st.session_state.statuses = {}
    st.session_state.meta = {}
    st.session_state.image_name = None
    st.session_state.reviewed = False


def tip_carousel(key_prefix: str) -> None:
    col_prev, col_tip, col_next = st.columns([1, 6, 1])
    with col_prev:
        if st.button("‹", key=f"{key_prefix}_prev"):
            st.session_state.tip_index = (st.session_state.tip_index - 1) % len(DENTAL_TIPS)
            st.rerun()
    with col_tip:
        st.info(
            f"**Dental Tip**\n\n{DENTAL_TIPS[st.session_state.tip_index]}  \n"
            f"({st.session_state.tip_index + 1} / {len(DENTAL_TIPS)})"
        )
    with col_next:
        if st.button("›", key=f"{key_prefix}_next"):
            st.session_state.tip_index = (st.session_state.tip_index + 1) % len(DENTAL_TIPS)
            st.rerun()


init_state()

st.sidebar.title("🦷 Meckel AI")
st.sidebar.caption("Better insights. Safer decisions.")
page = st.sidebar.radio(
    "Navigate",
    ["Home", "New Scan", "Feedback Hub"],
    key="page",
    label_visibility="collapsed",
)
st.sidebar.markdown("---")
st.sidebar.warning("AI assistance only. Not a diagnosis. Every finding requires clinician review.")
st.sidebar.caption("Model trained on dental-xray-dataset by shreku (Roboflow Universe), CC BY 4.0.")

# ---------------- HOME ----------------
if page == "Home":
    st.title("Smarter Radiographs. Better Decisions.")
    st.markdown(
        "Meckel AI helps dental professionals detect and analyze **periapical lesions** and **caries**, "
        "and presents findings for clinical confirmation."
    )
    c1, c2, c3 = st.columns(3)
    c1.markdown("##### 🔍 Detect\nAI finds periapical lesions and caries on radiographs.")
    c2.markdown("##### 📍 Localize\nShows the exact location of each finding on your X-ray.")
    c3.markdown("##### 🩺 Present\nFindings are presented for clinician review — never a diagnosis.")
    st.markdown("---")
    if st.button("Upload Radiograph →", type="primary"):
        st.session_state["pending_page"] = "New Scan"
        st.rerun()
    st.caption("Supported formats: JPG, PNG  |  Max size: 10MB")
    tip_carousel("home")

# ---------------- NEW SCAN ----------------
elif page == "New Scan":
    st.title("New Scan")
    st.caption("1 Upload  →  2 Quality Check  →  3 Analyze  →  4 Verify")

    uploaded = st.file_uploader("Upload a periapical radiograph", type=["jpg", "jpeg", "png"])

    if uploaded is not None:
        size_mb = uploaded.size / (1024 * 1024)
        if size_mb > MAX_UPLOAD_MB:
            st.error("Unsupported image: file too large. We currently support JPG and PNG files up to 10MB.")
            st.stop()

    sample_names = []
    if SAMPLE_DIR.is_dir():
        sample_names = sorted(
            p.name for p in SAMPLE_DIR.iterdir()
            if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
        )

    sample_choice = st.selectbox(
        "Or test with a bundled sample image",
        [""] + sample_names,
        format_func=lambda s: s if s else "-- choose a sample --",
    )

    image = None
    source_name = None
    if uploaded is not None:
        source_name = uploaded.name
        image = Image.open(uploaded).convert("RGB")
    elif sample_choice:
        source_name = f"sample:{sample_choice}"
        image = Image.open(SAMPLE_DIR / sample_choice).convert("RGB")

    if source_name is not None and source_name != st.session_state.image_name:
        reset_scan()
        st.session_state.image_name = source_name

    if source_name is None:
        if st.session_state.image_name is not None:
            reset_scan()
        st.info("Upload a radiograph or pick a bundled sample to begin.")
        tip_carousel("idle")
        st.stop()

    # ---- Step 2: quality gate ----
    st.subheader("Image Quality Check")
    report = check_quality(image)

    preview, checks_col = st.columns([1, 2])
    preview.image(image, caption="Preview", use_container_width=True)
    with checks_col:
        for name, passed, detail in report.checks:
            icon = "✅" if passed else "⚠️"
            st.markdown(f"{icon} **{name}** — {detail}")

    if not report.ok:
        st.error("Image Quality Too Low — the uploaded image may be blurry or too low resolution for accurate analysis.")
        override = st.checkbox("Demo mode: continue anyway")
        if not override:
            st.stop()

    tip_carousel("scan")

    tc1, tc2 = st.columns(2)
    pal_thr = tc1.slider(
        "Periapical lesion threshold", 0.05, 0.90,
        DEFAULT_THRESHOLDS["periapical_lesion"], 0.05,
    )
    car_thr = tc2.slider(
        "Caries threshold", 0.05, 0.90,
        DEFAULT_THRESHOLDS["caries"], 0.05,
    )
    thresholds = {"periapical_lesion": pal_thr, "caries": car_thr}

    # ---- Step 3: analyze ----
    if st.button("Analyze Radiograph", type="primary"):
        with st.status("Analyzing your radiograph…", expanded=True) as status:
            st.write("✅ Image quality check")
            st.write("✅ Preprocessing")
            st.write("⏳ Detecting findings…")
            model = get_model()
            st.session_state.detections = run_detection(model, image, thresholds)
            st.session_state.statuses = {d.detection_id: "pending" for d in st.session_state.detections}
            st.session_state.meta = {}
            st.session_state.reviewed = False
            st.session_state.thresholds = thresholds
            st.write("✅ Detecting findings")
            st.write("✅ Preparing results")
            status.update(label="Analysis complete", state="complete")

    detections = st.session_state.detections

    # ---- Success screen ----
    if st.session_state.reviewed:
        st.subheader("Analysis Complete!")
        st.success("Your radiograph has been analyzed and the review was saved.")

        report_md = build_report(
            st.session_state.image_name,
            detections,
            st.session_state.statuses,
            st.session_state.meta,
            st.session_state.thresholds,
        )
        with st.expander("📄 View Report"):
            st.markdown(report_md)
        st.download_button(
            "Download Report (Markdown)",
            report_md,
            file_name="meckel_analysis_report.md",
        )
        if st.button("Upload Another Image"):
            reset_scan()
            st.rerun()
        st.stop()

    if not detections:
        st.info(
            "No findings detected above the current thresholds. "
            "Lower the per-class thresholds and re-analyze if you expect a finding."
        )
        st.stop()

    # ---- Step 4: results + verify ----
    st.subheader("Analysis Results")
    overlay = draw_detections(image, detections, st.session_state.statuses)

    left, right = st.columns(2)
    left.image(image, caption="Original Radiograph", use_container_width=True)
    right.image(overlay, caption="AI Overlay", use_container_width=True)

    st.markdown("---")
    st.subheader("Review Findings")

    for det in detections:
        status = st.session_state.statuses.get(det.detection_id, "pending")
        m = st.session_state.meta.get(det.detection_id, {})

        with st.container(border=True):
            head = st.columns([3, 1])
            label_shown = m.get("label", det.class_name)
            head[0].markdown(f"**Finding #{det.detection_id} — {label_shown}** — model confidence {det.confidence:.0%}")
            head[1].markdown(f"Status: **{status}**")

            btns = st.columns(3)
            if btns[0].button("✅ Confirm", key=f"confirm_{det.detection_id}"):
                st.session_state.statuses[det.detection_id] = "confirmed"
                st.rerun()
            if btns[1].button("❌ Dismiss", key=f"dismiss_{det.detection_id}"):
                st.session_state.statuses[det.detection_id] = "dismissed"
                st.rerun()

            with btns[2]:
                with st.expander("✏️ Correct"):
                    with st.form(f"correct_{det.detection_id}"):
                        st.caption("Adjust Location (pixel coordinates)")
                        c1, c2, c3, c4 = st.columns(4)
                        x1 = c1.number_input("x1", value=det.x1, step=1, format="%d", key=f"x1_{det.detection_id}")
                        y1 = c2.number_input("y1", value=det.y1, step=1, format="%d", key=f"y1_{det.detection_id}")
                        x2 = c3.number_input("x2", value=det.x2, step=1, format="%d", key=f"x2_{det.detection_id}")
                        y2 = c4.number_input("y2", value=det.y2, step=1, format="%d", key=f"y2_{det.detection_id}")

                        current_label = m.get("label", det.class_name)
                        label_idx = LABEL_OPTIONS.index(current_label) if current_label in LABEL_OPTIONS else 0
                        new_label = st.selectbox("Change Label", LABEL_OPTIONS, index=label_idx, key=f"label_{det.detection_id}")
                        new_conf = st.slider(
                            "Clinician Confidence Level (%)", 0, 100,
                            int(m.get("confidence", round(det.confidence * 100))),
                            key=f"conf_{det.detection_id}",
                        )
                        notes = st.text_area(
                            "Additional Notes (optional)",
                            value=m.get("notes", ""),
                            key=f"notes_{det.detection_id}",
                        )

                        if st.form_submit_button("Save Correction"):
                            det.x1, det.y1, det.x2, det.y2 = int(x1), int(y1), int(x2), int(y2)
                            st.session_state.meta[det.detection_id] = {
                                "label": new_label,
                                "confidence": new_conf,
                                "notes": notes,
                            }
                            st.session_state.statuses[det.detection_id] = "adjusted"
                            st.rerun()

    st.markdown("---")
    if st.button("Finish Review & Save Feedback", type="primary"):
        payload = {
            "thresholds": st.session_state.thresholds,
            "findings": [
                {
                    "detection_id": d.detection_id,
                    "class": d.class_name,
                    "model_confidence": round(d.confidence, 4),
                    "box": [d.x1, d.y1, d.x2, d.y2],
                    "status": st.session_state.statuses.get(d.detection_id, "pending"),
                    **st.session_state.meta.get(d.detection_id, {}),
                }
                for d in detections
            ],
        }
        save_review(st.session_state.image_name, payload)
        st.session_state.reviewed = True
        st.rerun()

# ---------------- FEEDBACK HUB ----------------
elif page == "Feedback Hub":
    st.title("Feedback Hub")
    st.caption("Clinician corrections that will seed future model improvements.")

    reviews = load_reviews()
    if not reviews:
        st.info("No reviews saved yet. Complete a scan review to populate this hub.")
        st.stop()

    total_findings = 0
    status_counts = {"confirmed": 0, "dismissed": 0, "adjusted": 0, "pending": 0}
    rows = []
    for r in reviews:
        findings = r.get("findings", [])
        total_findings += len(findings)
        row_counts = {"confirmed": 0, "dismissed": 0, "adjusted": 0, "pending": 0}
        for f in findings:
            stt = f.get("status", "pending")
            status_counts[stt] = status_counts.get(stt, 0) + 1
            row_counts[stt] = row_counts.get(stt, 0) + 1
        rows.append(
            {
                "timestamp": r.get("timestamp", ""),
                "image": r.get("image_name", ""),
                "findings": len(findings),
                "confirmed": row_counts["confirmed"],
                "dismissed": row_counts["dismissed"],
                "adjusted": row_counts["adjusted"],
            }
        )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Reviews", len(reviews))
    m2.metric("Total Findings", total_findings)
    m3.metric("Confirmed", status_counts["confirmed"])
    m4.metric("Dismissed", status_counts["dismissed"])

    st.subheader("Recent Reviews")
    st.dataframe(rows, use_container_width=True)