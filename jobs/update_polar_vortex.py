#!/usr/bin/env python3
"""
Entrypoint for the ERA5 Current Analysis / Polar Vortex ingestion job.

This script is intentionally thin. All real logic (CDS retrieval,
storage format, stats, state tracking) lives in
shared/era5_polar_vortex.py, consistent with the rest of the
MassachusettsWx shared pipeline architecture -- this is a CLI
wrapper, not a standalone script.

This job is NOT part of the Cloud Run web service (models_server.py)
and is not invoked by it. It is meant to be run:

  - once, manually, for the historical backfill
  - on a daily schedule (Cloud Scheduler + Cloud Run Job, a cron'd
    VM, GitHub Actions, etc. -- whatever already runs the GFS/IFS/
    AIFS pipelines in this deployment) for the incremental update

Retrieval uses ECMWF's ARCO (Analysis-Ready, Cloud-Optimized) Zarr
store over HTTPS -- the same mechanism the ~/era5 sandbox scripts
already use for surface fields -- NOT the classic cdsapi Toolbox
client. That means credentials are a single environment variable,
not a ~/.cdsapirc file.

Requires:
  - CDS_API_KEY environment variable (used as an ARCO Bearer token;
    same variable name ~/era5/era5.py already expects)
  - Google Cloud Storage credentials with write access to the
    shared bucket (same as the rest of the pipeline)
  - The dependencies in jobs/requirements.txt -- kept separate from
    the lightweight requirements.txt used by the Cloud Run web
    service, which does not need xarray/zarr at all

The exact ARCO schema for pressure-level data (dataset URL, variable
name, level coordinate) was not confirmed when this was written --
run --probe first.

Usage:

    # Check the ARCO pressure-level store's actual schema and data
    # freshness before running anything else
    python jobs/update_polar_vortex.py --probe

    # One-time historical backfill, 1940 through the current year
    python jobs/update_polar_vortex.py --backfill

    # Backfill a specific range (e.g. re-running after a bug fix)
    python jobs/update_polar_vortex.py --backfill \\
        --start-year 1940 --end-year 2010 --overwrite

    # Daily incremental update (also refreshes recent ERA5T days,
    # if the store carries them -- see --probe)
    python jobs/update_polar_vortex.py --daily

    # Rebuild the frontend bundle + latest.json from what's already
    # stored, without fetching anything new
    python jobs/update_polar_vortex.py --rebuild-bundle
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running this script directly from any working directory --
# Python only puts jobs/ itself on sys.path by default, not the repo
# root where `shared` actually lives.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.era5_polar_vortex import (
    ERA5_START_DATE,
    probe_arco_pressure_levels,
    rebuild_bundle,
    recompute_and_publish_latest,
    run_backfill,
    run_daily_update,
)


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Update the ERA5 polar vortex "
            "(10 hPa, 60N zonal-mean wind) archive."
        ),
    )

    parser.add_argument(
        "--probe",
        action="store_true",
        help=(
            "Open the ARCO pressure-level store and print its "
            "schema (variable names, level coordinate, data "
            "freshness) without fetching or storing anything. "
            "Run this first."
        ),
    )

    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Run the one-time historical backfill.",
    )

    parser.add_argument(
        "--start-year",
        type=int,
        default=ERA5_START_DATE.year,
        help="First year to backfill (default: 1940).",
    )

    parser.add_argument(
        "--end-year",
        type=int,
        default=None,
        help="Last year to backfill (default: current year).",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=(
            "Re-fetch years even if already stored "
            "(default: only fetch missing/current years)."
        ),
    )

    parser.add_argument(
        "--daily",
        action="store_true",
        help="Run the incremental daily update.",
    )

    parser.add_argument(
        "--rebuild-bundle",
        action="store_true",
        help=(
            "Rebuild the combined frontend bundle and "
            "latest.json from already-stored data only, "
            "without contacting CDS."
        ),
    )

    args = parser.parse_args()

    ran_something = False

    if args.probe:

        probe_arco_pressure_levels()

        ran_something = True

    if args.backfill:

        run_backfill(
            start_year=args.start_year,
            end_year=args.end_year,
            overwrite=args.overwrite,
        )

        ran_something = True

    if args.daily:

        run_daily_update()

        ran_something = True

    if args.rebuild_bundle:

        bundle = rebuild_bundle()

        recompute_and_publish_latest(
            bundle
        )

        ran_something = True

    if not ran_something:

        parser.print_help()

        return 1

    return 0


if __name__ == "__main__":

    sys.exit(
        main()
    )
