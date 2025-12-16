import logging
from collections.abc import Iterable
from datetime import datetime, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd
from calgebra import Interval
from calgebra.gcsa import Event, calendars
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


def _format_cal_name(calendar_id: str | None) -> str:
    if not calendar_id:
        return "unknown"
    if "@" in calendar_id:
        return calendar_id.split("@", 1)[0]
    return calendar_id


def _format_day(ts: int | None, zone: ZoneInfo, is_all_day: bool = False) -> str:
    """
    Format the day portion of a datetime with a hybrid relative approach:
    - 'Today' or 'Tomorrow' for nearby dates
    - 'Tue, Dec 7' for current year (day-name first)
    - 'Tue, Dec 7, 2025' for other years
    """
    if ts is None:
        return "—"
    
    # Determine which datetime to use based on event type
    if is_all_day:
        # For all-day events, use UTC to avoid timezone shifts
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    else:
        # For timed events, convert to user's timezone
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(zone)
    
    # Get today's date in the same timezone for comparison
    now = datetime.now(tz=zone if not is_all_day else timezone.utc)
    today = now.date()
    event_date = dt.date()
    
    # Calculate day difference
    day_diff = (event_date - today).days
    
    # Relative dates for today and tomorrow
    if day_diff == 0:
        return "Today"
    elif day_diff == 1:
        return "Tomorrow"
    
    # Context-aware year display
    if event_date.year == today.year:
        # Current year: "Tue, Dec 7"
        return dt.strftime("%a, %b %-d")
    else:
        # Other years: "Tue, Dec 7, 2025"
        return dt.strftime("%a, %b %-d, %Y")


def _format_time(ts: int | None, zone: ZoneInfo, is_all_day: bool = False) -> str:
    """Format the time portion of a datetime (e.g., '8:30am' or 'All day')."""
    if ts is None:
        return "—"
    if is_all_day:
        return "All day"
    # For timed events, convert to user's timezone
    dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(zone)
    return dt.strftime("%-I:%M%p").lower()


def _is_all_day_interval(start: int | None, end: int | None, zone: ZoneInfo) -> bool:
    """
    Check if an interval represents an all-day event.
    An interval is all-day if both start and end are at midnight in the given timezone.
    """
    if start is None or end is None:
        return False
    # Convert timestamps to datetimes in the specified timezone
    start_dt = datetime.fromtimestamp(start, tz=timezone.utc).astimezone(zone)
    end_dt = datetime.fromtimestamp(end, tz=timezone.utc).astimezone(zone)
    # Check if both are at midnight (hour=0, minute=0, second=0)
    return (
        start_dt.hour == 0
        and start_dt.minute == 0
        and start_dt.second == 0
        and end_dt.hour == 0
        and end_dt.minute == 0
        and end_dt.second == 0
    )


def _format_duration(start: int | None, end: int | None) -> str:
    if start is None or end is None:
        return "—"
    # calgebra uses exclusive end semantics [start, end), so duration is end - start
    seconds = max(0, end - start)
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
    timezone_name: str | None = None,
) -> pd.DataFrame:
    """
    Convert Events into a standardized dataframe for the UI. Defaults to the user's
    timezone.

    The resulting dataframe will have the following columns:
    - calendar: The name of the calendar the event belongs to
    - summary: The summary of the event
    - day: The day of the event
    - time: The time of the event
    - duration: The duration of the event (as a string)
    """
    zone = _resolve_zone(timezone_name)
    return pd.DataFrame(
        [
            {
                "calendar": _format_cal_name(event.calendar_summary),
                "summary": event.summary,
                "day": _format_day(
                    event.start, zone, is_all_day=event.is_all_day or False
                ),
                "time": _format_time(
                    event.start, zone, is_all_day=event.is_all_day or False
                ),
                "duration": _format_duration(event.start, event.end),
            }
            for event in events
        ]
    )


def intervals_to_dataframe(
    ivls: Iterable[Interval],
    timezone_name: str | None = None,
) -> pd.DataFrame:
    """
    Convert Intervals into a standardized dataframe for the UI. Defaults to the user's
    timezone. Automatically detects all-day events (intervals from midnight to midnight).

    The resulting dataframe will have the following columns:
    - day: The day of the interval
    - time: The time of the interval
    - duration: The duration of the interval (as a string)    
    """
    zone = _resolve_zone(timezone_name)
    return pd.DataFrame(
        [
            {
                "day": _format_day(
                    ivl.start,
                    zone,
                    is_all_day=_is_all_day_interval(ivl.start, ivl.end, zone),
                ),
                "time": _format_time(
                    ivl.start,
                    zone,
                    is_all_day=_is_all_day_interval(ivl.start, ivl.end, zone),
                ),
                "duration": _format_duration(ivl.start, ivl.end),
            }
            for ivl in ivls
        ]
    )

