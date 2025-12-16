"""Turn orchestration for agent execution.

This module provides the main entry point for running agent turns,
coordinating between user input, agent execution, event handling,
and response rendering.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

import pandas as pd
import plotly.graph_objects as go
from agex import TaskClarify, TaskFail, TaskTimeout
from nicegui import ui

from agex_ui.core.events import EventHandler
from agex_ui.core.renderers import EventRenderer, ResponseRenderer
from agex_ui.core.responses import Response


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
    agent_task: Callable[..., Response | str | pd.DataFrame | go.Figure],
    prompt: str,
    state: Any = None,
    config: TurnConfig | None = None,
    response_renderer: ResponseRenderer | None = None,
    event_renderer: EventRenderer | None = None,
    agent_name: str = "Agent",
):
    """Execute one agent turn with configurable rendering.
    
    The core framework is agent-agnostic - it accepts any callable that:
    - Takes a prompt string as first positional arg
    - Accepts on_event and on_token callbacks (as keyword args)
    - Optionally accepts state (as keyword arg)
    - Returns Response | str | pd.DataFrame | go.Figure (or raises TaskClarify/TaskFail/TaskTimeout)
    
    Examples define their own agents and pass the task function to this orchestrator.
    
    Args:
        chat_messages: Chat messages container
        chat_input: Chat input field
        agent_task: Agent task function with signature (prompt: str, **kwargs) -> Response | str | ...
        prompt: User prompt string
        state: Optional state object to pass to agent
        config: Turn configuration (uses defaults if None)
        response_renderer: Custom response renderer (uses default if None)
        event_renderer: Custom event renderer (uses default if None)
        agent_name: Agent name for display purposes
        
    This function coordinates:
    1. User message display
    2. Agent activity expansion setup
    3. Event/token streaming
    4. Response rendering
    5. Auto-scrolling
    """
    config = config or TurnConfig()
    response_renderer = response_renderer or ResponseRenderer()
    event_renderer = event_renderer or EventRenderer()

    # Display user message
    with chat_messages:
        ui.chat_message(
            prompt,
            sent=True,
            name="You",
            avatar="assets/human.png",
            stamp=get_timestamp(),
        ).classes("self-end")
    chat_input.value = ""  # Clear input immediately

    if config.auto_scroll:
        await scroll_chat_to_bottom(chat_messages)

    # Get the asyncio event loop for thread-safe UI updates
    loop = asyncio.get_running_loop()

    # Create agent activity expansion
    with chat_messages:
        current_expansion = ui.expansion("Agent Activity", icon="psychology").classes(
            "w-full border border-gray-200 rounded-lg text-gray-500"
        )
        current_expansion.value = not config.collapse_agent_activity

    # Create event handler
    event_handler = EventHandler(
        loop=loop,
        expansion=current_expansion,
        show_setup_events=config.show_setup_events,
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
                ui.spinner(size="sm", type="dots")

    # Run the agent task in a background thread
    task_kwargs = {
        "on_event": on_agent_event,
    }
    
    if config.enable_token_streaming:
        task_kwargs["on_token"] = on_agent_token
        
    if state is not None:
        task_kwargs["state"] = state

    try:
        result = await asyncio.to_thread(
            agent_task,
            prompt,
            **task_kwargs,
        )
    except (TaskClarify, TaskFail) as e:
        result = e.message
    except TaskTimeout:
        result = "Sorry, I got stuck. Please try again."

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
