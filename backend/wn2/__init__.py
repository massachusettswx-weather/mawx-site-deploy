"""
Google DeepMind WeatherNext 2 atmospheric forecast pipeline.
"""

from .download.client import WeatherNext2Client

__all__ = [
    "WeatherNext2Client",
]
