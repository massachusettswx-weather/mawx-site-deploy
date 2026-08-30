from fnv3_cyclone.regions import (
    get_extent,
)


def point_in_extent(
    latitude,
    longitude,
    extent,
):
    west, east, south, north = extent

    return (
        west
        <= longitude
        <= east
        and
        south
        <= latitude
        <= north
    )


def group_individual_tracks(
    tracks,
):
    """
    Group points using the true WeatherNext cyclone track key:

        (system_id, member)

    A single ensemble member can contain many independent
    cyclones.
    """

    systems = {}

    for point in tracks:
        key = (
            point.system_id,
            point.member,
        )

        systems.setdefault(
            key,
            [],
        ).append(
            point
        )

    for key in systems:
        systems[key].sort(
            key=lambda p: (
                p.forecast_hour
            )
        )

    return systems


def filter_tracks_for_basin(
    tracks,
    basin,
):
    """
    Retain complete tracks that intersect the requested basin.

    We intentionally do NOT throw away portions of a storm
    outside the selected geographic box.

    This is important for tropical cyclogenesis tracks that
    develop outside a basin and later enter it, or that form
    inside a basin and subsequently leave it.
    """

    extent = get_extent(
        basin
    )

    grouped = (
        group_individual_tracks(
            tracks
        )
    )

    selected = {}

    for key, points in grouped.items():
        intersects = any(
            point_in_extent(
                point.latitude,
                point.longitude,
                extent,
            )
            for point in points
        )

        if intersects:
            selected[
                key
            ] = points

    return selected


def flatten_tracks(
    grouped_tracks,
):
    """
    Convert a grouped track dictionary back into one point list.
    """

    output = []

    for points in grouped_tracks.values():
        output.extend(
            points
        )

    return output
