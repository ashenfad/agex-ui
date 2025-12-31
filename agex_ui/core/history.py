"""Chat history restoration from agex state events.

This module reconstructs the chat UI from historic events stored in agex state.
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agex import Agent

from agex import events
from agex.agent.events import (
    ActionEvent,
    CancelledEvent,
    ClarifyEvent,
    FailEvent,
    SuccessEvent,
    TaskStartEvent,
)
from agex.state import Versioned
from nicegui import ui

from agex_ui.core.renderers import EventRenderer, ResponseRenderer
from agex_ui.core.utils import clear_chat_until


def _format_timestamp(dt: datetime | None) -> str:
    """Format datetime for chat message stamps, converting UTC to local.

    Shows relative dates:
    - Today: just time (e.g., "3:45 PM")
    - Yesterday: "Yesterday, 3:45 PM"
    - Older: "Dec 28, 3:45 PM"
    """
    if dt is None:
        return ""

    # Convert UTC to local timezone
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
    return f"{date_str}, {time_str}"


def _render_user_message(
    chat_messages: ui.column,
    message: str,
    timestamp: datetime | None,
    state,
    revert_commit: str | None,
) -> None:
    """Render a user chat message with optional revert button."""
    with chat_messages:
        message_container = ui.column().classes("self-end relative group w-auto")

        with message_container:
            ui.chat_message(
                message,
                sent=True,
                name="You",
                avatar="assets/human.png",
                stamp=_format_timestamp(timestamp),
            )

        # Add revert button for Versioned state
        if isinstance(state, Versioned) and revert_commit:

            async def undo_to_commit():
                """Revert state to this commit and remove subsequent UI elements."""
                if not state.revert_to(revert_commit):
                    ui.notify("Failed to revert state", type="negative")
                    return

                # Remove this message container and everything after it
                if not clear_chat_until(chat_messages, message_container):
                    ui.notify(
                        "UI Clean error: Message container not found", type="warning"
                    )

            with message_container:
                ui.button(icon="undo", on_click=undo_to_commit).props(
                    "round flat size=xs color=grey-4"
                ).classes(
                    "absolute bottom-2 right-14 opacity-0 group-hover:opacity-100 "
                    "transition-opacity bg-white shadow-sm"
                ).tooltip(
                    "Undo to this point"
                )


def _render_action_events(
    chat_messages: ui.column,
    action_events: list[ActionEvent],
    event_renderer: EventRenderer,
    collapsed: bool = True,
) -> None:
    """Render ActionEvents in a collapsed expansion panel."""
    if not action_events:
        return

    # Build label with action count and last action title
    last_action = action_events[-1]
    last_title = getattr(last_action, "title", "") or ""
    if last_title:
        label = f"Activity — {last_title}"
    else:
        label = "Activity"

    with chat_messages:
        expansion = ui.expansion(label, icon="psychology").classes(
            "w-full border border-gray-200 rounded-lg text-gray-500"
        )
        expansion.value = not collapsed

        with expansion:
            for action in action_events:
                html_content = event_renderer.render_action_event(
                    agent_name=action.agent_name,
                    full_namespace=action.full_namespace,
                    timestamp=action.timestamp,
                    title=action.title if hasattr(action, "title") else "",
                    thinking=action.thinking,
                    code=action.code,
                    dark_mode=event_renderer.dark_mode,
                )
                ui.html(html_content, sanitize=False).classes("w-full p-0 my-0")


def _render_agent_response(
    chat_messages: ui.column,
    result,
    timestamp: datetime | None,
    agent_name: str,
    response_renderer: ResponseRenderer,
    is_error: bool = False,
) -> None:
    """Render agent response message."""
    with chat_messages:
        bg_color = "red-2" if is_error else "blue-2"
        with (
            ui.chat_message(
                name=agent_name,
                sent=False,
                avatar="assets/robot.png",
            )
            .classes("w-full")
            .props(f'bg-color={bg_color} stamp="{_format_timestamp(timestamp)}"')
        ):
            response_renderer.render_response(result)


def restore_chat_history(
    chat_messages: ui.column,
    agent: "Agent",
    session: str = "default",
    dark_mode: bool = False,
    collapse_actions: bool = True,
) -> bool:
    """Restore chat history from agent state events.

    Reconstructs the chat UI from historic events stored in the agent's state.
    This allows users to see their previous conversations when the app loads.

    Args:
        chat_messages: Chat messages container
        agent: Agent instance for accessing state
        session: Session identifier (default: "default")
        dark_mode: Whether dark mode is enabled
        collapse_actions: Whether to collapse ActionEvent expansions (default: True)

    Returns:
        True if history was restored, False if no history exists
    """
    # Get state and events
    state = agent.state(session)
    if state is None:
        return False

    all_events = events(state)
    if not all_events:
        return False

    # Filter out setup events
    main_events = [e for e in all_events if e.source != "setup"]
    if not main_events:
        return False

    # Initialize renderers
    response_renderer = ResponseRenderer(dark_mode=dark_mode)
    event_renderer = EventRenderer(dark_mode=dark_mode)
    agent_name = agent.name

    # Group events by task (TaskStartEvent → completion event)
    current_task_start: TaskStartEvent | None = None
    current_actions: list[ActionEvent] = []
    revert_commit: str | None = None

    for event in main_events:
        if isinstance(event, TaskStartEvent):
            # New task starting - render previous task if exists
            if current_task_start is not None:
                # Render user message - prompt is in inputs dict
                prompt = current_task_start.inputs.get("prompt", "")
                _render_user_message(
                    chat_messages,
                    prompt,
                    current_task_start.timestamp,
                    state,
                    revert_commit,
                )
                # Render action events
                _render_action_events(
                    chat_messages, current_actions, event_renderer, collapse_actions
                )
                # Previous task had no completion event - show pending
                _render_agent_response(
                    chat_messages,
                    "(Task in progress or interrupted)",
                    None,
                    agent_name,
                    response_renderer,
                    is_error=True,
                )

            # Start new task group
            current_task_start = event
            current_actions = []
            revert_commit = event.commit_hash

        elif isinstance(event, ActionEvent):
            current_actions.append(event)

        elif isinstance(event, (SuccessEvent, FailEvent, ClarifyEvent, CancelledEvent)):
            if current_task_start is not None:
                # Determine message and style based on event type
                message = ""
                is_error = False

                if isinstance(event, SuccessEvent):
                    message = event.result
                elif isinstance(event, (FailEvent, ClarifyEvent)):
                    message = event.message
                    is_error = isinstance(event, FailEvent)
                elif isinstance(event, CancelledEvent):
                    message = "Task was cancelled."
                    is_error = True

                # Render complete task interaction
                prompt = current_task_start.inputs.get("prompt", "")
                _render_user_message(
                    chat_messages,
                    prompt,
                    current_task_start.timestamp,
                    state,
                    revert_commit,
                )
                _render_action_events(
                    chat_messages, current_actions, event_renderer, collapse_actions
                )
                _render_agent_response(
                    chat_messages,
                    message,
                    event.timestamp,
                    agent_name,
                    response_renderer,
                    is_error=is_error,
                )

            # Reset for next task
            current_task_start = None
            current_actions = []
            revert_commit = None

    # Handle case where last task is still in progress
    if current_task_start is not None:
        prompt = current_task_start.inputs.get("prompt", "")
        _render_user_message(
            chat_messages,
            prompt,
            current_task_start.timestamp,
            state,
            revert_commit,
        )
        if current_actions:
            _render_action_events(
                chat_messages, current_actions, event_renderer, collapse_actions
            )

    return True
