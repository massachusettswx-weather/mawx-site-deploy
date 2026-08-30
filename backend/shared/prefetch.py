from concurrent.futures import (
    ThreadPoolExecutor,
)


class ForecastHourPrefetcher:
    """
    Keep at most one forecast-hour download running ahead of
    the processing loop.

    The processing loop itself remains strictly ordered:

        f003 -> f006 -> f009 -> ...

    Only network/download work for the NEXT forecast hour is
    overlapped with plotting/upload work for the CURRENT hour.

    This intentionally uses a thread rather than another
    process because downloads are primarily I/O-bound and the
    plotting system already manages its own worker processes.
    """

    def __init__(
        self,
        download_function,
    ):
        self.download_function = (
            download_function
        )

        self.executor = (
            ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix=(
                    "forecast-download"
                ),
            )
        )

        self.future = None
        self.future_hour = None

    def start(
        self,
        forecast_hour,
    ):
        """
        Begin downloading forecast_hour in the background.
        """

        if self.future is not None:
            raise RuntimeError(
                "A forecast-hour download is already pending."
            )

        self.future_hour = (
            forecast_hour
        )

        self.future = (
            self.executor.submit(
                self.download_function,
                forecast_hour,
            )
        )

    def get(
        self,
        forecast_hour,
    ):
        """
        Wait for and return the previously prefetched hour.
        """

        if self.future is None:
            raise RuntimeError(
                "No forecast-hour download is pending."
            )

        if (
            self.future_hour
            !=
            forecast_hour
        ):
            raise RuntimeError(
                (
                    "Prefetch order mismatch: "
                    f"expected f{forecast_hour:03d}, "
                    f"but pending download is "
                    f"f{self.future_hour:03d}."
                )
            )

        future = self.future

        self.future = None
        self.future_hour = None

        return future.result()

    def cancel_pending(
        self,
    ):
        """
        Cancel a queued download if it has not started.

        A download already running in a Python thread cannot
        safely be forcibly terminated, so shutdown waits for it
        to leave the downloader normally.
        """

        if self.future is not None:
            self.future.cancel()

    def close(
        self,
    ):
        self.cancel_pending()

        self.executor.shutdown(
            wait=True,
            cancel_futures=True,
        )

        self.future = None
        self.future_hour = None

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
