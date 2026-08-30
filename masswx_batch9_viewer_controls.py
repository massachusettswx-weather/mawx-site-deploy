#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import shutil, sys
STAMP=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
def die(m): raise RuntimeError(m)
def backup(p):
    d=p.with_name(p.name+f".before_batch9_{STAMP}"); shutil.copy2(p,d); print(f"BACKUP: {p} -> {d}")
def patch_html(p):
    text=p.read_text(); old=text
    s=text.find('<section class="forecast-scrubber')
    if s<0: s=text.find('<div class="forecast-scrubber')
    if s<0: die("Existing forecast scrubber block not found")
    tag="section" if text[s:s+9].startswith("<section") else "div"
    close=f"</{tag}>"; e=text.find(close,s)
    if e<0: die("Could not close scrubber block")
    e+=len(close); scrubber=text[s:e]; text=text[:s]+text[e:]
    m=text.find('<section class="map-wrapper">')
    if m<0: die("map-wrapper not found")
    text=text[:m]+scrubber+"\n\n            "+text[m:]
    if 'id="runGifButton"' not in text:
        top=text.find('<section class="viewer-topbar">'); end=text.find("</section>",top)
        if top<0 or end<0: die("viewer-topbar not found")
        controls="\n                <div class=\"export-buttons\">\n                    <button id=\"runGifButton\" type=\"button\" title=\"Animate the loaded run in your browser\">Run GIF</button>\n                    <button id=\"trendGifButton\" type=\"button\" title=\"Trend animation uses multiple model cycles\">Trend GIF</button>\n                </div>\n"
        text=text[:end]+controls+text[end:]
    if text!=old: backup(p); p.write_text(text); print(f"{p}: UPDATED")
def patch_js(p):
    text=p.read_text(); old=text; pos=text.find("const mapImage =")
    if pos<0: die("mapImage declaration not found")
    if "const runGifButton =" not in text:
        block="const runGifButton =\n    document.getElementById(\"runGifButton\");\n\nconst trendGifButton =\n    document.getElementById(\"trendGifButton\");\n\n\n"
        text=text[:pos]+block+text[pos:]
    marker="// BATCH 9 - LOW-COST ANIMATION CONTROLS"
    if marker not in text:
        pos=text.find("modelSelect.addEventListener(")
        if pos<0: die("event-listener anchor not found")
        helper="// ============================================================\n// BATCH 9 - LOW-COST ANIMATION CONTROLS\n// ============================================================\n\nfunction startRunGifPreview() {\n    if (!state.selectionFiles || state.selectionFiles.length === 0) return;\n    for (const file of state.selectionFiles) preloadFrame(file);\n    state.frameIndex = 0;\n    renderCurrentFrame();\n    if (!playTimer) startAnimation();\n}\n\nfunction trendGifPreview() {\n    window.alert(\"Trend GIF will use cached prior model cycles after the multi-cycle archive is activated.\");\n}\n\nif (runGifButton) runGifButton.addEventListener(\"click\", startRunGifPreview);\nif (trendGifButton) trendGifButton.addEventListener(\"click\", trendGifPreview);\n\n\n"
        text=text[:pos]+helper+text[pos:]
    if text!=old: backup(p); p.write_text(text); print(f"{p}: UPDATED")
def patch_css(p):
    text=p.read_text(); old=text
    if "/* BATCH 9 - TOP SCRUBBER + ANIMATION CONTROLS */" not in text:
        text+="\n\n/* BATCH 9 - TOP SCRUBBER + ANIMATION CONTROLS */\n.forecast-scrubber { width:100%; margin:8px 0 10px; padding:10px 12px; background:var(--panel); border:1px solid var(--border); border-radius:7px; }\n.forecast-scrubber input[type=\"range\"] { width:100%; }\n.export-buttons { display:flex; gap:8px; margin-left:auto; }\n#runGifButton, #trendGifButton { white-space:nowrap; }\n@media (max-width:800px) { .export-buttons { width:100%; margin-left:0; } #runGifButton, #trendGifButton { flex:1; } }\n"
    if text!=old: backup(p); p.write_text(text); print(f"{p}: UPDATED")
def main():
    html=Path("site/index.html"); js=Path("site/app.js"); css=Path("site/styles.css")
    for p in (html,js,css):
        if not p.exists(): die(f"Missing {p}; run from ~/models-site-deploy")
    print("===== BATCH 9: TOP SCRUBBER + LOW-COST GIF UI =====")
    patch_html(html); patch_js(js); patch_css(css)
    h=html.read_text(); j=js.read_text(); c=css.read_text()
    checks={"Scrubber exists":'id="forecastScrubber"' in h,"Scrubber above map":h.find('id="forecastScrubber"')<h.find('class="map-wrapper"'),"Run GIF control":'id="runGifButton"' in h and "startRunGifPreview" in j,"Trend GIF control":'id="trendGifButton"' in h and "trendGifPreview" in j,"Frame cache reused":"preloadFrame(file)" in j,"Responsive controls":".export-buttons" in c}
    print("\n===== VERIFICATION =====")
    for k,v in checks.items(): print(f"{k}: {'PASS' if v else 'FAIL'}")
    if not all(checks.values()): die([k for k,v in checks.items() if not v])
    print("\nMASSACHUSETTSWX BATCH 9: PASS")
    print("Run GIF uses browser-cached forecast frames; no server render.")
    print("Trend GIF control staged for multi-cycle archive wiring.")
    print("NO DEPLOYMENT / NO CLOUD RUN / NO SERVER-SIDE GIF COST")
if __name__=="__main__":
    try: main()
    except Exception as e: print(f"\nBATCH 9 FAILED: {e}",file=sys.stderr); sys.exit(1)
