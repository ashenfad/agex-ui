from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import datetime, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd
from calgebra.gcsa import Event
from gcsa.google_calendar import GoogleCalendar


def _resolve_zone(name: str | None) -> ZoneInfo:
    """Resolve a timezone name into a ZoneInfo object, defaulting to UTC."""
    target = name or user_timezone()
    try:
        return ZoneInfo(target)
    except ZoneInfoNotFoundError:
        logging.getLogger(__name__).warning(
            "Unknown timezone '%s', falling back to UTC", target
        )
        return ZoneInfo("UTC")


def _format_calendar_name(calendar_id: str | None) -> str:
    if not calendar_id:
        return "unknown"
    if calendar_id.endswith("@gmail.com"):
        return calendar_id[:-10]
    return calendar_id


def _format_start(ts: int | None, zone: ZoneInfo) -> str:
    if ts is None:
        return "—"
    dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(zone)
    return dt.strftime("%Y-%m-%d %I:%M %p")


def _format_duration(start: int | None, end: int | None) -> str:
    if start is None or end is None:
        return "—"
    seconds = max(0, end - start + 1)
    units = [("d", 86_400), ("h", 3_600), ("m", 60)]
    for suffix, divisor in units:
        if seconds >= divisor:
            value = seconds / divisor
            return f"{value:.1f}".rstrip("0").rstrip(".") + suffix
    return f"{seconds}s"


@lru_cache(maxsize=1)
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


def events_to_dataframe(
    events: Iterable[Event],
    *,
    timezone_name: str | None = None,
) -> pd.DataFrame:
    """Convert Events into a standardized table for the UI."""
    zone = _resolve_zone(timezone_name)
    rows: list[dict[str, str]] = []

    for event in events:
        start = getattr(event, "start", None)
        end = getattr(event, "end", None)
        rows.append(
            {
                "calendar": _format_calendar_name(getattr(event, "calendar_id", None)),
                "summary": getattr(event, "summary", ""),
                "start": _format_start(start, zone),
                "duration": _format_duration(start, end),
            }
        )

    return pd.DataFrame(rows)
