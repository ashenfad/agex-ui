"""User action bubble rendering with revert support."""

from typing import TYPE_CHECKING, Callable

from nicegui import ui

if TYPE_CHECKING:
    from agex import Agent

from agex.state import Staged
from agex_ui.core.turn import get_timestamp
from agex_ui.core.utils import clear_chat_until


async def render_user_action_bubble(
    chat_messages: ui.column,
    markdown_content: str,
    agent: "Agent",
    namespace: str,
    revert_commit: str | None = None,
    refresh_file_list_callback: Callable[[], None] | None = None,
    refresh_session_list_callback: Callable[[], None] | None = None,
):
    """Render a user action bubble with optional revert button.

    Used for file uploads, deletions, and other user-initiated state changes
    that should appear in the chat history with undo capability.
    """
    state = agent.state(namespace)

    with chat_messages:
        # Use same wrapper as _render_user_message for consistent positioning
        message_container = ui.column().classes("self-end relative group max-w-full")
        with message_container:
            with ui.chat_message(
                name="You",
                sent=True,
                avatar="assets/human.png",
                stamp=get_timestamp(),
            ):
                ui.markdown(markdown_content)

        # Add revert button for Staged state
        if isinstance(state, Staged) and revert_commit:

            async def undo_to_commit():
                """Reset state to this commit and remove subsequent UI elements."""
                if not state.reset_to(revert_commit):
                    ui.notify("Failed to reset state", type="negative")
                    return

                # Remove this message container and everything after it
                if not clear_chat_until(chat_messages, message_container):
                    ui.notify(
                        "UI Clean error: Message container not found", type="warning"
                    )

                # Refresh file list since state changed
                if refresh_file_list_callback:
                    refresh_file_list_callback()

                if refresh_session_list_callback:
                    refresh_session_list_callback()

            with message_container:
                ui.button(icon="undo", on_click=undo_to_commit).props(
                    "round flat size=xs color=grey-4"
                ).classes(
                    "absolute bottom-2 right-14 opacity-0 group-hover:opacity-100 "
                    "transition-opacity bg-white shadow-sm"
                ).tooltip(
                    "Undo to this point"
                )

    # Auto-scroll (simple js scroll)
    await ui.run_javascript(
        "document.getElementById('chat-messages-container').scrollTop = 999999"
    )
