const $ = (s) => document.querySelector(s);
const CLASS_COLORS = { periapical_lesion: "#FF3B30", caries: "#FF9500" };
const OTHER = { periapical_lesion: "caries", caries: "periapical_lesion" };

let queue = [], reviewed = {}, unit = null, statuses = [], history = [], rects = [];

const canvas = $("#canvas");
const ctx = canvas.getContext("2d");
let img = new Image();

/* ---------- help modal ---------- */
function openHelp() { $("#help-overlay").hidden = false; }
function closeHelp() {
  $("#help-overlay").hidden = true;
  localStorage.setItem("curation-help-seen", "1");
}

async function boot() {
  $("#help-btn").addEventListener("click", openHelp);
  $("#help-close").addEventListener("click", closeHelp);
  if (!localStorage.getItem("curation-help-seen")) openHelp();

  canvas.addEventListener("dragstart", (e) => e.preventDefault());
  canvas.addEventListener("click", onCanvasClick);
  window.addEventListener("keydown", onKey);
  $("#next").addEventListener("click", next);
  $("#prev").addEventListener("click", prev);
  $("#filter").addEventListener("change", loadQueue);

  await loadQueue();
}

async function loadQueue() {
  const filter = $("#filter").value;
  const q = await (await fetch("/capi/queue?filter=" + filter)).json();
  queue = q.keys;
  reviewed = q.reviewed;
  const first = queue.findIndex((k) => !reviewed[k]);
  await loadUnit(queue[first < 0 ? 0 : first]);
}

async function loadUnit(key) {
  if (!key) return;
  unit = await (await fetch("/capi/unit?key=" + encodeURIComponent(key))).json();
  statuses = unit.boxes.map((b) => {
    const a = unit.actions[String(b.idx)];
    if (a === "drop") return "drop";
    if (a && a.startsWith("relabel:")) return "relabel";
    return "keep";
  });
  $("#filename").textContent = unit.key + (unit.done ? " (re-review)" : "");
  img = new Image();
  img.onload = draw;
  img.src = "/capi/image/" + unit.split + "/" + encodeURIComponent(unit.file);
  renderList();
}

function scale() { return canvas.width / unit.width; }

function draw() {
  rects = [];
  const maxW = Math.min(1000, $("#canvas-wrap").clientWidth - 4);
  const s0 = Math.min(1, maxW / unit.width);
  canvas.width = Math.round(unit.width * s0);
  canvas.height = Math.round(unit.height * s0);
  const s = scale();
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

  unit.boxes.forEach((b, i) => {
    const [xc, yc, w, h] = b.box;
    const x1 = (xc - w / 2) * unit.width * s, y1 = (yc - h / 2) * unit.height * s;
    const bw = w * unit.width * s, bh = h * unit.height * s;
    rects[i] = [x1, y1, bw, bh];
    const st = statuses[i];
    const color = st === "drop" ? "#8E8E93" : st === "relabel" ? CLASS_COLORS[OTHER[b.class_name]] : CLASS_COLORS[b.class_name];

    ctx.strokeStyle = color;
    ctx.lineWidth = 3;
    ctx.setLineDash(st === "relabel" ? [8, 5] : []);
    ctx.strokeRect(x1, y1, bw, bh);
    ctx.setLineDash([]);

    if (st === "drop") {
      ctx.beginPath();
      ctx.moveTo(x1, y1); ctx.lineTo(x1 + bw, y1 + bh);
      ctx.moveTo(x1 + bw, y1); ctx.lineTo(x1, y1 + bh);
      ctx.stroke();
    }

    const label = `#${b.idx} ${b.class_name}${st !== "keep" ? " [" + st.toUpperCase() + "]" : ""}`;
    ctx.font = "600 13px Segoe UI, sans-serif";
    const tw = ctx.measureText(label).width;
    ctx.fillStyle = color;
    ctx.fillRect(x1, Math.max(0, y1 - 18), tw + 10, 18);
    ctx.fillStyle = "#fff";
    ctx.fillText(label, x1 + 5, Math.max(13, y1 - 5));
  });
}

function onCanvasClick(e) {
  if (!unit) return;
  const r = canvas.getBoundingClientRect();
  const x = e.clientX - r.left, y = e.clientY - r.top;
  for (let i = unit.boxes.length - 1; i >= 0; i--) {
    const [bx, by, bw, bh] = rects[i] || [0, 0, 0, 0];
    if (x >= bx && x <= bx + bw && y >= by && y <= by + bh) { cycle(i); return; }
  }
}

function renderList() {
  const wrap = $("#boxlist");
  wrap.innerHTML = "";
  unit.boxes.forEach((b, i) => {
    const row = document.createElement("div");
    row.className = "boxrow";
    row.innerHTML = `
      <span class="sw" style="background:${CLASS_COLORS[b.class_name]}"></span>
      <span class="name">#${b.idx} ${b.class_name}</span>
      <span class="chip ${statuses[i]}">${statuses[i]}</span>`;
    row.addEventListener("click", () => cycle(i));
    wrap.appendChild(row);
  });
  fetch("/capi/meta").then((r) => r.json()).then((m) => {
    if ($("#filter").value === "pal") {
      $("#progress").textContent = `${m.pal_reviewed}/${m.pal_total} in queue · ${m.reviewed}/${m.total} overall`;
    } else {
      $("#progress").textContent = `${m.reviewed}/${m.total} reviewed`;
    }
  });
}

function cycle(i) {
  statuses[i] = statuses[i] === "keep" ? "drop" : statuses[i] === "drop" ? "relabel" : "keep";
  draw();
  renderList();
}

async function next() {
  const actions = [];
  unit.boxes.forEach((b, i) => {
    if (statuses[i] === "drop") actions.push({ box: b.idx, action: "drop" });
    if (statuses[i] === "relabel") actions.push({ box: b.idx, action: "relabel:" + OTHER[b.class_name] });
  });
  const res = await (await fetch("/capi/commit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key: unit.key, actions }),
  })).json();
  reviewed[unit.key] = true;
  history.push(unit.key);
  renderList();
  const pos = queue.indexOf(unit.key);
  let nxt = null;
  for (let i = pos + 1; i < queue.length; i++) if (!reviewed[queue[i]]) { nxt = queue[i]; break; }
  if (!nxt) for (let i = 0; i < pos; i++) if (!reviewed[queue[i]]) { nxt = queue[i]; break; }
  if (nxt) loadUnit(nxt);
  else alert("Queue complete for this filter. 🎉");
}

function prev() {
  const k = history.pop();
  if (k) loadUnit(k);
}

function onKey(e) {
  if (!unit) return;
  if (e.key === "ArrowRight" || e.key === " ") { e.preventDefault(); next(); }
  if (e.key === "ArrowLeft") { e.preventDefault(); prev(); }
  const n = parseInt(e.key, 10);
  if (!isNaN(n) && n >= 1 && n <= unit.boxes.length) cycle(n - 1);
}

boot();