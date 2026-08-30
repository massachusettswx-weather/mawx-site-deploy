EXPECTED_FNV3_MEMBERS = 50


class FNV3EnsembleProcessor:
    """
    Process the standard 51-member FNV3 Cyclone ensemble.
    """

    def __init__(self, tracks):
        self.tracks = tracks

    def member_tracks(self):
        return self.tracks

    def member_ids(self):
        members = set()

        for point in self.tracks:
            if isinstance(point, dict):
                member = point.get("member")
            else:
                member = getattr(point, "member", None)

            if member is not None:
                members.add(int(member))

        return sorted(members)

    def member_count(self):
        return len(self.member_ids())

    def validate_member_count(self):
        count = self.member_count()

        if count != EXPECTED_FNV3_MEMBERS:
            raise ValueError(
                f"Expected {EXPECTED_FNV3_MEMBERS} FNV3 members, "
                f"but found {count}."
            )

        return True

    def ensemble_mean_track(self):
        raise NotImplementedError

    def track_density(self):
        raise NotImplementedError

    def intensity_distribution(self):
        raise NotImplementedError
