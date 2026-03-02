"""Core UI utility functions."""

from nicegui import ui


def clear_chat_until(chat_container: ui.column, target_element: ui.element) -> bool:
    """Remove target_element and all subsequent siblings from chat container.

    Used for "undo" functionality to truncate chat history.

    Args:
        chat_container: The parent ui.column containing chat messages
        target_element: The element starting the range to remove

    Returns:
        True if successful, False if target_element not found
    """
    try:
        # chat_messages is a ui.column. Its children are in .default_slot.children
        # We urge caution accessing internal slots, but it's the standard way in NiceGUI 1.x
        children = chat_container.default_slot.children
        index = children.index(target_element)
        to_remove = children[index:]
        for element in to_remove:
            chat_container.remove(element)
        return True
    except (ValueError, Exception):
        return False


from datetime import datetime, timedelta

def format_timestamp(dt: datetime | None) -> str:
    """Format datetime for chat message stamps, converting UTC to local.

    Shows relative dates:
    - Today: just time (e.g., "3:45 PM")
    - Yesterday: "Yesterday, 3:45 PM"
    - Older: "Dec 28, 3:45 PM"
    """
    if dt is None:
        return ""

    # Convert UTC to local timezone
    # Ensure dt is aware before converting if it might be naive (though usually it's from agex events which use UTC)
    if dt.tzinfo is None:
        # If naive, assume local or UTC? Agex events are usually UTC aware.
        # But let's just trigger .astimezone() which handles aware->local. 
        # If naive, it assumes local system time, which might be wrong if it was meant to be UTC.
        # Agex events use datetime.now(timezone.utc), so they are aware.
        pass

    local_dt = dt.astimezone()
    now = datetime.now().astimezone()
    today = now.date()
    msg_date = local_dt.date()

    time_str = local_dt.strftime("%-I:%M %p")
    time_str_with_sec = local_dt.strftime("%-I:%M:%S %p")

    if msg_date == today:
        return time_str_with_sec

    # Check if yesterday using timedelta for month boundaries
    yesterday = today - timedelta(days=1)
    if msg_date == yesterday:
        return f"Yesterday, {time_str}"

    date_str = local_dt.strftime("%b %-d")
    date_str = local_dt.strftime("%b %-d")
    return f"{date_str}, {time_str}"


def parse_timestamp(ts_str: str | None) -> datetime | None:
    """Parse an ISO 8601 timestamp string into a datetime object.

    Handles standard ISO formats and falls back gracefully.
    """
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str)
    except (ValueError, TypeError):
        return None
