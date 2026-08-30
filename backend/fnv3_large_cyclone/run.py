from shared.inventory_seed import (
    build_work_plan,
    mark_complete,
)

from shared.operational_lifecycle import (
    FrontierSweep,
    OperationalCycleState,
    OperationalLifecycle,
)



# ============================================================
# PRODUCTION FNV3-L ENTRYPOINT
#
# Stable entrypoint used by Cloud Run / watcher infrastructure.
# Delegates to the existing internal implementation:
#
#     fnv3_large.run.run_fnv3_large
# ============================================================

def run_fnv3_large_cyclone_cycle(
    *args,
    **kwargs,
):
    from fnv3_large.run import (
        run_fnv3_large,
    )

    return run_fnv3_large(
        *args,
        **kwargs,
    )

