from __future__ import annotations

import os

from concurrent.futures import (
    ProcessPoolExecutor,
    ThreadPoolExecutor,
)


# ============================================================
# MASSACHUSETTSWX SHARED EXECUTION LAYER
#
# One execution owns its worker pools.
#
# Goals:
#   - create workers once
#   - reuse them for the full model execution
#   - bounded concurrency
#   - no idle worker processes after execution
#   - shared by current and future models
# ============================================================


def get_worker_count(
    *,
    env_name="MODEL_PRODUCT_WORKERS",
    default=2,
    minimum=1,
):
    return max(
        minimum,
        int(
            os.environ.get(
                env_name,
                str(default),
            )
        ),
    )


class ModelExecutionResources:
    """
    Execution-lifetime worker resources.

    Pools are created lazily. A model that does not need a
    particular pool pays no startup cost for it.

    Examples:

        GFS / IFS / AIFS:
            resources.process_pool()

        download / upload / I/O workloads:
            resources.thread_pool()

        FNV3 / FNV3-L / WN2:
            may use either pool according to their workload.
    """

    def __init__(
        self,
        *,
        model,
        process_workers=None,
        thread_workers=None,
    ):
        self.model = str(
            model
        )

        self.process_workers = (
            process_workers
            if process_workers is not None
            else get_worker_count()
        )

        self.thread_workers = (
            thread_workers
            if thread_workers is not None
            else get_worker_count(
                env_name=(
                    "MODEL_IO_WORKERS"
                ),
                default=4,
            )
        )

        self._process_pool = None
        self._thread_pool = None

    def process_pool(
        self,
    ):
        if self._process_pool is None:

            print(
                f"{self.model}: starting "
                f"persistent process pool "
                f"({self.process_workers} workers)"
            )

            self._process_pool = (
                ProcessPoolExecutor(
                    max_workers=(
                        self.process_workers
                    )
                )
            )

        return self._process_pool

    def thread_pool(
        self,
    ):
        if self._thread_pool is None:

            print(
                f"{self.model}: starting "
                f"persistent I/O pool "
                f"({self.thread_workers} workers)"
            )

            self._thread_pool = (
                ThreadPoolExecutor(
                    max_workers=(
                        self.thread_workers
                    ),
                    thread_name_prefix=(
                        f"{self.model}-io"
                    ),
                )
            )

        return self._thread_pool

    def close(
        self,
    ):
        if self._thread_pool is not None:

            self._thread_pool.shutdown(
                wait=True,
                cancel_futures=True,
            )

            self._thread_pool = None

        if self._process_pool is not None:

            self._process_pool.shutdown(
                wait=True,
                cancel_futures=True,
            )

            self._process_pool = None

        print(
            f"{self.model}: execution "
            "resources closed"
        )

    def __enter__(
        self,
    ):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        self.close()

        return False
