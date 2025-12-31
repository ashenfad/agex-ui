"""Reusable chat interface template.

Provides a standard chat UI layout that can be customized via configuration,
including dark mode support.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Awaitable, Callable

if TYPE_CHECKING:
    from agex import Agent

import pandas as pd
import plotly.graph_objects as go
from nicegui import ui

from agex_ui.core.history import restore_chat_history
from agex_ui.core.responses import Response
from agex_ui.core.theme import ThemeManager
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
    dark_mode: bool = True  # Start in dark mode by default


def create_chat_interface(
    agent: "Agent",
    agent_task: Callable[..., Awaitable[Response | str | pd.DataFrame | go.Figure]],
    session: str = "default",
    config: ChatInterfaceConfig | None = None,
    turn_config: TurnConfig | None = None,
) -> tuple[ui.column, ui.input, ThemeManager]:
    """Create a standard chat interface with proper layout and dark mode support.

    Args:
        agent: Agent instance for accessing state and metadata
        agent_task: Agent task function that takes (prompt: str, **kwargs) and returns
                   Response | str | pd.DataFrame | go.Figure. The function should accept
                   on_event and on_token callbacks as keyword arguments.
        session: Session identifier for state management (default: "default")
        config: Chat interface configuration (uses defaults if None)
        turn_config: Turn execution configuration (uses defaults if None)

    Returns:
        (chat_messages, chat_input, theme_manager) - The main UI components and theme manager

    Example:
        >>> from agex_ui.templates import create_chat_interface
        >>> from my_agent import agent, handle_prompt
        >>>
        >>> chat_messages, chat_input, theme = create_chat_interface(
        ...     agent=agent,
        ...     agent_task=handle_prompt,
        ...     config=ChatInterfaceConfig(title="My App", dark_mode=True),
        ... )
    """
    config = config or ChatInterfaceConfig()
    turn_config = turn_config or TurnConfig()

    # Initialize theme manager and apply CSS
    theme_manager = ThemeManager(dark_mode=config.dark_mode)
    theme_manager.apply()

    # Configure main window - use CSS variables for theming
    ui.query("body").style(
        "background-color: var(--bg-primary); display: flex; flex-direction: column; "
        "align-items: center; height: 100vh; margin: 0;"
    )
    ui.page_title(config.page_title)

    # Header with theme toggle
    with (
        ui.header(elevated=False)
        .style(f"background-color: {config.header_bg_color};")
        .classes("items-center justify-between")
    ):
        ui.label(config.title).classes("text-2xl")

        # Spacer to push toggle to the right
        ui.element("div").classes("flex-grow")

        # Dark mode toggle button
        theme_manager.create_toggle_button()

    # Main content area
    with (
        ui.column()
        .classes("w-full h-full p-4")
        .style(f"flex-grow: 1; width: {config.max_width};")
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
            chat_input = ui.input(placeholder="Type your request...").classes(
                "flex-grow"
            )

    # Handler for chat input
    async def handle_turn():
        """Handle turn execution (start or stop)."""
        # If running, treat as stop button
        if chat_input.props.get("disable"):
            # This relies on the agent task object having a .cancel() method
            # which is true for agex.Task objects
            if hasattr(agent_task, "cancel"):
                agent_task.cancel(session=session)
                ui.notify("Cancelling task...", type="warning")
            return

        # Otherwise treat as send
        if not chat_input.value.strip():
            return

        # Update UI state to "running"
        chat_input.disable()
        send_button.props("icon=stop color=negative")
        send_button.tooltip("Stop generation")

        try:
            await run_agent_turn(
                chat_messages=chat_messages,
                chat_input=chat_input,
                agent=agent,
                agent_task=agent_task,
                prompt=chat_input.value,
                session=session,
                config=turn_config,
                dark_mode=theme_manager.dark_mode,
            )
        finally:
            # Reset UI state to "ready"
            chat_input.enable()
            send_button.props("icon=send color=primary")
            send_button.tooltip("Send message")
            # Focus back on input
            chat_input.run_method("focus")

    # Add send/stop button next to input
    with chat_input.parent_slot:  # pyright: ignore
        send_button = (
            ui.button(icon="send", on_click=handle_turn)
            .props("round flat color=primary")
            .classes("ml-2")
            .tooltip("Send message")
        )

    # Bind enter key to same handler
    chat_input.on("keydown.enter", handle_turn)

    # Restore chat history from state events
    restore_chat_history(
        chat_messages=chat_messages,
        agent=agent,
        session=session,
        dark_mode=theme_manager.dark_mode,
        collapse_actions=turn_config.collapse_agent_activity,
    )

    # Scroll to bottom after history loads (with delay for DOM to update)
    ui.timer(
        0.2,
        lambda: ui.run_javascript(
            "document.getElementById('chat-messages-container').scrollTop = 999999"
        ),
        once=True,
    )

    return chat_messages, chat_input, theme_manager
