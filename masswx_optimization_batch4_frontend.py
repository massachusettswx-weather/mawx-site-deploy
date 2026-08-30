#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import re, shutil
ROOT=Path.cwd(); APP=ROOT/'site/app.js'; STAMP=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
def die(m): raise RuntimeError(m)
if not APP.exists(): die('Run from ~/models-site-deploy (site/app.js not found)')
text=APP.read_text(); backup=APP.with_name(f'app.js.before_batch4_{STAMP}'); shutil.copy2(APP,backup); print('BACKUP:',backup)
marker='function renderCurrentFrame() {'
if marker not in text: die('renderCurrentFrame() not found')
if 'const FRAME_PRELOAD_RADIUS' not in text:
 layer='''
// FAST FRAME CACHE / SCRUBBING
const FRAME_PRELOAD_RADIUS = 4;
const FRAME_CACHE_LIMIT = 24;
const frameImageCache = new Map();
let frameRenderToken = 0;
function frameUrl(file) { return file && file.url ? String(file.url) : ""; }
function touchFrameCache(url, image) {
    if (!url || !image) return;
    if (frameImageCache.has(url)) frameImageCache.delete(url);
    frameImageCache.set(url, image);
    while (frameImageCache.size > FRAME_CACHE_LIMIT) {
        const oldest = frameImageCache.keys().next().value;
        frameImageCache.delete(oldest);
    }
}
function preloadFrame(file) {
    const url = frameUrl(file);
    if (!url) return null;
    const existing = frameImageCache.get(url);
    if (existing) { touchFrameCache(url, existing); return existing; }
    const image = new Image(); image.decoding = "async"; image.src = url;
    image.onload = () => touchFrameCache(url, image);
    image.onerror = () => frameImageCache.delete(url);
    touchFrameCache(url, image); return image;
}
function preloadAroundFrame(index, direction = 1) {
    const files = state.selectionFiles || []; if (!files.length) return;
    const order = [];
    for (let d = 1; d <= FRAME_PRELOAD_RADIUS; d += 1) {
        const a = index + (d * direction), b = index - (d * direction);
        if (a >= 0 && a < files.length) order.push(a);
        if (b >= 0 && b < files.length) order.push(b);
    }
    for (const i of order) preloadFrame(files[i]);
}
function displayFrameImmediately(current, direction = 1) {
    const url = frameUrl(current); if (!url) return;
    const token = ++frameRenderToken; const cached = preloadFrame(current);
    loadingText.style.display = "none";
    const commit = () => {
        if (token !== frameRenderToken) return;
        mapImage.src = url; mapImage.style.display = "block";
        preloadAroundFrame(state.frameIndex, direction);
    };
    if (cached && cached.complete && cached.naturalWidth > 0) commit();
    else if (cached) {
        cached.addEventListener("load", commit, { once: true });
        cached.addEventListener("error", () => { if (token === frameRenderToken) console.debug("Forecast frame unavailable:", url); }, { once: true });
    }
}

'''
 text=text.replace(marker,layer+marker,1)
start=text.find(marker); end=text.find('\nfunction ',start+10); end=len(text) if end<0 else end
func=text[start:end]
pattern='\n\s*loadingText\.style\.display\s*=\s*"flex";.*?mapImage\.src\s*=\s*addCacheBuster\(\s*current\.url\s*\);'
pat=re.compile(pattern,re.S)
if pat.search(func):
 repl='\n\n    const previousIndex = Number(mapImage.dataset.frameIndex ?? state.frameIndex);\n    const direction = state.frameIndex >= previousIndex ? 1 : -1;\n    mapImage.dataset.frameIndex = String(state.frameIndex);\n    displayFrameImmediately(current, direction);'
 func=pat.sub(repl,func,count=1)
elif 'displayFrameImmediately(current' not in func: die('Could not safely locate legacy Loading map block')
text=text[:start]+func+text[end:]; APP.write_text(text)
final=APP.read_text(); checks={'bounded cache':'FRAME_CACHE_LIMIT = 24' in final,'adjacent preload':'preloadAroundFrame' in final,'instant display':'displayFrameImmediately(current' in final,'immutable frame URL':'mapImage.src = url' in final,'metadata cache busting':'function addCacheBuster' in final}
for k,v in checks.items(): print(f"{k}: {'PASS' if v else 'FAIL'}")
if not all(checks.values()): die('Batch 4 verification failed')
print('\nMASSACHUSETTSWX FRONTEND BATCH 4: PASS'); print('No deployment performed.')
