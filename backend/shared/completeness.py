from __future__ import annotations

from dataclasses import dataclass, field


# ============================================================
# MASSACHUSETTSWX SHARED COMPLETENESS ENGINE
#
# Model-agnostic inventory tracking for:
#
#   model × cycle × forecast hour × product × region
#
# HOT PATH:
#   Track completed work in memory as maps upload.
#
# START / RESUME:
#   Seed completed keys from persistent inventory once.
#
# REPAIR:
#   Calculate only genuinely missing work.
#
# This module performs NO cloud listings itself.
# ============================================================


def inventory_key(
    *,
    product,
    region,
    forecast_hour,
):
    return (
        str(product),
        str(region),
        int(forecast_hour),
    )


@dataclass
class FrameCompleteness:

    model: str
    cycle_id: str

    completed: set = field(
        default_factory=set
    )

    failed: set = field(
        default_factory=set
    )


    # ========================================================
    # BASIC STATE
    # ========================================================

    def seed_completed(
        self,
        keys,
    ):
        """
        Seed the ledger from an inventory obtained when a job
        starts/resumes.

        No cloud operation happens here.
        """

        for key in keys:

            if len(key) != 3:
                continue

            product, region, hour = key

            self.completed.add(
                inventory_key(
                    product=product,
                    region=region,
                    forecast_hour=hour,
                )
            )


    def mark_completed(
        self,
        *,
        product,
        region,
        forecast_hour,
    ):
        key = inventory_key(
            product=product,
            region=region,
            forecast_hour=forecast_hour,
        )

        self.completed.add(
            key
        )

        self.failed.discard(
            key
        )


    def mark_failed(
        self,
        *,
        product,
        region,
        forecast_hour,
    ):
        key = inventory_key(
            product=product,
            region=region,
            forecast_hour=forecast_hour,
        )

        if key not in self.completed:
            self.failed.add(
                key
            )


    def is_completed(
        self,
        *,
        product,
        region,
        forecast_hour,
    ):
        return (
            inventory_key(
                product=product,
                region=region,
                forecast_hour=forecast_hour,
            )
            in self.completed
        )


    # ========================================================
    # EXPECTED INVENTORY
    # ========================================================

    def expected_keys(
        self,
        *,
        products,
        regions,
        forecast_hours,
    ):
        return {
            inventory_key(
                product=product,
                region=region,
                forecast_hour=hour,
            )
            for hour in forecast_hours
            for product in products
            for region in regions
        }


    def expected_for_hour(
        self,
        *,
        products,
        regions,
        forecast_hour,
    ):
        return {
            inventory_key(
                product=product,
                region=region,
                forecast_hour=forecast_hour,
            )
            for product in products
            for region in regions
        }


    # ========================================================
    # MISSING INVENTORY
    # ========================================================

    def missing(
        self,
        *,
        products,
        regions,
        forecast_hours,
    ):
        return (
            self.expected_keys(
                products=products,
                regions=regions,
                forecast_hours=forecast_hours,
            )
            -
            self.completed
        )


    def missing_for_hour(
        self,
        *,
        products,
        regions,
        forecast_hour,
    ):
        return (
            self.expected_for_hour(
                products=products,
                regions=regions,
                forecast_hour=forecast_hour,
            )
            -
            self.completed
        )


    def hour_complete(
        self,
        *,
        products,
        regions,
        forecast_hour,
    ):
        return not self.missing_for_hour(
            products=products,
            regions=regions,
            forecast_hour=forecast_hour,
        )


    # ========================================================
    # SELECTIVE WORK PLAN
    # ========================================================

    def work_plan_for_hour(
        self,
        *,
        products,
        regions,
        forecast_hour,
    ):
        """
        Return only missing product/region combinations.

        Structure:

        {
            "conus": {
                "mslp",
                "t2m",
            },

            "europe": {
                "t2m",
            },
        }

        A complete region is omitted entirely.
        """

        work = {}

        for region in regions:

            missing_products = set()

            for product in products:

                if not self.is_completed(
                    product=product,
                    region=region,
                    forecast_hour=forecast_hour,
                ):
                    missing_products.add(
                        product
                    )

            if missing_products:

                work[
                    region
                ] = missing_products

        return work


    def complete_regions_for_hour(
        self,
        *,
        products,
        regions,
        forecast_hour,
    ):
        complete = []

        for region in regions:

            if all(
                self.is_completed(
                    product=product,
                    region=region,
                    forecast_hour=forecast_hour,
                )
                for product in products
            ):
                complete.append(
                    region
                )

        return complete


    def incomplete_regions_for_hour(
        self,
        *,
        products,
        regions,
        forecast_hour,
    ):
        plan = self.work_plan_for_hour(
            products=products,
            regions=regions,
            forecast_hour=forecast_hour,
        )

        return list(
            plan.keys()
        )


    # ========================================================
    # PUBLISH SAFETY
    # ========================================================

    def publishable_hour(
        self,
        *,
        products,
        regions,
        forecast_hour,
    ):
        """
        A forecast hour is globally publishable only after its
        required inventory is complete for every configured
        region.

        Individual maps can still upload immediately while the
        hour is being rendered.
        """

        return self.hour_complete(
            products=products,
            regions=regions,
            forecast_hour=forecast_hour,
        )


    # ========================================================
    # SUMMARY
    # ========================================================

    def summary(
        self,
        *,
        products,
        regions,
        forecast_hours,
    ):
        expected = self.expected_keys(
            products=products,
            regions=regions,
            forecast_hours=forecast_hours,
        )

        completed = (
            expected
            &
            self.completed
        )

        failed = (
            expected
            &
            self.failed
        )

        missing = (
            expected
            -
            self.completed
        )

        return {
            "model": self.model,
            "cycle": self.cycle_id,
            "expected": len(expected),
            "completed": len(completed),
            "missing": len(missing),
            "failed": len(failed),
        }


# ============================================================
# STANDALONE HELPERS
# ============================================================

def missing_products_by_region(
    *,
    completed,
    products,
    regions,
    forecast_hour,
):
    ledger = FrameCompleteness(
        model="inventory",
        cycle_id="inventory",
    )

    ledger.seed_completed(
        completed
    )

    return ledger.work_plan_for_hour(
        products=products,
        regions=regions,
        forecast_hour=forecast_hour,
    )


def flatten_work_plan(
    *,
    work_plan,
    forecast_hour,
):
    """
    Convert a regional work plan into discrete render tasks.

    Useful for persistent worker pools.
    """

    tasks = []

    for region, products in (
        work_plan.items()
    ):

        for product in products:

            tasks.append(
                (
                    str(product),
                    str(region),
                    int(forecast_hour),
                )
            )

    return tasks
