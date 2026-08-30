from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
import mimetypes
import time

from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    request,
    send_from_directory,
)

from shared.storage import (
    get_bucket,
    get_bucket_name,
)

# ============================================================
# ERA5 DISABLED IN OPERATIONAL CLOUD RUN
#
# ERA5 will be deployed later as its own archive/reanalysis page.
# The operational viewer currently serves GFS / IFS / AIFS only.
# ============================================================

ERA5_ENABLED = False



# ============================================================
# PATHS
# ============================================================

ROOT_DIR = Path(
    __file__
).resolve().parent


WEATHERNEXT_DIR = (
    ROOT_DIR
    / "weathernext"
)


SITE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    / "site"
)


OUTPUT_DIR = (
    WEATHERNEXT_DIR
    / "output"
)


PREVIEW_DIR = (
    WEATHERNEXT_DIR
    / "preview"
)


PRODUCTS_DIR = (
    WEATHERNEXT_DIR
    / "products"
)


ERA5_DIR = (
    ROOT_DIR
    / "era5"
)


ERA5_CACHE_DIR = (
    ERA5_DIR
    / "static"
    / "cache"
)


ERA5_CACHE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# APP
# ============================================================

app = Flask(
    __name__,
    static_folder=None,
)


# ============================================================
# ERA5 REGIONS
# ============================================================
#
# west, east, south, north
#
# These are retrieval bounds.
# ============================================================

ERA5_REGIONS = {

    "conus": {

        "name":
            "CONUS",

        "fetch": (
            -132,
            -60,
            18,
            56,
        ),

    },


    "northeast": {

        "name":
            "Northeast",

        "fetch": (
            -86,
            -61,
            33,
            51,
        ),

    },


    "new_england": {

        "name":
            "New England",

        "fetch": (
            -76,
            -64,
            39,
            49,
        ),

    },


    "mid_atlantic": {

        "name":
            "Mid-Atlantic",

        "fetch": (
            -84,
            -70,
            34,
            44,
        ),

    },


    "southeast": {

        "name":
            "Southeast",

        "fetch": (
            -92,
            -73,
            23,
            38,
        ),

    },


    "great_lakes": {

        "name":
            "Great Lakes",

        "fetch": (
            -94,
            -73,
            39,
            51,
        ),

    },


    "midwest": {

        "name":
            "Midwest",

        "fetch": (
            -104,
            -78,
            34,
            51,
        ),

    },


    "north_america": {

        "name":
            "North America",

        "fetch": (
            -175,
            -42,
            2,
            78,
        ),

    },

}


# ============================================================
# ERA5 PRODUCT CATALOG
# ============================================================

ERA5_PRODUCTS = {

    "t2m": {

        "name":
            "2-m Temperature",

        "enabled":
            True,

    },


    "mslp": {

        "name":
            "Mean Sea-Level Pressure",

        "enabled":
            False,

    },


    "wind10m": {

        "name":
            "10-m Wind",

        "enabled":
            False,

    },


    "cape": {

        "name":
            "CAPE",

        "enabled":
            False,

    },


    "tcwv": {

        "name":
            "Precipitable Water",

        "enabled":
            False,

    },

}


# ============================================================
# ERA5 PREFETCH
# ============================================================

prefetch_pool = ThreadPoolExecutor(
    max_workers=4
)


def shift_timestamp(
    timestamp,
    hours,
):

    dt = datetime.strptime(
        timestamp,
        "%Y-%m-%dT%H:%M",
    )


    dt += timedelta(
        hours=hours
    )


    return dt.strftime(
        "%Y-%m-%dT%H:%M"
    )


def prefetch_t2m(
    timestamp,
    region,
):

    try:

        get_t2m(
            timestamp,
            region,
        )


        print(
            "ERA5 PREFETCH COMPLETE:",
            timestamp,
        )


    except Exception as exc:

        print(
            "ERA5 PREFETCH FAILED:",
            timestamp,
            exc,
        )


def schedule_prefetch(
    timestamp,
    region,
):

    for offset in (
        -3,
        -2,
        -1,
        1,
        2,
        3,
    ):

        neighbor = shift_timestamp(
            timestamp,
            offset,
        )


        prefetch_pool.submit(
            prefetch_t2m,
            neighbor,
            region,
        )


# ============================================================
# WEBSITE
# ============================================================

@app.route("/")
def root():

    return redirect(
        "/site/"
    )


@app.route("/site/")
def site_index():

    return send_from_directory(
        SITE_DIR,
        "index.html",
    )


@app.route(
    "/site/<path:filename>"
)
def site_file(
    filename,
):

    return send_from_directory(
        SITE_DIR,
        filename,
    )


# ============================================================
# LIVE MODEL METADATA FROM GOOGLE CLOUD STORAGE
# ============================================================
#
# Browser asks:
#
# /metadata/gfs/current.json
#
# Server reads:
#
# gs://massachusettswx-nwp-project/
# metadata/gfs/current.json
#
# This preserves the existing automatic-update system.
# ============================================================

@app.route(
    "/metadata/<path:filename>"
)
def metadata_file(
    filename,
):

    object_name = (
        "metadata/"
        + filename
    )


    try:

        bucket = get_bucket()


        blob = bucket.blob(
            object_name
        )


        if not blob.exists():

            print(
                "METADATA NOT FOUND:",
                object_name,
            )


            return jsonify(
                {
                    "error":
                        "Metadata object not found.",

                    "object":
                        object_name,
                }
            ), 404


        data = (
            blob.download_as_bytes()
        )


        response = Response(
            data,
            mimetype="application/json",
        )


        # We WANT the viewer to see newly published
        # forecast hours immediately.
        response.headers[
            "Cache-Control"
        ] = (
            "no-store, "
            "no-cache, "
            "must-revalidate, "
            "max-age=0"
        )


        return response


    except Exception as exc:

        print(
            "METADATA ERROR:",
            object_name,
            exc,
        )


        return jsonify(
            {
                "error":
                    str(exc),

                "object":
                    object_name,
            }
        ), 500


# ============================================================
# CURRENT ANALYSIS METADATA FROM GOOGLE CLOUD STORAGE
# ============================================================
#
# Browser asks:
#
# /analysis/polar_vortex/10hpa_60n_zonal_wind/latest.json
# /analysis/polar_vortex/10hpa_60n_zonal_wind/bundle.json
#
# Server reads:
#
# gs://massachusettswx-nwp-project/
# analysis/polar_vortex/10hpa_60n_zonal_wind/latest.json
#
# This mirrors the /metadata/ proxy above, but serves the new
# Current Analysis section (separate from the model viewer) instead.
# The actual ERA5 ingestion job lives in
# shared/era5_polar_vortex.py + jobs/update_polar_vortex.py and does
# not run inside this web service; this route only serves what that
# job has already written to Cloud Storage.
# ============================================================

@app.route(
    "/analysis/<path:filename>"
)
def analysis_file(
    filename,
):

    object_name = (
        "analysis/"
        + filename
    )


    try:

        bucket = get_bucket()


        blob = bucket.blob(
            object_name
        )


        if not blob.exists():

            print(
                "ANALYSIS FILE NOT FOUND:",
                object_name,
            )


            return jsonify(
                {
                    "error":
                        "Analysis object not found.",

                    "object":
                        object_name,
                }
            ), 404


        data = (
            blob.download_as_bytes()
        )


        response = Response(
            data,
            mimetype="application/json",
        )


        # latest.json changes daily and should always be fresh.
        # Everything else (per-year series, the combined bundle)
        # changes at most once a day, so a short cache is fine and
        # cuts down on repeated GCS reads.
        if filename.endswith(
            "latest.json"
        ):

            response.headers[
                "Cache-Control"
            ] = (
                "no-store, "
                "no-cache, "
                "must-revalidate, "
                "max-age=0"
            )

        else:

            response.headers[
                "Cache-Control"
            ] = (
                "public, max-age=3600"
            )


        return response


    except Exception as exc:

        print(
            "ANALYSIS FILE ERROR:",
            object_name,
            exc,
        )


        return jsonify(
            {
                "error":
                    str(exc),

                "object":
                    object_name,
            }
        ), 500


# ============================================================
# OPTIONAL LOCAL MODEL FILE ROUTES
# ============================================================

@app.route(
    "/output/<path:filename>"
)
def output_file(
    filename,
):

    return send_from_directory(
        OUTPUT_DIR,
        filename,
    )


@app.route(
    "/preview/<path:filename>"
)
def preview_file(
    filename,
):

    return send_from_directory(
        PREVIEW_DIR,
        filename,
    )


@app.route(
    "/products/<path:filename>"
)
def products_file(
    filename,
):

    object_name = (
        "products/"
        + filename
    )

    try:

        bucket = get_bucket()

        blob = bucket.blob(
            object_name
        )

        if not blob.exists():

            print(
                "PRODUCT NOT FOUND:",
                object_name,
            )

            return jsonify(
                {
                    "error":
                        "Model product object not found.",

                    "object":
                        object_name,
                }
            ), 404

        data = (
            blob.download_as_bytes()
        )

        content_type = (
            blob.content_type
            or
            "image/png"
        )

        response = Response(
            data,
            mimetype=content_type,
        )

        response.headers[
            "Cache-Control"
        ] = (
            "public, "
            "max-age=300"
        )

        return response

    except Exception as exc:

        print(
            "PRODUCT ERROR:",
            object_name,
            exc,
        )

        return jsonify(
            {
                "error":
                    str(exc),

                "object":
                    object_name,
            }
        ), 500


# ============================================================
# ERA5 MAP API
# ============================================================

@app.route(
    "/api/era5/map"
)
def era5_map():

    total_start = (
        time.perf_counter()
    )


    # --------------------------------------------------------
    # REQUEST
    # --------------------------------------------------------

    date = request.args.get(
        "date",
        "1955-08-13",
    )


    hour = request.args.get(
        "hour",
        "18",
    )


    region_key = request.args.get(
        "region",
        "conus",
    )


    product_key = request.args.get(
        "product",
        "t2m",
    )


    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    try:

        requested_date = (
            datetime.strptime(
                date,
                "%Y-%m-%d",
            )
        )


    except ValueError:

        return jsonify(
            {
                "ok":
                    False,

                "error":
                    "Invalid ERA5 date.",
            }
        ), 400


    if requested_date < datetime(
        1940,
        1,
        1,
    ):

        return jsonify(
            {
                "ok":
                    False,

                "error":
                    (
                        "ERA5 begins "
                        "January 1, 1940."
                    ),
            }
        ), 400


    # --------------------------------------------------------
    # HOUR
    # --------------------------------------------------------

    try:

        hour_number = int(
            hour
        )


    except (
        TypeError,
        ValueError,
    ):

        return jsonify(
            {
                "ok":
                    False,

                "error":
                    "Invalid ERA5 hour.",
            }
        ), 400


    if not (
        0
        <= hour_number
        <= 23
    ):

        return jsonify(
            {
                "ok":
                    False,

                "error":
                    (
                        "ERA5 hour must be "
                        "00–23 UTC."
                    ),
            }
        ), 400


    hour = (
        f"{hour_number:02d}"
    )


    # --------------------------------------------------------
    # REGION
    # --------------------------------------------------------

    if region_key not in (
        ERA5_REGIONS
    ):

        return jsonify(
            {
                "ok":
                    False,

                "error":
                    (
                        "ERA5 region "
                        f"'{region_key}' "
                        "is not enabled yet."
                    ),
            }
        ), 400


    region_config = (
        ERA5_REGIONS[
            region_key
        ]
    )


    region = (
        region_config[
            "fetch"
        ]
    )


    # --------------------------------------------------------
    # PRODUCT
    # --------------------------------------------------------

    if product_key not in (
        ERA5_PRODUCTS
    ):

        return jsonify(
            {
                "ok":
                    False,

                "error":
                    "Unknown ERA5 product.",
            }
        ), 400


    product_config = (
        ERA5_PRODUCTS[
            product_key
        ]
    )


    if not product_config[
        "enabled"
    ]:

        return jsonify(
            {
                "ok":
                    False,

                "error":
                    (
                        product_config[
                            "name"
                        ]
                        +
                        " is not enabled yet."
                    ),
            }
        ), 400


    # --------------------------------------------------------
    # TIMESTAMP
    # --------------------------------------------------------

    timestamp = (
        f"{date}T"
        f"{hour}:00"
    )


    print()

    print(
        "========================================"
    )


    print(
        "ERA5 REQUEST:",
        timestamp,
    )


    print(
        "REGION:",
        region_key,
    )


    print(
        "PRODUCT:",
        product_key,
    )


    # ========================================================
    # DATA
    # ========================================================

    try:

        fetch_start = (
            time.perf_counter()
        )


        if product_key == "t2m":

            data = get_t2m(
                timestamp,
                region,
            )


        else:

            raise RuntimeError(
                "ERA5 backend "
                "not implemented."
            )


        fetch_seconds = (
            time.perf_counter()
            - fetch_start
        )


        # ====================================================
        # STATISTICS
        # ====================================================

        minimum = None

        maximum = None


        if product_key == "t2m":

            temperature_f = (
                (
                    data
                    - 273.15
                )
                * 9.0
                / 5.0
                + 32.0
            )


            minimum = float(
                temperature_f
                .min()
                .values
            )


            maximum = float(
                temperature_f
                .max()
                .values
            )


        # ====================================================
        # RENDER
        # ====================================================

        render_start = (
            time.perf_counter()
        )


        if product_key == "t2m":

            image_path = (
                render_t2m(
                    data,
                    timestamp,
                )
            )


        else:

            raise RuntimeError(
                "ERA5 renderer "
                "not implemented."
            )


        render_seconds = (
            time.perf_counter()
            - render_start
        )


        total_seconds = (
            time.perf_counter()
            - total_start
        )


        # ====================================================
        # IMAGE URL
        # ====================================================

        image_filename = (
            Path(
                image_path
            )
            .name
        )


        image_url = (
            "/era5-cache/"
            + image_filename
        )


        # ====================================================
        # PREFETCH
        # ====================================================

        schedule_prefetch(
            timestamp,
            region,
        )


        print(
            f"FETCH: "
            f"{fetch_seconds:.2f}s"
        )


        print(
            f"RENDER: "
            f"{render_seconds:.2f}s"
        )


        print(
            f"TOTAL: "
            f"{total_seconds:.2f}s"
        )


        print(
            "========================================"
        )


        # ====================================================
        # RESPONSE
        # ====================================================

        return jsonify(
            {
                "ok":
                    True,


                "timestamp":
                    timestamp,


                "image_url":
                    image_url,


                "region":
                    region_key,


                "region_name":
                    region_config[
                        "name"
                    ],


                "product":
                    product_key,


                "product_name":
                    product_config[
                        "name"
                    ],


                "statistics": {

                    "minimum":
                        (
                            round(
                                minimum,
                                1,
                            )

                            if minimum
                            is not None

                            else None
                        ),


                    "maximum":
                        (
                            round(
                                maximum,
                                1,
                            )

                            if maximum
                            is not None

                            else None
                        ),

                },


                "timing": {

                    "fetch":
                        round(
                            fetch_seconds,
                            2,
                        ),


                    "render":
                        round(
                            render_seconds,
                            2,
                        ),


                    "total":
                        round(
                            total_seconds,
                            2,
                        ),

                },

            }
        )


    except Exception as exc:

        print(
            "ERA5 ERROR:",
            exc,
        )


        print(
            "========================================"
        )


        return jsonify(
            {
                "ok":
                    False,

                "error":
                    str(
                        exc
                    ),
            }
        ), 500


# ============================================================
# ERA5 RANGE API
# ============================================================

@app.route(
    "/api/era5/range"
)
def era5_range():

    start_date = request.args.get(
        "start_date"
    )


    start_hour = request.args.get(
        "start_hour",
        "00",
    )


    end_date = request.args.get(
        "end_date"
    )


    end_hour = request.args.get(
        "end_hour",
        "00",
    )


    interval = request.args.get(
        "interval",
        "1",
    )


    try:

        interval = int(
            interval
        )


        if interval not in (
            1,
            3,
            6,
            12,
            24,
        ):

            raise ValueError


        start = datetime.strptime(
            (
                f"{start_date} "
                f"{start_hour}"
            ),
            "%Y-%m-%d %H",
        )


        end = datetime.strptime(
            (
                f"{end_date} "
                f"{end_hour}"
            ),
            "%Y-%m-%d %H",
        )


    except Exception:

        return jsonify(
            {
                "ok":
                    False,

                "error":
                    "Invalid ERA5 range.",
            }
        ), 400


    if start < datetime(
        1940,
        1,
        1,
    ):

        return jsonify(
            {
                "ok":
                    False,

                "error":
                    (
                        "ERA5 begins "
                        "January 1, 1940."
                    ),
            }
        ), 400


    if end < start:

        return jsonify(
            {
                "ok":
                    False,

                "error":
                    (
                        "End time must be "
                        "after start time."
                    ),
            }
        ), 400


    timestamps = []

    current = start


    MAX_FRAMES = 240


    while current <= end:

        timestamps.append(
            current.strftime(
                "%Y-%m-%dT%H:%M"
            )
        )


        if len(
            timestamps
        ) > MAX_FRAMES:

            return jsonify(
                {
                    "ok":
                        False,

                    "error":
                        (
                            "Maximum ERA5 "
                            "range is "
                            "240 frames."
                        ),
                }
            ), 400


        current += timedelta(
            hours=interval
        )


    return jsonify(
        {
            "ok":
                True,

            "timestamps":
                timestamps,

            "count":
                len(
                    timestamps
                ),

            "interval":
                interval,
        }
    )


# ============================================================
# ERA5 PREFETCH API
# ============================================================

@app.route(
    "/api/era5/prefetch"
)
def era5_prefetch():

    timestamp = request.args.get(
        "timestamp"
    )


    region_key = request.args.get(
        "region",
        "conus",
    )


    if not timestamp:

        return jsonify(
            {
                "ok":
                    False,

                "error":
                    "Timestamp required.",
            }
        ), 400


    if region_key not in (
        ERA5_REGIONS
    ):

        return jsonify(
            {
                "ok":
                    False,

                "error":
                    "Unknown ERA5 region.",
            }
        ), 400


    region = (
        ERA5_REGIONS[
            region_key
        ]["fetch"]
    )


    schedule_prefetch(
        timestamp,
        region,
    )


    return jsonify(
        {
            "ok":
                True,
        }
    )


# ============================================================
# ERA5 GENERATED MAPS
# ============================================================

@app.route(
    "/era5-cache/<path:filename>"
)
def era5_cache(
    filename,
):

    return send_from_directory(
        ERA5_CACHE_DIR,
        filename,
    )


# ============================================================
# HEALTH
# ============================================================

@app.route(
    "/health"
)
def health():

    return jsonify(
        {
            "ok":
                True,

            "site":
                "MassachusettsWx Models",

            "era5":
                True,

            "storage_bucket":
                get_bucket_name(),
        }
    )


# ============================================================
# START
# ============================================================


# ============================================================
# PRIVATE GCS OBJECT PROXY
# ============================================================
#
# Browser:
#
#     /objects/products/gfs/20260814/18/h5_vort/conus/f000.png
#
# Cloud Run authenticates to private GCS using its service
# account and returns the bytes to the browser.
#
# GCS itself remains private.
# ============================================================

@app.route(
    "/objects/<path:object_name>"
)
def serve_private_object(
    object_name,
):

    object_name = (
        str(
            object_name
        )
        .lstrip("/")
    )

    # Only expose website-readable model products.
    if not object_name.startswith(
        "products/"
    ):

        return (
            "Not found",
            404,
        )

    blob = (
        get_bucket()
        .blob(
            object_name
        )
    )

    if not blob.exists():

        return (
            "Not found",
            404,
        )

    data = (
        blob.download_as_bytes()
    )

    content_type = (
        blob.content_type
        or
        "application/octet-stream"
    )

    response = Response(
        data,
        status=200,
        content_type=(
            content_type
        ),
    )

    # Model frames can be cached briefly, but keep updates fresh.
    response.headers[
        "Cache-Control"
    ] = (
        "public, max-age=60"
    )

    return response


if __name__ == "__main__":

    print()

    print(
        "========================================"
    )


    print(
        "MASSACHUSETTSWX MODELS"
    )


    print(
        "Forecast viewer + ERA5 archive"
    )


    print(
        "Live forecast metadata:"
    )


    print(
        "gs://"
        + get_bucket_name()
        + "/metadata/"
    )


    print(
        "http://localhost:8080/site/"
    )


    print(
        "========================================"
    )


    print()


    app.run(
        host="0.0.0.0",

        port=8080,

        debug=False,

        threaded=True,
    )
