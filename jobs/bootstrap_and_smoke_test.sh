#!/usr/bin/env bash
#
# One-shot setup + probe + smoke test for the polar vortex job.
#
# Run this on the machine/container that will actually execute the
# job (it needs real internet access to ECMWF's ARCO store and GCS
# -- this chat's sandbox does not have that).
#
# Usage:
#
#   CDS_API_KEY="your-key-here" bash jobs/bootstrap_and_smoke_test.sh
#
# What it does:
#   1. Installs jobs/requirements.txt
#   2. Runs --probe to confirm the ARCO pressure-level schema and,
#      critically, how fresh the data actually is
#   3. Runs a small, cheap backfill (2024-2025 only) as a smoke test
#   4. Lists what landed in the GCS bucket and prints latest.json
#
# NOTE: unlike the classic cdsapi Toolbox client, this does NOT use
# a ~/.cdsapirc file. CDS_API_KEY is read directly as an environment
# variable and used as an ARCO Bearer token (same convention as
# ~/era5/era5.py). Export it in your shell profile if you want it to
# persist across sessions.
#
# After this succeeds, run the full backfill:
#
#   python jobs/update_polar_vortex.py --backfill

set -euo pipefail

if [[ -z "${CDS_API_KEY:-}" ]]; then
    echo "ERROR: set CDS_API_KEY first, e.g.:"
    echo '  CDS_API_KEY="your-key-here" bash jobs/bootstrap_and_smoke_test.sh'
    exit 1
fi

echo "==> Installing job dependencies"
pip install -r jobs/requirements.txt

echo "==> Probing the ARCO pressure-level store"
python jobs/update_polar_vortex.py --probe

echo
echo "==> Look at the output above -- specifically the wind variable name,"
echo "    level coordinate, and MOST RECENT available time. If --probe"
echo "    failed to open any candidate URL, stop here and send me the"
echo "    error output before continuing."
echo

echo "==> Running smoke-test backfill (2024-2025 only)"
python jobs/update_polar_vortex.py --backfill --start-year 2024 --end-year 2025

echo "==> Checking Cloud Storage output"
BUCKET="${WEATHER_STORAGE_BUCKET:-massachusettswx-nwp-project}"
gsutil ls "gs://${BUCKET}/analysis/polar_vortex/10hpa_60n_zonal_wind/"

echo "==> latest.json contents:"
gsutil cat "gs://${BUCKET}/analysis/polar_vortex/10hpa_60n_zonal_wind/latest.json"

echo
echo "==> Smoke test complete. If everything above looks right, run the full backfill:"
echo "    python jobs/update_polar_vortex.py --backfill"
