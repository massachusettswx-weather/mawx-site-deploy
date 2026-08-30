#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import shutil

APP=Path("site/app.js")
STAMP=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def die(m): raise RuntimeError(m)

if not APP.exists():
    die("Run from ~/models-site-deploy")

text=APP.read_text()
backup=APP.with_name(f"app.js.before_preload_all_{STAMP}")
shutil.copy2(APP,backup)
print("BACKUP:", backup)

marker="// BATCH 12 - BACKGROUND PRELOAD ALL SELECTED FORECAST HOURS"

if marker not in text:
    anchor="function preloadNearbyFrames"
    pos=text.find(anchor)
    if pos < 0:
        anchor="function preloadAroundFrame"
        pos=text.find(anchor)
    if pos < 0:
        die("Could not locate frame preload helper")

    helper=r"""
// ============================================================
// BATCH 12 - BACKGROUND PRELOAD ALL SELECTED FORECAST HOURS
// ============================================================
const FULL_RUN_PRELOAD_CONCURRENCY = 4;

let fullRunPreloadGeneration = 0;

async function preloadAllSelectedFrames() {
    const files = Array.isArray(state.selectionFiles)
        ? [...state.selectionFiles]
        : [];

    if (!files.length) {
        return;
    }

    const generation = ++fullRunPreloadGeneration;
    let cursor = 0;

    async function worker() {
        while (
            generation === fullRunPreloadGeneration
            &&
            cursor < files.length
        ) {
            const index = cursor++;
            const file = files[index];
            const url = frameUrl(file);

            if (!url) {
                continue;
            }

            const cached = frameImageCache.get(url);

            if (
                cached
                &&
                cached.complete
                &&
                cached.naturalWidth > 0
            ) {
                continue;
            }

            await new Promise((resolve) => {
                const image = preloadFrame(file);

                if (!image) {
                    resolve();
                    return;
                }

                if (
                    image.complete
                    &&
                    image.naturalWidth > 0
                ) {
                    resolve();
                    return;
                }

                const done = () => resolve();

                image.addEventListener(
                    "load",
                    done,
                    {once: true},
                );

                image.addEventListener(
                    "error",
                    done,
                    {once: true},
                );
            });
        }
    }

    const workerCount = Math.min(
        FULL_RUN_PRELOAD_CONCURRENCY,
        files.length,
    );

    await Promise.all(
        Array.from(
            {length: workerCount},
            () => worker(),
        ),
    );
}

function scheduleFullRunPreload() {
    fullRunPreloadGeneration += 1;

    window.setTimeout(
        () => {
            preloadAllSelectedFrames().catch(
                (error) => {
                    console.debug(
                        "Full-run preload stopped:",
                        error,
                    );
                },
            );
        },
        350,
    );
}


"""
    text=text[:pos]+helper+text[pos:]

needle="    renderHourGrid();"
if needle not in text:
    die("renderHourGrid() anchor missing")

if "scheduleFullRunPreload();" not in text:
    text=text.replace(
        needle,
        needle+"\n\n    scheduleFullRunPreload();",
        1,
    )

APP.write_text(text)

final=APP.read_text()
checks={
    "all-hour preload helper":"async function preloadAllSelectedFrames" in final,
    "bounded concurrency":"FULL_RUN_PRELOAD_CONCURRENCY = 4" in final,
    "selection cancellation":"fullRunPreloadGeneration" in final,
    "browser warm-up scheduled":"scheduleFullRunPreload();" in final,
    "existing cache retained":"FRAME_CACHE_LIMIT" in final,
}
for name,ok in checks.items():
    print(f"{name}: {'PASS' if ok else 'FAIL'}")
if not all(checks.values()):
    die("Batch 12 verification failed")

print()
print("MASSACHUSETTSWX BATCH 12: PASS")
print("Preload scope: all hours for selected model/product/region")
print("Concurrency: 4")
print("No deployment performed.")
