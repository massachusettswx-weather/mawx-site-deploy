EXPECTED_FNV3_LARGE_MEMBERS = 1000


class FNV3LargeEnsembleProcessor:
    """
    Processing for the WeatherNext/FNV3
    1000-member cyclone ensemble.

    One ensemble member may contain many independent
    tropical systems, so a unique track is:

        (system_id, member)
    """

    def __init__(
        self,
        tracks,
    ):
        self.tracks = tracks

    @staticmethod
    def _value(
        point,
        name,
        default=None,
    ):
        if isinstance(
            point,
            dict,
        ):
            return point.get(
                name,
                default,
            )

        return getattr(
            point,
            name,
            default,
        )

    def member_ids(self):
        members = set()

        for point in self.tracks:
            member = self._value(
                point,
                "member",
            )

            if member is not None:
                members.add(
                    int(member)
                )

        return sorted(
            members
        )

    def member_count(self):
        return len(
            self.member_ids()
        )

    def validate_member_count(
        self,
        strict=True,
    ):
        count = self.member_count()

        if (
            strict
            and count
            != EXPECTED_FNV3_LARGE_MEMBERS
        ):
            raise ValueError(
                "Expected "
                f"{EXPECTED_FNV3_LARGE_MEMBERS} "
                "FNV3-L members, but found "
                f"{count}."
            )

        return (
            count
            == EXPECTED_FNV3_LARGE_MEMBERS
        )

    def individual_tracks(self):
        grouped = {}

        for point in self.tracks:
            member = self._value(
                point,
                "member",
            )

            system_id = self._value(
                point,
                "system_id",
            )

            if (
                member is None
                or system_id is None
            ):
                continue

            key = (
                str(system_id),
                int(member),
            )

            grouped.setdefault(
                key,
                [],
            ).append(
                point
            )

        for key in grouped:
            grouped[key].sort(
                key=lambda p: (
                    self._value(
                        p,
                        "forecast_hour",
                        0,
                    )
                )
            )

        return grouped

    def member_tracks(self):
        """
        Retained for compatibility.

        Returns all points organized by member. Do not use
        this for plotting individual cyclone paths.
        """

        grouped = {}

        for point in self.tracks:
            member = self._value(
                point,
                "member",
            )

            if member is None:
                continue

            grouped.setdefault(
                int(member),
                [],
            ).append(
                point
            )

        return grouped

    def generated_tracks(self):
        output = {}

        for key, points in (
            self.individual_tracks()
            .items()
        ):
            if any(
                self._value(
                    p,
                    "genesis",
                    False,
                )
                for p in points
            ):
                output[
                    key
                ] = points

        return output

    def existing_tracks(self):
        output = {}

        for key, points in (
            self.individual_tracks()
            .items()
        ):
            if any(
                self._value(
                    p,
                    "existing_storm",
                    False,
                )
                for p in points
            ):
                output[
                    key
                ] = points

        return output
