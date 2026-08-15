from pathlib import Path

from ecmwf.opendata import (
    Client,
)

from shared.download import (
    build_ecmwf_pressure_plan,
    build_ecmwf_surface_plan,
)

from shared.storage import (
    get_local_root,
)


# ============================================================
# TEMPORARY STORAGE
# ============================================================

def get_ifs_temp_root():
    """
    Return the temporary working directory for IFS raw GRIB data.

    Raw forecast files are temporary and should not live in the
    persistent Cloud Shell /home filesystem.
    """

    return (
        get_local_root()
        / "ifs"
    )


# ============================================================
# CLIENT
# ============================================================

def create_ifs_client():

    return Client(
        source="ecmwf",
        model="ifs",
        resol="0p25",
        infer_stream_keyword=True,
        preserve_request_order=False,
    )


# ============================================================
# CYCLE NORMALIZATION
# ============================================================

def normalize_cycle(
    cycle=None,
):

    if cycle is None:

        return {
            "date": None,
            "time": None,
            "id": "latest",
        }

    return {
        "date": cycle[
            "date"
        ],

        "time": int(
            cycle[
                "hour"
            ]
        ),

        "id": cycle[
            "id"
        ],
    }


# ============================================================
# IFS STREAM
#
# Cycle 50r1:
#
# Atmospheric deterministic 00/06/12/18 data use OPER.
# ============================================================

def get_ifs_stream(
    hour,
):

    hour = int(
        hour
    )

    if hour in {
        0,
        6,
        12,
        18,
    }:

        return "oper"

    raise ValueError(
        f"Invalid IFS cycle hour: "
        f"{hour}"
    )


# ============================================================
# OUTPUT FILE
# ============================================================

def build_output_path(
    cycle_id,
    forecast_hour,
):
    """
    Build the temporary combined IFS GRIB path.

    Example:

        /tmp/massachusettswx/
            ifs/
                20260809_12z/
                    ifs_20260809_12z_f006.grib2
    """

    cycle_dir = (
        get_ifs_temp_root()
        / cycle_id
    )

    cycle_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    return (
        cycle_dir
        /
        (
            f"ifs_"
            f"{cycle_id}_"
            f"f{forecast_hour:03d}."
            f"grib2"
        )
    )


# ============================================================
# DOWNLOAD ONE FORECAST HOUR
# ============================================================

def download_ifs_hour(
    forecast_hour,
    *,
    products,
    cycle=None,
):

    cycle_info = (
        normalize_cycle(
            cycle
        )
    )

    output_path = (
        build_output_path(
            cycle_info[
                "id"
            ],
            forecast_hour,
        )
    )

    # --------------------------------------------------------
    # EXISTING DATA
    # --------------------------------------------------------

    if (
        output_path.exists()
        and
        output_path.stat().st_size
        > 0
    ):

        print(
            f"IFS "
            f"f{forecast_hour:03d}: "
            f"already downloaded "
            f"("
            f"{output_path.stat().st_size / 1024 / 1024:.2f} MB"
            f")"
        )

        return output_path

    client = (
        create_ifs_client()
    )

    # --------------------------------------------------------
    # FIELD PLANS
    # --------------------------------------------------------

    pressure_plan = (
        build_ecmwf_pressure_plan(
            "ifs",
            products,
        )
    )

    surface_plan = (
        build_ecmwf_surface_plan(
            "ifs",
            products,
        )
    )

    pressure_params = (
        pressure_plan[
            "params"
        ]
    )

    pressure_levels = (
        pressure_plan[
            "levels"
        ]
    )

    surface_params = (
        surface_plan[
            "params"
        ]
    )

    # --------------------------------------------------------
    # COMMON REQUEST
    # --------------------------------------------------------

    request_common = {
        "type": "fc",

        "step": (
            int(
                forecast_hour
            )
        ),
    }

    if (
        cycle_info[
            "date"
        ]
        is not None
    ):

        request_common[
            "date"
        ] = cycle_info[
            "date"
        ]

        request_common[
            "time"
        ] = cycle_info[
            "time"
        ]

        request_common[
            "stream"
        ] = get_ifs_stream(
            cycle_info[
                "time"
            ]
        )

    temporary_files = []

    # ========================================================
    # PRESSURE LEVEL DATA
    # ========================================================

    if pressure_params:

        pressure_path = (
            output_path.parent
            /
            (
                f".ifs_"
                f"f{forecast_hour:03d}_"
                f"pressure.grib2"
            )
        )

        request = dict(
            request_common
        )

        request.update(
            {
                "levtype": "pl",

                "param": (
                    pressure_params
                ),

                "levelist": (
                    pressure_levels
                ),
            }
        )

        print(
            f"IFS "
            f"f{forecast_hour:03d}: "
            f"downloading "
            f"pressure fields..."
        )

        client.retrieve(
            request=request,

            target=str(
                pressure_path
            ),
        )

        if (
            pressure_path.exists()
            and
            pressure_path.stat().st_size
            > 0
        ):

            temporary_files.append(
                pressure_path
            )

    # ========================================================
    # SINGLE LEVEL DATA
    # ========================================================

    if surface_params:

        surface_path = (
            output_path.parent
            /
            (
                f".ifs_"
                f"f{forecast_hour:03d}_"
                f"surface.grib2"
            )
        )

        request = dict(
            request_common
        )

        request.update(
            {
                "levtype": "sfc",

                "param": (
                    surface_params
                ),
            }
        )

        print(
            f"IFS "
            f"f{forecast_hour:03d}: "
            f"downloading "
            f"surface fields..."
        )

        client.retrieve(
            request=request,

            target=str(
                surface_path
            ),
        )

        if (
            surface_path.exists()
            and
            surface_path.stat().st_size
            > 0
        ):

            temporary_files.append(
                surface_path
            )

    # ========================================================
    # VERIFY DOWNLOAD
    # ========================================================

    if not temporary_files:

        raise RuntimeError(
            f"IFS "
            f"f{forecast_hour:03d}: "
            f"no data downloaded"
        )

    # ========================================================
    # COMBINE GRIB FILES
    # ========================================================

    try:

        with open(
            output_path,
            "wb",
        ) as destination:

            for temporary_file in (
                temporary_files
            ):

                with open(
                    temporary_file,
                    "rb",
                ) as source:

                    while True:

                        chunk = (
                            source.read(
                                1024
                                *
                                1024
                            )
                        )

                        if not chunk:

                            break

                        destination.write(
                            chunk
                        )

    finally:

        # ----------------------------------------------------
        # REMOVE PRESSURE/SURFACE COMPONENT FILES
        # ----------------------------------------------------

        for temporary_file in (
            temporary_files
        ):

            temporary_file.unlink(
                missing_ok=True
            )

    # --------------------------------------------------------
    # FINAL CHECK
    # --------------------------------------------------------

    if (
        not output_path.exists()
        or
        output_path.stat().st_size
        == 0
    ):

        output_path.unlink(
            missing_ok=True
        )

        raise RuntimeError(
            f"IFS "
            f"f{forecast_hour:03d}: "
            f"combined GRIB is empty"
        )

    print(
        f"IFS "
        f"f{forecast_hour:03d}: "
        f"complete "
        f"("
        f"{output_path.stat().st_size / 1024 / 1024:.2f} "
        f"MB"
        f")"
    )

    return output_path


# ============================================================
# COMPLETE CYCLE
# ============================================================

def download_ifs_cycle(
    *,
    forecast_hours,
    products,
    cycle=None,
):

    cycle_info = (
        normalize_cycle(
            cycle
        )
    )

    print()
    print("=" * 70)
    print(
        "ECMWF IFS DOWNLOAD"
    )
    print("=" * 70)

    print(
        f"Cycle: "
        f"{cycle_info['id']}"
    )

    print(
        f"Forecast hours: "
        f"{len(forecast_hours)}"
    )

    print(
        f"Temporary root: "
        f"{get_ifs_temp_root()}"
    )

    print("=" * 70)

    forecast_files = []

    for (
        index,
        forecast_hour,
    ) in enumerate(
        forecast_hours,
        start=1,
    ):

        print()

        print(
            f"[{index}/"
            f"{len(forecast_hours)}] "
            f"IFS "
            f"f{forecast_hour:03d}"
        )

        try:

            output_path = (
                download_ifs_hour(
                    forecast_hour,

                    products=(
                        products
                    ),

                    cycle=(
                        cycle
                    ),
                )
            )

            if (
                output_path.exists()
                and
                output_path.stat().st_size
                > 0
            ):

                forecast_files.append(
                    (
                        int(
                            forecast_hour
                        ),
                        output_path,
                    )
                )

        except Exception as exc:

            print(
                f"IFS "
                f"f{forecast_hour:03d}: "
                f"DOWNLOAD FAILED: "
                f"{exc}"
            )

    print()
    print("=" * 70)

    print(
        f"IFS download complete: "
        f"{len(forecast_files)}/"
        f"{len(forecast_hours)} "
        f"forecast hours available"
    )

    print("=" * 70)

    return forecast_files