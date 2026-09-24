const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const CLASS_COLORS = { periapical_lesion: "#FF3B30", caries: "#FF9500" };
const CLASS_SHORT = { periapical_lesion: "PAL", caries: "CAR" };
const STATUS_COLORS = { confirmed: "#34C759", dismissed: "#8E8E93", adjusted: "#30B0F0" };

const state = {
  file: null,
  imageSrc: null,
  imageName: null,
  img: new Image(),
  quality: null,
  findings: [],
  thresholds: { periapical_lesion: 0.30, caries: 0.40 },
  drag: null,
};

/* ---------- navigation ---------- */
function show(view) {
  $$(".view").forEach((v) => v.classList.remove("active"));
  $("#view-" + view).classList.add("active");
  $$(".nav-btn").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
  if (view === "hub") loadHub();
  if (view === "results") initCanvas();
}
$$(".nav-btn").forEach((b) => b.addEventListener("click", () => show(b.dataset.view)));
$$("[data-goto]").forEach((b) =>
  b.addEventListener("click", () => { resetScan(); show(b.dataset.goto); })
);

function resetScan() {
  state.file = null;
  state.imageSrc = null;
  state.imageName = null;
  state.quality = null;
  state.findings = [];
  $("#file-input").value = "";
  $("#preview").hidden = true;
  $("#drop-hint").hidden = false;
  $("#quality-card").hidden = true;
  $("#analyze-card").hidden = true;
  $("#sample-select").value = "";
}

/* ---------- image input ---------- */
$("#dropzone").addEventListener("click", () => $("#file-input").click());
$("#file-input").addEventListener("change", (e) => {
  const f = e.target.files[0];
  if (!f) return;
  if (f.size > 10 * 1024 * 1024) { alert("File too large (max 10MB)."); return; }
  state.file = f;
  setImage(URL.createObjectURL(f), f.name);
});
$("#sample-select").addEventListener("change", (e) => {
  if (!e.target.value) return;
  state.file = null;
  setImage("/api/samples/" + encodeURIComponent(e.target.value), "sample:" + e.target.value);
});

function setImage(src, name) {
  state.imageSrc = src;
  state.imageName = name;
  state.img = new Image();
  state.img.src = src;
  const prev = $("#preview");
  prev.src = src;
  prev.hidden = false;
  $("#drop-hint").hidden = true;
  fetchQuality();
}

function inputFormData() {
  const fd = new FormData();
  if (state.file) fd.append("file", state.file);
  else fd.append("sample", state.imageName.replace("sample:", ""));
  return fd;
}

/* ---------- quality gate ---------- */
async function fetchQuality() {
  const res = await fetch("/api/quality", { method: "POST", body: inputFormData() });
  if (!res.ok) { alert("Quality check failed."); return; }
  state.quality = await res.json();
  renderQuality(state.quality);
}

function renderQuality(q) {
  $("#quality-card").hidden = false;
  $("#analyze-card").hidden = false;
  const list = $("#quality-list");
  list.innerHTML = "";
  q.checks.forEach((c) => {
    list.insertAdjacentHTML(
      "beforeend",
      `<li>${c.passed ? "✅" : "️"} <strong>${c.name}</strong> — ${c.detail}</li>`
    );
  });
  $("#quality-block").hidden = q.ok;
  $("#quality-override-wrap").hidden = q.ok;
}

/* ---------- thresholds ---------- */
["pal", "car"].forEach((k) => {
  const el = $("#" + k + "-thr");
  el.addEventListener("input", () => {
    const v = parseFloat(el.value);
    $("#" + k + "-thr-val").textContent = v.toFixed(2);
    state.thresholds[k === "pal" ? "periapical_lesion" : "caries"] = v;
  });
});

/* ---------- analyze ---------- */
$("#analyze-btn").addEventListener("click", async () => {
  if (!state.quality) return;
  if (!state.quality.ok && !$("#quality-override").checked) return;

  const fd = inputFormData();
  fd.append("pal_threshold", state.thresholds.periapical_lesion);
  fd.append("car_threshold", state.thresholds.caries);

  $("#analyze-status").hidden = false;
  const res = await fetch("/api/predict", { method: "POST", body: fd });
  $("#analyze-status").hidden = true;
  if (!res.ok) { alert("Analysis failed: " + (await res.text())); return; }

  const data = await res.json();
  if (!data.detections.length) {
    alert("No findings above the current thresholds. Lower them and re-analyze.");
    return;
  }
  state.findings = data.detections.map((d) => ({ ...d, status: "pending", meta: {} }));
  show("results");
  renderFindings();
});

/* ---------- canvas ---------- */
const canvas = $("#canvas");
const ctx = canvas.getContext("2d");

function canvasScale() { return canvas.width / state.img.naturalWidth; }

function initCanvas() {
  if (!state.img.complete || !state.img.naturalWidth) {
    state.img.onload = initCanvas;
    return;
  }
  const maxW = Math.min(1000, canvas.parentElement.clientWidth - 40);
  const scale = Math.min(1, maxW / state.img.naturalWidth);
  canvas.width = Math.round(state.img.naturalWidth * scale);
  canvas.height = Math.round(state.img.naturalHeight * scale);
  draw();
}
window.addEventListener("resize", () => {
  if ($("#view-results").classList.contains("active")) initCanvas();
});

function draw() {
  if (!state.img.complete || !state.img.naturalWidth) return;
  const s = canvasScale();
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(state.img, 0, 0, canvas.width, canvas.height);

  state.findings.forEach((f) => {
    const [x1, y1, x2, y2] = f.box;
    const color = f.status === "pending"
      ? (CLASS_COLORS[f.class_name] || "#FF3B30")
      : (STATUS_COLORS[f.status] || "#FF3B30");

    ctx.strokeStyle = color;
    ctx.lineWidth = Math.max(2, canvas.width / 350);
    ctx.strokeRect(x1 * s, y1 * s, (x2 - x1) * s, (y2 - y1) * s);

    const label = `#${f.id} ${CLASS_SHORT[f.class_name] || f.class_name} ${Math.round(f.confidence * 100)}%`;
    ctx.font = `${Math.max(11, canvas.width / 55)}px sans-serif`;
    const w = ctx.measureText(label).width;
    const ty = Math.max(18, y1 * s);
    ctx.fillStyle = color;
    ctx.fillRect(x1 * s, ty - 16, w + 8, 18);
    ctx.fillStyle = "#fff";
    ctx.fillText(label, x1 * s + 4, ty - 3);

    ctx.fillStyle = color;
    ctx.fillRect(x2 * s - 6, y2 * s - 6, 12, 12);
  });
}

function toImageCoords(evt) {
  const rect = canvas.getBoundingClientRect();
  const s = canvasScale();
  return [(evt.clientX - rect.left) / s, (evt.clientY - rect.top) / s];
}

canvas.addEventListener("pointerdown", (evt) => {
  const [px, py] = toImageCoords(evt);
  for (let i = state.findings.length - 1; i >= 0; i--) {
    const [x1, y1, x2, y2] = state.findings[i].box;
    if (Math.abs(px - x2) < 12 && Math.abs(py - y2) < 12) {
      state.drag = { i, mode: "resize" };
      canvas.setPointerCapture(evt.pointerId);
      return;
    }
    if (px >= x1 && px <= x2 && py >= y1 && py <= y2) {
      state.drag = { i, mode: "move", dx: px - x1, dy: py - y1 };
      canvas.setPointerCapture(evt.pointerId);
      return;
    }
  }
});

canvas.addEventListener("pointermove", (evt) => {
  if (!state.drag) return;
  const [px, py] = toImageCoords(evt);
  const f = state.findings[state.drag.i];
  const W = state.img.naturalWidth, H = state.img.naturalHeight;

  if (state.drag.mode === "move") {
    const w = f.box[2] - f.box[0], h = f.box[3] - f.box[1];
    const nx = Math.min(Math.max(0, px - state.drag.dx), W - w);
    const ny = Math.min(Math.max(0, py - state.drag.dy), H - h);
    f.box = [Math.round(nx), Math.round(ny), Math.round(nx + w), Math.round(ny + h)];
  } else {
    f.box[2] = Math.round(Math.min(Math.max(f.box[0] + 8, px), W));
    f.box[3] = Math.round(Math.min(Math.max(f.box[1] + 8, py), H));
  }
  f.status = "adjusted";
  draw();
  updateCardStatus(state.drag.i);
});

canvas.addEventListener("pointerup", () => { state.drag = null; });

/* ---------- findings cards ---------- */
function renderFindings() {
  const wrap = $("#findings");
  wrap.innerHTML = "";
  state.findings.forEach((f, i) => {
    const card = document.createElement("div");
    card.className = "card finding";
    card.id = "finding-" + i;
    card.innerHTML = `
      <div class="row between">
        <strong>#${f.id} — <span class="f-label">${f.meta.label || f.class_name}</span> · model ${Math.round(f.confidence * 100)}%</strong>
        <span class="f-status">Status: <b>${f.status}</b></span>
      </div>
      <div class="row">
        <button class="btn ok" data-act="confirm">✅ Confirm</button>
        <button class="btn" data-act="dismiss">❌ Dismiss</button>
      </div>
      <details><summary>✏️ Correct</summary>
        <label>Label
          <select data-f="label">
            <option>periapical_lesion</option><option>caries</option><option>not_a_finding</option>
          </select>
        </label>
        <label>Clinician confidence
          <input type="range" min="0" max="100" data-f="confidence" /> <span data-f="confidence-val"></span>
        </label>
        <label>Notes
          <textarea data-f="notes" rows="2" placeholder="Optional notes"></textarea>
        </label>
      </details>`;

    const sel = card.querySelector('[data-f="label"]');
    sel.value = f.meta.label || f.class_name;
    const rng = card.querySelector('[data-f="confidence"]');
    rng.value = f.meta.confidence ?? Math.round(f.confidence * 100);
    card.querySelector('[data-f="confidence-val"]').textContent = rng.value + "%";
    card.querySelector('[data-f="notes"]').value = f.meta.notes || "";

    sel.addEventListener("change", () => {
      f.meta.label = sel.value;
      card.querySelector(".f-label").textContent = sel.value;
      f.status = "adjusted"; updateCardStatus(i);
    });
    rng.addEventListener("input", () => {
      f.meta.confidence = +rng.value;
      card.querySelector('[data-f="confidence-val"]').textContent = rng.value + "%";
    });
    rng.addEventListener("change", () => { f.status = "adjusted"; updateCardStatus(i); });
    card.querySelector('[data-f="notes"]').addEventListener("input", (e) => { f.meta.notes = e.target.value; });
    card.querySelector('[data-act="confirm"]').addEventListener("click", () => { f.status = "confirmed"; updateCardStatus(i); draw(); });
    card.querySelector('[data-act="dismiss"]').addEventListener("click", () => { f.status = "dismissed"; updateCardStatus(i); draw(); });

    wrap.appendChild(card);
  });
}

function updateCardStatus(i) {
  const card = $("#finding-" + i);
  if (card) card.querySelector(".f-status b").textContent = state.findings[i].status;
}

/* ---------- finish + report ---------- */
function reviewPayload() {
  return {
    image_name: state.imageName,
    thresholds: state.thresholds,
    findings: state.findings.map((f) => ({
      detection_id: f.id,
      class: f.class_name,
      model_confidence: f.confidence,
      box: f.box,
      status: f.status,
      ...f.meta,
    })),
  };
}

$("#finish-btn").addEventListener("click", async () => {
  const res = await fetch("/api/reviews", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(reviewPayload()),
  });
  if (!res.ok) { alert("Failed to save review."); return; }
  show("success");
});

$("#report-btn").addEventListener("click", async () => {
  const res = await fetch("/api/report", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(reviewPayload()),
  });
  const data = await res.json();
  const blob = new Blob([data.markdown], { type: "text/markdown" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "meckel_analysis_report.md";
  a.click();
});

/* ---------- feedback hub ---------- */
async function loadHub() {
  const res = await fetch("/api/reviews");
  const { reviews } = await res.json();
  const metrics = $("#hub-metrics");
  metrics.innerHTML = "";
  if (!reviews.length) {
    $("#hub-table").hidden = true;
    $("#hub-empty").hidden = false;
    return;
  }
  $("#hub-table").hidden = false;
  $("#hub-empty").hidden = true;

  let total = 0;
  const counts = { confirmed: 0, dismissed: 0, adjusted: 0, pending: 0 };
  const tbody = $("#hub-table tbody");
  tbody.innerHTML = "";

  reviews.forEach((r) => {
    const rc = { confirmed: 0, dismissed: 0, adjusted: 0, pending: 0 };
    (r.findings || []).forEach((f) => {
      total++; counts[f.status] = (counts[f.status] || 0) + 1; rc[f.status] = (rc[f.status] || 0) + 1;
    });
    tbody.insertAdjacentHTML(
      "beforeend",
      `<tr><td>${r.timestamp || ""}</td><td>${r.image_name || ""}</td><td>${(r.findings || []).length}</td><td>${rc.confirmed}</td><td>${rc.dismissed}</td><td>${rc.adjusted}</td></tr>`
    );
  });

  [["Total Reviews", reviews.length], ["Total Findings", total], ["Confirmed", counts.confirmed], ["Dismissed", counts.dismissed]]
    .forEach(([k, v]) =>
      metrics.insertAdjacentHTML("beforeend", `<div class="card metric"><b>${v}</b><span>${k}</span></div>`)
    );
}

/* ---------- boot ---------- */
(async () => {
  const res = await fetch("/api/samples");
  const { samples } = await res.json();
  const sel = $("#sample-select");
  samples.forEach((n) => sel.insertAdjacentHTML("beforeend", `<option value="${n}">${n}</option>`));
})();