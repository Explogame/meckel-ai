const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

const CLASS_COLORS = { periapical_lesion: "#FF3B30", caries: "#FF9500" };
const CLASS_SHORT = { periapical_lesion: "PAL", caries: "CAR" };
const CLASS_ICON = { periapical_lesion: "🦷", caries: "⚠️" };
const CLASS_LABEL = { periapical_lesion: "Periapical Lesion", caries: "Caries" };
const STATUS_COLORS = { confirmed: "#34C759", dismissed: "#8E8E93", adjusted: "#30B0F0" };

const TIPS = [
  "Periapical radiolucencies often appear as dark, round or oval areas at the tip of the tooth root.",
  "The periodontal ligament space surrounds the tooth root and can mimic early radiolucencies when widened.",
  "Cervical burnout is a normal dark band at the tooth neck and is a common false-positive mimic.",
  "Horizontal bone loss is assessed by comparing the crestal bone level to the cementoenamel junction.",
  "Always correlate radiographic findings with clinical symptoms before confirming a diagnosis.",
];

const TRACK = [
  ["Upload", "Radiograph received"],
  ["Analyze", "AI processing"],
  ["Results", "Review findings"],
  ["Verify", "Confirm or adjust"],
];

const state = {
  file: null, imageSrc: null, imageName: null, img: new Image(),
  quality: null, findings: [], showOverlay: true,
  thresholds: { periapical_lesion: 0.30, caries: 0.40 },
  drag: null, tipIndex: 0, tipTimer: null, stage: 0,
};

/* ---------- navigation & tracker ---------- */
function renderTracker(sel, active) {
  const el = $(sel);
  if (!el) return;
  el.innerHTML = TRACK.map((s, i) => {
    const cls = i < active ? "done" : i === active ? "active" : "";
    return `<div class="tstep ${cls}"><span class="tdot">${i < active ? "✓" : i + 1}</span><span class="tlabel"><b>${s[0]}</b><small>${s[1]}</small></span></div>`;
  }).join("");
}

function show(view) {
  $$(".view").forEach((v) => v.classList.remove("active"));
  $("#view-" + view).classList.add("active");
  $$(".nav-btn").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
  if (view === "home") renderTracker("#tracker-home", 0);
  if (view === "scan") renderTracker("#tracker-scan", state.stage);
  if (view === "results") { renderTracker("#tracker-results", 2); initCanvas(); }
  if (view === "success") renderTracker("#tracker-success", 3);
  if (view === "hub") loadHub();
  window.scrollTo(0, 0);
}
$$(".nav-btn").forEach((b) => b.addEventListener("click", () => show(b.dataset.view)));
$$("[data-goto]").forEach((b) => b.addEventListener("click", () => { resetScan(); show(b.dataset.goto); }));

function resetScan() {
  state.file = null; state.imageSrc = null; state.imageName = null;
  state.quality = null; state.findings = []; state.stage = 0; state.showOverlay = true;
  $("#file-input").value = "";
  $("#preview").hidden = true;
  $("#drop-hint").hidden = false;
  $("#quality-card").hidden = true;
  $("#analyze-card").hidden = true;
  $("#analyzing-card").hidden = true;
  $("#format-error").hidden = true;
  $("#upload-card").hidden = false;
  $("#sample-select").value = "";
  $("#report-card").hidden = true;
  stopTips();
}

/* ---------- image input ---------- */
$("#dropzone").addEventListener("click", () => $("#file-input").click());
$("#format-retry").addEventListener("click", () => $("#file-input").click());

$("#file-input").addEventListener("change", (e) => {
  const f = e.target.files[0];
  if (!f) return;
  const okType = /image\/(jpeg|png)/.test(f.type) || /\.(jpe?g|png)$/i.test(f.name);
  if (!okType) { $("#format-error").hidden = false; return; }
  $("#format-error").hidden = true;
  if (f.size > 10 * 1024 * 1024) { alert("File too large (max 10MB)."); return; }
  state.file = f;
  setImage(URL.createObjectURL(f), f.name);
});

$("#sample-select").addEventListener("change", (e) => {
  if (!e.target.value) return;
  $("#format-error").hidden = true;
  state.file = null;
  setImage("/api/samples/" + encodeURIComponent(e.target.value), "sample:" + e.target.value);
});

function setImage(src, name) {
  state.imageSrc = src; state.imageName = name; state.stage = 0;
  state.img = new Image(); state.img.src = src;
  const prev = $("#preview");
  prev.src = src; prev.hidden = false;
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
  const list = $("#quality-list");
  list.innerHTML = "";
  q.checks.forEach((c) =>
    list.insertAdjacentHTML("beforeend", `<li>${c.passed ? "✅" : "⚠️"} <strong>${c.name}</strong> — ${c.detail}</li>`)
  );
  $("#quality-ok").hidden = !q.ok;
  $("#quality-bad").hidden = q.ok;
  $("#quality-actions").hidden = false;
  $("#override-wrap").hidden = q.ok;
  $("#quality-continue").hidden = !q.ok;
  $("#analyze-card").hidden = true;
}

$("#quality-continue").addEventListener("click", () => {
  state.stage = 1;
  renderTracker("#tracker-scan", 1);
  $("#analyze-card").hidden = false;
  $("#analyze-card").scrollIntoView({ behavior: "smooth" });
});
$("#quality-retry").addEventListener("click", () => resetScan());
$("#quality-override").addEventListener("change", (e) => {
  $("#quality-continue").hidden = !e.target.checked;
});

/* ---------- thresholds ---------- */
["pal", "car"].forEach((k) => {
  const el = $("#" + k + "-thr");
  el.addEventListener("input", () => {
    const v = parseFloat(el.value);
    $("#" + k + "-thr-val").textContent = v.toFixed(2);
    state.thresholds[k === "pal" ? "periapical_lesion" : "caries"] = v;
  });
});

/* ---------- tips carousel ---------- */
function renderTip() {
  $("#tip-text").textContent = TIPS[state.tipIndex];
  $("#tip-count").textContent = `${state.tipIndex + 1} / ${TIPS.length}`;
}
function startTips() {
  renderTip();
  state.tipTimer = setInterval(() => { state.tipIndex = (state.tipIndex + 1) % TIPS.length; renderTip(); }, 5000);
}
function stopTips() { if (state.tipTimer) clearInterval(state.tipTimer); state.tipTimer = null; }
$("#tip-prev").addEventListener("click", () => { state.tipIndex = (state.tipIndex - 1 + TIPS.length) % TIPS.length; renderTip(); });
$("#tip-next").addEventListener("click", () => { state.tipIndex = (state.tipIndex + 1) % TIPS.length; renderTip(); });

/* ---------- analyze ---------- */
function setPipeline(stepStates) {
  $$("#pipeline li").forEach((li, i) => {
    li.className = stepStates[i] || "";
  });
}

$("#analyze-btn").addEventListener("click", async () => {
  $("#analyze-card").hidden = true;
  $("#analyzing-card").hidden = false;
  startTips();
  setPipeline(["done", "done", "active", ""]);
  $("#progress-fill").style.width = "45%";

  const fd = inputFormData();
  fd.append("pal_threshold", state.thresholds.periapical_lesion);
  fd.append("car_threshold", state.thresholds.caries);

  const res = await fetch("/api/predict", { method: "POST", body: fd });
  if (!res.ok) {
    stopTips();
    $("#analyzing-card").hidden = true;
    $("#analyze-card").hidden = false;
    alert("Analysis failed: " + (await res.text()));
    return;
  }
  const data = await res.json();
  setPipeline(["done", "done", "done", "active"]);
  $("#progress-fill").style.width = "85%";

  setTimeout(() => {
    stopTips();
    setPipeline(["done", "done", "done", "done"]);
    $("#progress-fill").style.width = "100%";
    setTimeout(() => {
      $("#analyzing-card").hidden = true;
      if (!data.detections.length) {
        $("#analyze-card").hidden = false;
        alert("No findings above the current thresholds. Lower them and re-analyze.");
        return;
      }
      state.findings = data.detections.map((d) => ({ ...d, status: "pending", meta: {} }));
      $("#results-subtitle").textContent =
        `We found ${state.findings.length} potential finding${state.findings.length > 1 ? "s" : ""} in your radiograph.`;
      show("results");
      renderFindings();
    }, 450);
  }, 500);
});

/* ---------- canvas viewer ---------- */
const canvas = $("#canvas");
const ctx = canvas.getContext("2d");

$("#toggle-overlay").addEventListener("click", () => {
  state.showOverlay = true;
  $("#toggle-overlay").classList.add("active");
  $("#toggle-original").classList.remove("active");
  draw();
});
$("#toggle-original").addEventListener("click", () => {
  state.showOverlay = false;
  $("#toggle-original").classList.add("active");
  $("#toggle-overlay").classList.remove("active");
  draw();
});

function canvasScale() { return canvas.width / state.img.naturalWidth; }

function initCanvas() {
  if (!state.img.complete || !state.img.naturalWidth) { state.img.onload = initCanvas; return; }
  const maxW = Math.min(960, canvas.parentElement.clientWidth - 36);
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
  if (!state.showOverlay) return;

  state.findings.forEach((f) => {
    const [x1, y1, x2, y2] = f.box;
    const color = f.status === "pending" ? (CLASS_COLORS[f.class_name] || "#FF3B30") : (STATUS_COLORS[f.status] || "#FF3B30");
    ctx.strokeStyle = color;
    ctx.lineWidth = Math.max(2, canvas.width / 350);
    ctx.strokeRect(x1 * s, y1 * s, (x2 - x1) * s, (y2 - y1) * s);

    const label = `${CLASS_LABEL[f.class_name] || f.class_name} · ${Math.round(f.confidence * 100)}%`;
    ctx.font = `600 ${Math.max(11, canvas.width / 60)}px Inter, sans-serif`;
    const w = ctx.measureText(label).width;
    const ty = Math.max(20, y1 * s);
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.roundRect(x1 * s, ty - 20, w + 14, 22, 11);
    ctx.fill();
    ctx.fillStyle = "#fff";
    ctx.fillText(label, x1 * s + 7, ty - 5);

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
  if (!state.showOverlay) return;
  const [px, py] = toImageCoords(evt);
  for (let i = state.findings.length - 1; i >= 0; i--) {
    const [x1, y1, x2, y2] = state.findings[i].box;
    if (Math.abs(px - x2) < 14 && Math.abs(py - y2) < 14) {
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
      <div class="f-head">
        <div class="f-ico ${f.class_name}">${CLASS_ICON[f.class_name] || "❓"}</div>
        <div class="f-title"><span class="f-label">${CLASS_LABEL[f.class_name] || f.class_name} Detected</span><small>Finding #${f.id} · model confidence ${Math.round(f.confidence * 100)}%</small></div>
        <span class="chip ${f.status} f-status">${f.status}</span>
      </div>
      <div class="conf-row"><span>Confidence</span><div class="conf-bar"><div class="conf-fill" style="width:${Math.round(f.confidence * 100)}%"></div></div><span>${Math.round(f.confidence * 100)}%</span></div>
      <div class="f-actions">
        <button class="btn primary" data-act="confirm">✓ Confirm</button>
        <button class="btn" data-act="dismiss">✕ Dismiss</button>
        <button class="btn" data-act="correct">✎ Correct</button>
      </div>
      <div class="f-correct" hidden>
        <label>Change Label
          <select data-f="label"><option>periapical_lesion</option><option>caries</option><option>not_a_finding</option></select>
        </label>
        <label>Clinician Confidence Level
          <input type="range" min="0" max="100" data-f="confidence" /> <span data-f="confidence-val"></span>
        </label>
        <label>Additional Notes (optional)
          <textarea data-f="notes" rows="2" placeholder="e.g. Lesion appears larger than detected…"></textarea>
        </label>
        <p class="muted">To move or resize the box, drag it directly on the image above.</p>
        <div class="save-row">
          <button class="btn primary" data-act="save-correct">Save Correction</button>
          <button class="btn" data-act="cancel-correct">Cancel</button>
        </div>
      </div>`;

    const panel = card.querySelector(".f-correct");
    const sel = card.querySelector('[data-f="label"]');
    sel.value = f.meta.label || f.class_name;
    const rng = card.querySelector('[data-f="confidence"]');
    rng.value = f.meta.confidence ?? Math.round(f.confidence * 100);
    card.querySelector('[data-f="confidence-val"]').textContent = rng.value + "%";
    card.querySelector('[data-f="notes"]').value = f.meta.notes || "";

    sel.addEventListener("change", () => {
      f.meta.label = sel.value;
      card.querySelector(".f-label").textContent = (CLASS_LABEL[sel.value] || sel.value) + " Detected";
    });
    rng.addEventListener("input", () => {
      f.meta.confidence = +rng.value;
      card.querySelector('[data-f="confidence-val"]').textContent = rng.value + "%";
    });
    card.querySelector('[data-f="notes"]').addEventListener("input", (e) => { f.meta.notes = e.target.value; });

    card.querySelector('[data-act="confirm"]').addEventListener("click", () => { f.status = "confirmed"; refresh(i); });
    card.querySelector('[data-act="dismiss"]').addEventListener("click", () => { f.status = "dismissed"; refresh(i); });
    card.querySelector('[data-act="correct"]').addEventListener("click", () => { panel.hidden = !panel.hidden; });
    card.querySelector('[data-act="save-correct"]').addEventListener("click", () => { f.status = "adjusted"; panel.hidden = true; refresh(i); });
    card.querySelector('[data-act="cancel-correct"]').addEventListener("click", () => { panel.hidden = true; });

    wrap.appendChild(card);
  });
}

function refresh(i) {
  updateCardStatus(i);
  draw();
}
function updateCardStatus(i) {
  const card = $("#finding-" + i);
  if (!card) return;
  const chip = card.querySelector(".f-status");
  chip.textContent = state.findings[i].status;
  chip.className = "chip " + state.findings[i].status + " f-status";
}

/* ---------- finish + report ---------- */
function reviewPayload() {
  return {
    image_name: state.imageName,
    thresholds: state.thresholds,
    findings: state.findings.map((f) => ({
      detection_id: f.id, class: f.class_name, model_confidence: f.confidence,
      box: f.box, status: f.status, ...f.meta,
    })),
  };
}

$("#finish-btn").addEventListener("click", async () => {
  const res = await fetch("/api/reviews", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(reviewPayload()),
  });
  if (!res.ok) { alert("Failed to save review."); return; }
  show("success");
});

function renderReport() {
  const rows = state.findings.map((f) => `
    <tr><td>Finding #${f.id}</td><td>${CLASS_LABEL[f.class_name] || f.class_name} — ${f.status} (${Math.round(f.confidence * 100)}% model, ${f.meta.confidence ?? Math.round(f.confidence * 100)}% clinician)</td></tr>
    <tr><td>Box (x1,y1,x2,y2)</td><td>[${f.box.join(", ")}]</td></tr>
    ${f.meta.notes ? `<tr><td>Notes</td><td>${f.meta.notes.replace(/</g, "&lt;")}</td></tr>` : ""}`
  ).join("");
  $("#report-body").innerHTML = `
    <p class="muted">Image: ${state.imageName} · Generated: ${new Date().toLocaleString()}</p>
    <table>${rows}</table>
    <p class="muted">AI assistance only — not a diagnosis. All findings require clinician confirmation.<br />
    Model trained on dental-xray-dataset by shreku (Roboflow Universe), CC BY 4.0.</p>`;
  $("#report-card").hidden = false;
}
$("#report-btn").addEventListener("click", renderReport);

$("#report-download").addEventListener("click", async () => {
  const res = await fetch("/api/report", {
    method: "POST", headers: { "Content-Type": "application/json" },
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
    (r.findings || []).forEach((f) => { total++; counts[f.status] = (counts[f.status] || 0) + 1; rc[f.status] = (rc[f.status] || 0) + 1; });
    tbody.insertAdjacentHTML("beforeend",
      `<tr><td>${r.timestamp || ""}</td><td>${r.image_name || ""}</td><td>${(r.findings || []).length}</td><td>${rc.confirmed}</td><td>${rc.dismissed}</td><td>${rc.adjusted}</td></tr>`);
  });
  [["Total Reviews", reviews.length], ["Total Findings", total], ["Confirmed", counts.confirmed], ["Adjusted", counts.adjusted]]
    .forEach(([k, v]) => metrics.insertAdjacentHTML("beforeend", `<div class="card metric"><b>${v}</b><span>${k}</span></div>`));
}

/* ---------- boot ---------- */
(async () => {
  const res = await fetch("/api/samples");
  const { samples } = await res.json();
  const sel = $("#sample-select");
  samples.forEach((n) => sel.insertAdjacentHTML("beforeend", `<option value="${n}">${n}</option>`));
  renderTracker("#tracker-home", 0);
})();