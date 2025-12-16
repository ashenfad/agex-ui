"""Reusable chat interface template.

Provides a standard chat UI layout that can be customized via configuration.
"""

from dataclasses import dataclass
from typing import Any, Callable

import pandas as pd
import plotly.graph_objects as go
from nicegui import ui

from agex_ui.core.responses import Response
from agex_ui.core.turn import TurnConfig, get_timestamp, run_agent_turn


@dataclass
class ChatInterfaceConfig:
    """Configuration for chat interface appearance and behavior."""
    
    header_bg_color: str = "#5894c8"
    title: str = "Agex-UI"
    page_title: str = "Agex-UI"
    max_width: str = "900px"
    greeting: str = "Hello! How can I help you today?"
    robot_avatar: str = "assets/robot.png"
    human_avatar: str = "assets/human.png"
    agent_name: str = "Agex"


def create_chat_interface(
    agent_task: Callable[..., Response | str | pd.DataFrame | go.Figure],
    state: Any = None,
    config: ChatInterfaceConfig | None = None,
    turn_config: TurnConfig | None = None,
) -> tuple[ui.column, ui.input]:
    """Create a standard chat interface with proper layout.
    
    Args:
        agent_task: Agent task function that takes (prompt: str, **kwargs) and returns
                   Response | str | pd.DataFrame | go.Figure. The function should accept
                   on_event, on_token, and state as keyword arguments.
        state: Optional state object to pass to agent task
        config: Chat interface configuration (uses defaults if None)
        turn_config: Turn execution configuration (uses defaults if None)
        
    Returns:
        (chat_messages, chat_input) - The main UI components
        
    Example:
        >>> from agex_ui.templates import create_chat_interface
        >>> from my_agent import handle_prompt, state
        >>> 
        >>> chat_messages, chat_input = create_chat_interface(
        ...     agent_task=handle_prompt,
        ...     state=state,
        ...     config=ChatInterfaceConfig(title="My App"),
        ... )
    """
    config = config or ChatInterfaceConfig()
    turn_config = turn_config or TurnConfig()

    # Configure main window
    ui.query("body").style(
        "background-color: #fcfcfc; display: flex; flex-direction: column; "
        "align-items: center; height: 100vh; margin: 0;"
    )
    ui.page_title(config.page_title)

    # Header
    with (
        ui.header(elevated=False)
        .style(f"background-color: {config.header_bg_color};")
        .classes("items-center justify-between")
    ):
        ui.label(config.title).classes("text-2xl")

    # Main content area
    with ui.column().classes("w-full h-full p-4").style(
        f"flex-grow: 1; width: {config.max_width};"
    ):
        # Chat messages area
        chat_messages = (
            ui.column()
            .classes("w-full overflow-auto p-4")
            .style("height: 75vh; max-height: 75vh;")
            .props("id=chat-messages-container")
        )
        
        with chat_messages:
            ui.chat_message(
                config.greeting,
                sent=False,
                name=config.agent_name,
                avatar=config.robot_avatar,
                stamp=get_timestamp(),
            ).classes("w-full").props("bg-color=blue-2")

        # Chat input area at bottom
        with ui.row().classes("w-full items-center p-2 border-t"):
            chat_input = ui.input(
                placeholder="Type your request..."
            ).classes("flex-grow")

    # Handler for chat input
    async def handle_chat_input():
        """Handler for when user presses enter in the chat input."""
        if not chat_input.value.strip():
            return
            
        await run_agent_turn(
            chat_messages=chat_messages,
            chat_input=chat_input,
            agent_task=agent_task,
            prompt=chat_input.value,
            state=state,
            config=turn_config,
            agent_name=config.agent_name,
        )

    chat_input.on("keydown.enter", handle_chat_input)

    return chat_messages, chat_input
