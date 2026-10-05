"""One-shot patch: inline no-findings card + 0.50 default thresholds (sliders still allow lower)."""
from pathlib import Path

STATIC = Path("static")
app_js = (STATIC / "js" / "app.js").read_text(encoding="utf-8")
index_html = (STATIC / "index.html").read_text(encoding="utf-8")
css = (STATIC / "css" / "styles.css").read_text(encoding="utf-8")
inference = Path("meckel/ui/inference.py").read_text(encoding="utf-8")
changed = []

# ---------- app.js: kill the browser alert, show inline card ----------
if 'alert("No findings above the current thresholds. Lower them and re-analyze.");' in app_js:
    app_js = app_js.replace(
        '''        $("#analyze-card").hidden = false;
        alert("No findings above the current thresholds. Lower them and re-analyze.");
        return;''',
        '''        $("#analyze-card").hidden = false;
        $("#no-findings").hidden = false;
        $("#no-findings").scrollIntoView({ behavior: "smooth", block: "center" });
        return;''')
    changed.append("app.js: alert replaced with inline card")

# ---------- app.js: defaults 0.50 ----------
if "thresholds: { periapical_lesion: 0.30, caries: 0.40 }," in app_js:
    app_js = app_js.replace(
        "thresholds: { periapical_lesion: 0.30, caries: 0.40 },",
        "thresholds: { periapical_lesion: 0.50, caries: 0.50 },")
    changed.append("app.js: state defaults -> 0.50")

# ---------- app.js: hide the card on reset / new image / new analyze ----------
if '$("#no-findings").hidden = true;' not in app_js:
    app_js = app_js.replace(
        '  $("#report-card").hidden = true;\n  stopTips();',
        '  $("#report-card").hidden = true;\n  $("#no-findings").hidden = true;\n  stopTips();')
    app_js = app_js.replace(
        'function setImage(src, name) {\n  state.imageSrc = src; state.imageName = name; state.stage = 0;',
        'function setImage(src, name) {\n  state.imageSrc = src; state.imageName = name; state.stage = 0;\n  $("#no-findings").hidden = true;')
    app_js = app_js.replace(
        '''$("#analyze-btn").addEventListener("click", async () => {
  $("#analyze-card").hidden = true;
  $("#analyzing-card").hidden = false;''',
        '''$("#analyze-btn").addEventListener("click", async () => {
  $("#analyze-card").hidden = true;
  $("#analyzing-card").hidden = false;
  $("#no-findings").hidden = true;''')
    changed.append("app.js: card hidden on reset/new image/analyze")

# ---------- index.html: inline no-findings card ----------
if 'id="no-findings"' not in index_html:
    index_html = index_html.replace(
        '<div class="card error-card" id="format-error" hidden>',
        '''<div class="card" id="no-findings" hidden>
        <div class="banner info" style="margin-top:0">
          <span class="b-ico"><i data-lucide="search-x"></i></span>
          <div>
            <strong>No AI findings detected</strong><br />
            <span class="muted">Meckel did not identify any findings above the current detection threshold. Clinical review is still recommended.</span>
          </div>
        </div>
        <p class="muted">If you expect a finding, adjust the per-class thresholds above and press <b>Analyze Radiograph</b> again.</p>
      </div>

      <div class="card error-card" id="format-error" hidden>''')
    changed.append("index.html: no-findings card inserted")

# ---------- index.html: sliders default 0.50, min stays 0.05 ----------
if 'value="0.30"' in index_html or 'value="0.40"' in index_html:
    index_html = index_html.replace(
        '<label>Periapical threshold <input type="range" id="pal-thr" min="0.05" max="0.9" step="0.05" value="0.30" /><span class="chip neutral" id="pal-thr-val">0.30</span></label>',
        '<label>Periapical threshold (default 0.50) <input type="range" id="pal-thr" min="0.05" max="0.90" step="0.05" value="0.50" /><span class="chip neutral" id="pal-thr-val">0.50</span></label>')
    index_html = index_html.replace(
        '<label>Caries threshold <input type="range" id="car-thr" min="0.05" max="0.9" step="0.05" value="0.40" /><span class="chip neutral" id="car-thr-val">0.40</span></label>',
        '<label>Caries threshold (default 0.50) <input type="range" id="car-thr" min="0.05" max="0.90" step="0.05" value="0.50" /><span class="chip neutral" id="car-thr-val">0.50</span></label>')
    changed.append("index.html: slider defaults -> 0.50 (min unchanged)")

# ---------- styles.css: info banner colors ----------
if ".banner.info" not in css:
    css += '''
.banner.info { background: #EAF3FE; border: 1px solid #BBD8F5; color: #0B3B66; }
.banner.info .b-ico { color: var(--primary); }
'''
    changed.append("styles.css: banner.info colors")

# ---------- inference.py: backend defaults 0.50 ----------
if '"periapical_lesion": 0.30,' in inference:
    inference = inference.replace(
        'DEFAULT_THRESHOLDS = {\n    "periapical_lesion": 0.30,\n    "caries": 0.40,\n}',
        'DEFAULT_THRESHOLDS = {\n    "periapical_lesion": 0.50,\n    "caries": 0.50,\n}')
    changed.append("inference.py: backend defaults -> 0.50")

(STATIC / "js" / "app.js").write_text(app_js, encoding="utf-8")
(STATIC / "index.html").write_text(index_html, encoding="utf-8")
(STATIC / "css" / "styles.css").write_text(css, encoding="utf-8")
Path("meckel/ui/inference.py").write_text(inference, encoding="utf-8")

if changed:
    print("Patched:")
    for c in changed:
        print(" -", c)
else:
    print("Nothing to patch - files already up to date.")