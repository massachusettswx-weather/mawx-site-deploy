#!/usr/bin/env bash
set -euo pipefail

cd "$HOME/model-cloudrun"

echo
echo "============================================================"
echo " MASSACHUSETTSWX CORE ARCHITECTURE CHECK"
echo "============================================================"

python3 -m py_compile   cloud_job.py   shared/models.py   shared/operational.py   shared/product_cadence.py   shared/resume.py   shared/runner.py   gfs/run.py   ifs/run.py   aifs/run.py

echo
echo "Compile: PASS"

echo
echo "===== MODEL ARCHITECTURE ====="

for MODEL in gfs ifs aifs; do

  echo
  echo "----- ${MODEL^^} -----"

  RESUME=$(
    grep -c       'get_remaining_forecast_hours'       "$MODEL/run.py"       || true
  )

  GATES=$(
    grep -c       'will NOT be published'       "$MODEL/run.py"       || true
  )

  FRONTIER=$(
    grep -c       'stopping cleanly at upstream frontier'       "$MODEL/run.py"       || true
  )

  STATUS=$(
    grep -c       'waiting_upstream'       "$MODEL/run.py"       || true
  )

  echo "resume references:   $RESUME"
  echo "publication gates:   $GATES"
  echo "frontier handling:   $FRONTIER"
  echo "runtime status:      $STATUS"

done

echo
echo "===== PRODUCT CADENCE ====="

python3 - <<'PY2'
from shared.product_cadence import (
    should_render_product,
)

checks = [
    ("gfs", "t2m", 1),
    ("gfs", "h5_vort", 1),
    ("gfs", "h5_vort", 3),

    ("ifs", "t2m", 1),
    ("ifs", "h5_vort", 1),
    ("ifs", "h5_vort", 3),

    ("aifs", "h5_vort", 6),
]

for model, product, hour in checks:

    print(
        f"{model:4s} "
        f"{product:20s} "
        f"f{hour:03d} "
        f"render="
        f"{should_render_product(model=model, product=product, forecast_hour=hour)}"
    )
PY2

echo
echo "Architecture check complete."
