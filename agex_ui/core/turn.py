"""Turn orchestration for agent execution.

This module provides the main entry point for running agent turns,
coordinating between user input, agent execution, event handling,
and response rendering.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Awaitable, Callable

if TYPE_CHECKING:
    from agex import Agent

import pandas as pd
import plotly.graph_objects as go
from agex import TaskCancelled, TaskClarify, TaskFail, TaskTimeout
from agex.state import Versioned
from nicegui import ui

from agex_ui.core.events import EventHandler
from agex_ui.core.renderers import EventRenderer, ResponseRenderer
from agex_ui.core.responses import Response
from agex_ui.core.utils import clear_chat_until


@dataclass
class TurnConfig:
    """Configuration for agent turn execution."""

    show_setup_events: bool = False
    enable_token_streaming: bool = True
    auto_scroll: bool = True
    collapse_agent_activity: bool = True


def get_timestamp() -> str:
    """Get current timestamp formatted for chat messages."""
    return datetime.now().strftime("%-I:%M:%S %p")


async def scroll_chat_to_bottom(chat_container: ui.column):
    """Scroll the chat container to the bottom.

    Args:
        chat_container: Chat messages container element
    """
    await asyncio.sleep(0.11)  # Wait for DOM to update
    with chat_container:
        ui.run_javascript(
            "document.getElementById('chat-messages-container').scrollTop = 999999"
        )


async def run_agent_turn(
    chat_messages: ui.column,
    chat_input: ui.input,
    agent: "Agent",
    agent_task: Callable[..., Awaitable[Response | str | pd.DataFrame | go.Figure]],
    prompt: str,
    session: str = "default",
    config: TurnConfig | None = None,
    response_renderer: ResponseRenderer | None = None,
    event_renderer: EventRenderer | None = None,
    dark_mode: bool = False,
):
    """Execute one agent turn with configurable rendering.

    The core framework is agent-agnostic - it accepts any callable that:
    - Takes a prompt string as first positional arg
    - Accepts on_event and on_token callbacks (as keyword args)
    - Returns Response | str | pd.DataFrame | go.Figure (or raises TaskClarify/TaskFail/TaskTimeout)

    Examples define their own agents and pass the task function to this orchestrator.

    Args:
        chat_messages: Chat messages container
        chat_input: Chat input field
        agent: Agent instance for accessing state and metadata
        agent_task: Agent task function with signature (prompt: str, **kwargs) -> Response | str | ...
        prompt: User prompt string
        session: Session identifier for state management (default: "default")
        config: Turn configuration (uses defaults if None)
        response_renderer: Custom response renderer (uses default if None)
        event_renderer: Custom event renderer (uses default if None)
        dark_mode: Whether to use dark mode styling (default: False)

    This function coordinates:
    1. User message display
    2. Agent activity expansion setup
    3. Event/token streaming
    4. Response rendering
    5. Auto-scrolling
    """
    # Derive state and agent name from agent instance
    state = agent.state(session)
    agent_name = agent.name
    config = config or TurnConfig()
    response_renderer = response_renderer or ResponseRenderer(dark_mode=dark_mode)
    event_renderer = event_renderer or EventRenderer(dark_mode=dark_mode)

    # Display user message
    with chat_messages:
        # Wrap message in a container for proper button positioning
        message_container = ui.column().classes("self-end relative group w-auto")

        with message_container:
            ui.chat_message(
                prompt,
                sent=True,
                name="You",
                avatar="assets/human.png",
                stamp=get_timestamp(),
            )

    chat_input.value = ""  # Clear input immediately

    # Capture state for potential revert (only if Versioned)
    revert_commit: str | None = None
    if isinstance(state, Versioned):
        revert_commit = state.current_commit

    async def undo_turn():
        """Revert state to before this turn and remove UI elements."""
        if isinstance(state, Versioned) and revert_commit:
            if not state.revert_to(revert_commit):
                ui.notify("Failed to revert state", type="negative")
                return

        # Restore input
        chat_input.value = prompt

        # Truncate UI
        if not clear_chat_until(chat_messages, message_container):
            ui.notify("UI Clean error: Message container not found", type="warning")

    # Add hidden undo button overlaying the user message (visible on hover)
    if isinstance(state, Versioned) and revert_commit:
        with message_container:
            # Absolute positioning relative to the message container
            # right-14 offsets for the avatar width (~56px) to position over the bubble edge
            ui.button(icon="undo", on_click=undo_turn).props(
                "round flat size=xs color=grey-4"
            ).classes(
                "absolute bottom-2 right-14 opacity-0 group-hover:opacity-100 transition-opacity bg-white shadow-sm"
            ).tooltip(
                "Undo this turn"
            )

    if config.auto_scroll:
        await scroll_chat_to_bottom(chat_messages)

    # Get the asyncio event loop for thread-safe UI updates
    loop = asyncio.get_running_loop()

    # Create agent activity expansion
    with chat_messages:
        current_expansion = ui.expansion("Activity", icon="psychology").classes(
            "w-full border border-gray-200 rounded-lg text-gray-500"
        )
        current_expansion.value = not config.collapse_agent_activity

    # Create event handler
    event_handler = EventHandler(
        loop=loop,
        expansion=current_expansion,
        show_setup_events=config.show_setup_events,
        dark_mode=dark_mode,
    )

    # Event callback wrapper
    def on_agent_event(evt):
        event_handler.handle_event(evt, event_renderer)

    # Token callback wrapper
    def on_agent_token(token):
        if config.enable_token_streaming:
            event_handler.handle_token(token, agent_name=agent_name)

    # Create agent response message with spinner
    with chat_messages:
        with (
            ui.chat_message(name=agent_name, sent=False, avatar="assets/robot.png")
            .classes("w-full")
            .props("bg-color=blue-2") as agent_message
        ):
            with ui.row().classes("items-center"):
                spinner = ui.spinner(size="sm", type="dots")
                # In dark mode, agent bubble is a medium blue (#5894c8)
                # We need a dark spinner (#24292e) to match the text
                if dark_mode:
                    spinner.props('color="dark"')
                else:
                    spinner.props('color="primary"')

    # Run the agent task in a background thread
    task_kwargs = {
        "on_event": on_agent_event,
    }

    if config.enable_token_streaming:
        task_kwargs["on_token"] = on_agent_token

    try:
        result = await agent_task(
            prompt,
            **task_kwargs,
        )
    except (TaskClarify, TaskFail) as e:
        result = e.message
    except TaskTimeout:
        result = "Sorry, I got stuck. Please try again."
    except TaskCancelled:
        result = "Task cancelled by user."
    except Exception as e:
        import traceback

        traceback.print_exc()
        result = f"An internal error occurred: {str(e)}"

    # Replace spinner with actual content
    with agent_message:
        agent_message.clear()
        response_renderer.render_response(result)

    # Set timestamp
    agent_message.props(f'stamp="{get_timestamp()}"')
    agent_message.update()

    # Auto-scroll for agent responses
    if config.auto_scroll:
        await scroll_chat_to_bottom(chat_messages)
