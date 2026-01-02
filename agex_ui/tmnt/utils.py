"""TMNT Calendar Demo Utilities.

Helpers for loading turtle calendars and formatting events for the UI.
"""

from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from calgebra import Interval
from calgebra.ical import ICalEvent, file_to_timeline
from calgebra.mutable.memory import MemoryTimeline

# Default timezone for TMNT demo
TZ = "America/Los_Angeles"


def load_cals() -> dict[str, MemoryTimeline]:
    """Load the four turtle calendars as a dict for state initialization."""
    cals_dir = Path.home() / "data" / "cals"
    return {
        "leo": file_to_timeline(cals_dir / "leo.ics"),
        "donnie": file_to_timeline(cals_dir / "donnie.ics"),
        "mikey": file_to_timeline(cals_dir / "mikey.ics"),
        "raph": file_to_timeline(cals_dir / "raph.ics"),
    }
