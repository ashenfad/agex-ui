import logging
from collections.abc import Iterable
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd
from calgebra import Interval
from calgebra.gcsa import Event
from gcsa.google_calendar import GoogleCalendar


def user_timezone() -> str:
    """Best-effort lookup of the authenticated user's default timezone."""
    try:
        calendar = GoogleCalendar()
        settings = calendar.get_settings()
        timezone_name = getattr(settings, "timezone", None)
        if isinstance(timezone_name, str) and timezone_name:
            return timezone_name
    except Exception as exc:  # pragma: no cover - depends on local creds
        logging.getLogger(__name__).warning(
            "Unable to load Google Calendar settings; falling back to UTC: %s", exc
        )
    return "UTC"
