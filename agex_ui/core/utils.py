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
