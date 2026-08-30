from pathlib import Path

from ecmwf.opendata import (
    Client,
)

from shared.download import (
    build_ecmwf_pressure_plan,
    build_ecmwf_surface_plan,
)

from shared.storage import (
    build_local_forecast_path,
)


# ============================================================
# CLIENT
# ============================================================

def create_aifs_client():

    return Client(
        source="ecmwf",
        model="aifs-single",
        resol="0p25",
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
# LOCAL OUTPUT PATH
# ============================================================

def build_output_path(
    cycle_id,
    forecast_hour,
    *,
    cycle_date=None,
    cycle_hour=None,
):
    """
    Build a temporary raw AIFS GRIB path.

    Exact cycles use:

        /tmp/massachusettswx/aifs/YYYYMMDD/HH/fXXX.grib2

    Manual "latest" runs use:

        /tmp/massachusettswx/aifs/latest/00/fXXX.grib2
    """

    if cycle_date is None:

        cycle_date = (
            "latest"
        )

    if cycle_hour is None:

        cycle_hour = 0

    return (
        build_local_forecast_path(
            model="aifs",
            cycle_date=(
                cycle_date
            ),
            cycle_hour=(
                cycle_hour
            ),
            forecast_hour=(
                forecast_hour
            ),
            extension="grib2",
        )
    )


# ============================================================
# DOWNLOAD ONE AIFS FORECAST HOUR
# ============================================================

def download_aifs_hour(
    forecast_hour,
    *,
    products,
    cycle=None,
):

    forecast_hour = int(
        forecast_hour
    )

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
            cycle_date=(
                cycle_info[
                    "date"
                ]
            ),
            cycle_hour=(
                cycle_info[
                    "time"
                ]
            ),
        )
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # REUSE COMPLETE TEMP FILE
    # --------------------------------------------------------

    if (
        output_path.exists()
        and
        output_path.stat().st_size
        > 0
    ):

        print(
            f"AIFS "
            f"f{forecast_hour:03d}: "
            f"already downloaded "
            f"("
            f"{output_path.stat().st_size / 1024 / 1024:.2f} MB"
            f")"
        )

        return output_path

    client = (
        create_aifs_client()
    )

    # --------------------------------------------------------
    # FIELD PLANS
    # --------------------------------------------------------

    pressure_plan = (
        build_ecmwf_pressure_plan(
            "aifs",
            products,
        )
    )

    surface_plan = (
        build_ecmwf_surface_plan(
            "aifs",
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

    request_common = {
        "type": "fc",
        "step": forecast_hour,
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

    pressure_path = (
        output_path.parent
        /
        (
            f".aifs_"
            f"f{forecast_hour:03d}_"
            f"pressure.grib2"
        )
    )

    surface_path = (
        output_path.parent
        /
        (
            f".aifs_"
            f"f{forecast_hour:03d}_"
            f"surface.grib2"
        )
    )

    temporary_files = []

    try:

        # ====================================================
        # PRESSURE LEVELS
        # ====================================================

        if pressure_params:

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
                f"AIFS "
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

        # ====================================================
        # SURFACE
        # ====================================================

        if surface_params:

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
                f"AIFS "
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

        # ====================================================
        # VERIFY
        # ====================================================

        if not temporary_files:

            raise RuntimeError(
                f"AIFS "
                f"f{forecast_hour:03d}: "
                f"no data downloaded"
            )

        # ====================================================
        # COMBINE
        # ====================================================

        with output_path.open(
            "wb"
        ) as destination:

            for temporary_file in (
                temporary_files
            ):

                with temporary_file.open(
                    "rb"
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
                f"AIFS "
                f"f{forecast_hour:03d}: "
                f"combined GRIB is empty"
            )

        print(
            f"AIFS "
            f"f{forecast_hour:03d}: "
            f"complete "
            f"("
            f"{output_path.stat().st_size / 1024 / 1024:.2f} MB"
            f")"
        )

        return output_path

    except Exception:

        output_path.unlink(
            missing_ok=True
        )

        raise

    finally:

        pressure_path.unlink(
            missing_ok=True
        )

        surface_path.unlink(
            missing_ok=True
        )


# ============================================================
# BACKWARD-COMPATIBLE COMPLETE CYCLE
# ============================================================

def download_aifs_cycle(
    *,
    forecast_hours,
    products,
    cycle=None,
):
    """
    Keep existing callers working.

    The operational runner now streams one hour at a time, so this
    function is retained only for compatibility/manual use.
    """

    cycle_info = (
        normalize_cycle(
            cycle
        )
    )

    print()
    print("=" * 70)
    print(
        "ECMWF AIFS DOWNLOAD"
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
            f"AIFS "
            f"f{int(forecast_hour):03d}"
        )

        try:

            path = (
                download_aifs_hour(
                    forecast_hour,
                    products=(
                        products
                    ),
                    cycle=cycle,
                )
            )

            forecast_files.append(
                (
                    int(
                        forecast_hour
                    ),
                    path,
                )
            )

        except Exception as error:

            print(
                f"AIFS "
                f"f{int(forecast_hour):03d} "
                f"FAILED: "
                f"{error}"
            )

    forecast_files.sort(
        key=lambda item: item[
            0
        ]
    )

    return forecast_files