from __future__ import annotations

import os
import time

from dataclasses import dataclass


# ============================================================
# MASSACHUSETTSWX OPERATIONAL LIFECYCLE
#
# Shared policy for current and future operational models.
#
# Goals:
#   - one warm execution during active dissemination
#   - no rapid Cloud Run relaunch loop
#   - bounded waiting
#   - inexpensive polling
#   - execution exits after dissemination becomes inactive
# ============================================================


def env_int(
    name,
    default,
    minimum=1,
):
    return max(
        minimum,
        int(
            os.environ.get(
                name,
                str(default),
            )
        ),
    )


@dataclass(frozen=True)
class OperationalLifecyclePolicy:

    poll_seconds: int

    # Number of consecutive frontier polls with no new usable
    # data before this execution is allowed to exit.
    idle_polls_before_exit: int

    # Absolute safety bound. Cloud Run must never sit around
    # indefinitely because an upstream source is broken.
    max_window_seconds: int


    @property
    def idle_exit_seconds(
        self,
    ):
        return (
            self.poll_seconds
            *
            self.idle_polls_before_exit
        )


def policy_for_model(
    model,
):
    model = (
        str(model)
        .strip()
        .lower()
    )

    prefix = (
        model
        .upper()
        .replace(
            "-",
            "_",
        )
    )

    # Defaults intentionally favor inexpensive polling rather
    # than CPU-heavy rapid probes.
    #
    # These can be tuned per model through Cloud Run env vars
    # without changing source code.

    poll_seconds = env_int(
        f"{prefix}_POLL_SECONDS",
        20,
        minimum=5,
    )

    idle_polls = env_int(
        f"{prefix}_IDLE_POLLS_BEFORE_EXIT",
        15,
        minimum=2,
    )

    max_window = env_int(
        f"{prefix}_MAX_DISSEMINATION_SECONDS",
        10800,
        minimum=300,
    )

    return OperationalLifecyclePolicy(
        poll_seconds=poll_seconds,
        idle_polls_before_exit=idle_polls,
        max_window_seconds=max_window,
    )


class OperationalLifecycle:

    def __init__(
        self,
        *,
        model,
        policy=None,
    ):
        self.model = (
            str(model)
            .strip()
            .lower()
        )

        self.policy = (
            policy
            or
            policy_for_model(
                self.model
            )
        )

        self.started_monotonic = (
            time.monotonic()
        )

        self.idle_polls = 0


    def mark_progress(
        self,
    ):
        """
        New upstream data was successfully obtained/processed.
        Reset the idle clock.
        """

        self.idle_polls = 0


    def mark_idle_poll(
        self,
    ):
        """
        One frontier probe found no new usable data.
        """

        self.idle_polls += 1


    def window_expired(
        self,
    ):
        return (
            time.monotonic()
            -
            self.started_monotonic
            >=
            self.policy.max_window_seconds
        )


    def should_exit(
        self,
    ):
        return (
            self.window_expired()
            or
            self.idle_polls
            >=
            self.policy.idle_polls_before_exit
        )


    def wait(
        self,
    ):
        """
        Sleep consumes no CPU while preserving the warm Cloud
        Run execution/container during an active dissemination
        window.
        """

        time.sleep(
            self.policy.poll_seconds
        )


    def summary(
        self,
    ):
        return {
            "model": self.model,
            "poll_seconds": (
                self.policy.poll_seconds
            ),
            "idle_polls": (
                self.idle_polls
            ),
            "idle_polls_before_exit": (
                self.policy.idle_polls_before_exit
            ),
            "idle_exit_seconds": (
                self.policy.idle_exit_seconds
            ),
            "max_window_seconds": (
                self.policy.max_window_seconds
            ),
        }


# ============================================================
# OPERATIONAL CYCLE STATE
#
# Combines:
#   - expected model inventory
#   - known completed inventory
#   - selective repair planning
#   - frontier tracking
#
# No cloud calls are performed here.
# ============================================================


# ============================================================
# FORECAST-HOUR FRONTIER SWEEP
#
# Tracks unresolved forecast hours in memory.
#
# A temporarily missing upstream hour remains pending while
# later available hours are allowed to proceed.
# ============================================================

class FrontierSweep:

    def __init__(
        self,
        forecast_hours,
    ):
        self.forecast_hours = list(
            forecast_hours
        )

        self.pending = set(
            self.forecast_hours
        )

        self.completed = set()


    def mark_completed(
        self,
        forecast_hour,
    ):
        forecast_hour = int(
            forecast_hour
        )

        self.completed.add(
            forecast_hour
        )

        self.pending.discard(
            forecast_hour
        )


    def mark_missing(
        self,
        forecast_hour,
    ):
        forecast_hour = int(
            forecast_hour
        )

        if (
            forecast_hour
            not in self.completed
        ):
            self.pending.add(
                forecast_hour
            )


    def next_hours(
        self,
    ):
        return [
            hour
            for hour in self.forecast_hours
            if hour in self.pending
        ]


    def complete(
        self,
    ):
        return not self.pending


    def summary(
        self,
    ):
        return {
            "expected": len(
                self.forecast_hours
            ),
            "completed": len(
                self.completed
            ),
            "pending": len(
                self.pending
            ),
        }


class OperationalCycleState:

    def __init__(
        self,
        *,
        model,
        cycle_id,
        forecast_hours,
        products,
        regions,
        completed_inventory=None,
    ):
        from shared.completeness import (
            FrameCompleteness,
        )

        self.model = str(
            model
        )

        self.cycle_id = str(
            cycle_id
        )

        self.forecast_hours = list(
            forecast_hours
        )

        self.products = list(
            products
        )

        self.regions = list(
            regions
        )

        self.completeness = (
            FrameCompleteness(
                model=self.model,
                cycle_id=self.cycle_id,
            )
        )

        if completed_inventory:

            self.completeness.seed_completed(
                completed_inventory
            )

        self.frontier = FrontierSweep(
            self.forecast_hours
        )

        # A forecast hour is frontier-complete only when EVERY
        # required product/region combination is complete.
        for hour in self.forecast_hours:

            if self.hour_complete(
                hour
            ):
                self.frontier.mark_completed(
                    hour
                )


    def work_plan(
        self,
        forecast_hour,
    ):
        """
        Return only missing product/region combinations for one
        forecast hour.
        """

        return (
            self.completeness
            .work_plan_for_hour(
                products=self.products,
                regions=self.regions,
                forecast_hour=(
                    forecast_hour
                ),
            )
        )


    def mark_completed(
        self,
        *,
        product,
        region,
        forecast_hour,
    ):
        """
        Update in-memory inventory after a successful upload.
        """

        self.completeness.mark_completed(
            product=product,
            region=region,
            forecast_hour=(
                forecast_hour
            ),
        )

        if self.hour_complete(
            forecast_hour
        ):

            self.frontier.mark_completed(
                forecast_hour
            )


    def mark_failed(
        self,
        *,
        product,
        region,
        forecast_hour,
    ):
        self.completeness.mark_failed(
            product=product,
            region=region,
            forecast_hour=(
                forecast_hour
            ),
        )

        self.frontier.mark_missing(
            forecast_hour
        )


    def hour_complete(
        self,
        forecast_hour,
    ):
        return (
            self.completeness
            .hour_complete(
                products=self.products,
                regions=self.regions,
                forecast_hour=(
                    forecast_hour
                ),
            )
        )


    def cycle_complete(
        self,
    ):
        """
        True only when the complete model × hour × product ×
        region inventory exists.
        """

        return all(
            self.hour_complete(
                hour
            )
            for hour in self.forecast_hours
        )


    def unresolved_hours(
        self,
    ):
        """
        Forecast hours that still contain at least one missing
        product/region combination.
        """

        return [
            hour
            for hour in self.forecast_hours
            if not self.hour_complete(
                hour
            )
        ]


    def summary(
        self,
    ):
        return (
            self.completeness
            .summary(
                products=self.products,
                regions=self.regions,
                forecast_hours=(
                    self.forecast_hours
                ),
            )
        )
