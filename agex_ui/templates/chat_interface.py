"""Reusable chat interface template."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Awaitable, Callable

if TYPE_CHECKING:
    from agex import Agent

import pandas as pd
import plotly.graph_objects as go
from nicegui import app, ui

from agex.state import Staged

from agex_ui.core.file_manager import setup_file_manager
from agex_ui.core.history import (
    ChatHistoryState,
    remove_history_sentinel,
    render_history_chunk,
    restore_chat_history,
    reveal_prepended_chunk,
    setup_history_intersection_observer,
    show_history_start_indicator,
)
from agex_ui.core.responses import Response
from agex_ui.core.session_panel import setup_session_panel
from agex_ui.core.sessions import CURRENT_BRANCH_KEY, SESSION_UPDATED_KEY, generate_branch_name
from agex_ui.core.theme import ThemeManager
from agex_ui.core.turn import TurnConfig, get_timestamp, run_agent_turn


@dataclass
class ChatInterfaceConfig:
    """Configuration for chat interface appearance and behavior."""

    header_bg_color: str = "#5894c8"
    title: str = "Agex-UI"
    page_title: str = "Agex-UI"
    max_width: str = "900px"
    min_width: str = "300px"
    greeting: str = "Hello! How can I help you today?"
    robot_avatar: str = "assets/robot.png"
    human_avatar: str = "assets/human.png"
    dark_mode: bool = True

    # App preview settings (Workshop)
    enable_app_preview: bool = False
    app_preview_path: str = "app/main.py"  # VFS path to watch


def create_chat_interface(
    agent: "Agent",
    agent_task: Callable[..., Awaitable[Response | str | pd.DataFrame | go.Figure]],
    config: ChatInterfaceConfig | None = None,
    turn_config: TurnConfig | None = None,
    initial_branch: str | None = None,
    namespace: str = "default",
) -> tuple[ui.column, ui.input, ThemeManager]:
    """Create a standard chat interface with proper layout and dark mode support."""
    config = config or ChatInterfaceConfig()
    turn_config = turn_config or TurnConfig()

    # --- Require Staged State ---
    _validate_versioned_state(agent)

    # --- Session Management (branch-based) ---
    session_ctx = _init_session_context(agent, namespace, initial_branch)

    # --- Theme ---
    theme_manager = ThemeManager(dark_mode=config.dark_mode)
    theme_manager.apply()
    # Define --header-height CSS variable so content areas can use calc(100vh - var(--header-height))
    ui.add_head_html("<style>:root { --header-height: 48px; }</style>")
    ui.query("body").style("background-color: var(--bg-primary); margin: 0;")
    ui.query('.nicegui-content').style('padding-top: 0px; padding-bottom: 0px; padding-left: 1px; padding-right: 1px;')
    ui.page_title(agent.name)

    # --- Preview Setup (if enabled) ---
    refresh_preview = None
    if config.enable_app_preview:
        from agex_ui.core.preview import (
            create_preview_panel,
            register_preview_route,
        )

        # Register preview route once per app startup
        if not hasattr(app, "_preview_route_registered"):
            register_preview_route(agent, namespace)
            app._preview_route_registered = True

    # --- Build Layout ---
    header_elements = _build_header(config, theme_manager)

    # Create a callback holder for file refresh (needed by preview panel before file_manager exists)
    file_refresh_holder = {"fn": lambda: None}

    def refresh_file_list():
        file_refresh_holder["fn"]()

    chat_area = _build_chat_area(
        config=config,
        session_ctx=session_ctx,
        agent=agent,
        refresh_file_list=refresh_file_list,
    )
    chat_messages = chat_area.chat_messages
    chat_input = chat_area.chat_input
    refresh_preview = chat_area.refresh_preview

    # --- Setup Drawers ---
    session_panel = setup_session_panel(
        agent,
        session_ctx.namespace,
        session_ctx.branch,
        header_elements.session_toggle,
    )

    file_manager = setup_file_manager(
        agent,
        session_ctx.namespace,
        chat_messages,
        header_elements.file_badge,
        refresh_session_list_callback=session_panel.refresh,
    )
    # Wire up the file refresh holder now that file_manager exists
    file_refresh_holder["fn"] = file_manager.refresh
    header_elements.file_toggle.on("click", lambda: file_manager.drawer.toggle())

    # --- Wire Turn Handling ---
    _setup_turn_handling(
        chat_messages=chat_messages,
        chat_input=chat_input,
        agent=agent,
        agent_task=agent_task,
        session_ctx=session_ctx,
        turn_config=turn_config,
        theme_manager=theme_manager,
        refresh_file_list=file_manager.refresh,
        refresh_session_list=session_panel.refresh,
        refresh_preview=refresh_preview,
    )

    # --- Restore History ---
    _restore_and_greet(
        chat_messages=chat_messages,
        chat_input=chat_input,
        agent=agent,
        session_ctx=session_ctx,
        config=config,
        turn_config=turn_config,
        theme_manager=theme_manager,
        refresh_file_list=file_manager.refresh,
        refresh_session_list=session_panel.refresh,
        refresh_preview=refresh_preview,
    )

    # Delayed file list refresh to ensure badge is updated after page fully loads
    ui.timer(0.1, file_manager.refresh, once=True)

    return chat_messages, chat_input, theme_manager


# --- Helper functions (private) ---

@dataclass
class SessionContext:
    branch: str
    namespace: str


@dataclass  
class HeaderElements:
    session_toggle: ui.button
    file_toggle: ui.button
    file_badge: ui.label


def _validate_versioned_state(agent: "Agent"):
    test_state = agent.state("__test__")
    if not isinstance(test_state, Staged):
        raise ValueError(
            "agex-ui requires a versioned state. "
            "Configure your agent with: state=connect_state(type='versioned', ...)"
        )


def _init_session_context(
    agent: "Agent",
    namespace: str,
    initial_branch: str | None,
) -> SessionContext:
    from datetime import datetime, timezone

    state: Staged = agent.state(namespace)

    # Determine which branch to use
    current_branch = app.storage.user.get(CURRENT_BRANCH_KEY)

    if initial_branch:
        current_branch = initial_branch

    # Validate the branch exists
    if current_branch and current_branch in state.list_branches():
        state.switch_branch(current_branch)
    else:
        # Create a new chat branch from the initial commit
        branch_name = generate_branch_name()
        initial = state.versioned.initial_commit
        state.create_branch(branch_name, at=initial)
        state.switch_branch(branch_name)
        now = datetime.now(timezone.utc).isoformat()
        state[SESSION_UPDATED_KEY] = now
        state.commit()
        current_branch = branch_name

    app.storage.user[CURRENT_BRANCH_KEY] = current_branch

    return SessionContext(
        branch=current_branch,
        namespace=namespace,
    )


def _build_header(config: ChatInterfaceConfig, theme_manager: ThemeManager) -> HeaderElements:
    with (
        ui.header(elevated=False)
        .style(
            f"background-color: {config.header_bg_color}; min-height: 40px; padding: 4px 16px; border-bottom: 1px solid rgba(0,0,0,0.15);"
        )
        .classes("items-center justify-between")
    ):
        session_toggle_btn = ui.button(icon="menu").props(
            "flat round dense color=white"
        ).tooltip("Sessions")

        ui.label(config.title).classes("text-lg font-medium")

        ui.element("div").classes("flex-grow")

        theme_manager.create_toggle_button()

        with ui.button(icon="folder").props(
            "flat round dense color=white"
        ).tooltip("Files") as file_toggle_btn:
            file_badge = ui.label().classes("absolute-center text-grey-8 font-bold").style("font-size: 11px; margin-top: 1px;")
            file_badge.visible = False

    return HeaderElements(
        session_toggle=session_toggle_btn,
        file_toggle=file_toggle_btn,
        file_badge=file_badge,
    )


@dataclass
class ChatAreaResult:
    """Result from building the chat area."""
    chat_messages: ui.column
    chat_input: ui.input
    refresh_preview: Callable[[], None] | None


def _build_chat_area(
    config: ChatInterfaceConfig,
    session_ctx: SessionContext,
    agent: "Agent",
    refresh_file_list: Callable[[], None] | None = None,
) -> ChatAreaResult:
    """Build the main chat area, optionally with preview panel.

    Returns:
        ChatAreaResult with chat elements
    """
    refresh_preview = None

    if config.enable_app_preview:
        from nicegui import app
        from agex_ui.core.preview import create_preview_panel

        # Split layout: chat on left, preview on right
        # Use --header-height CSS variable to account for header
        # Style the splitter to have a more visible separator via props
        # Persist splitter position in user storage
        splitter_position = app.storage.user.get('preview_splitter_position', 50)
        with ui.splitter(value=splitter_position).classes("w-full").style(
            "height: calc(100vh - var(--header-height)); background-color: var(--bg-primary);"
        ).props("separator-style='background-color: var(--accent-primary); width: 4px; opacity: 0.5;'") as splitter:
            # Save position when changed
            splitter.on_value_change(lambda e: app.storage.user.update({'preview_splitter_position': e.value}))
            with splitter.before:
                chat_messages, chat_input = _build_chat_column(config)
            with splitter.after:
                with ui.column().classes("w-full h-full p-0 m-0"):
                    _, refresh_preview = create_preview_panel(
                        session_ctx.branch,
                        agent=agent,
                        namespace=session_ctx.namespace,
                        chat_messages=chat_messages,
                        on_refresh=refresh_file_list,
                        on_debug_captured=refresh_file_list,
                    )

    else:
        # Standard single-column layout
        chat_messages, chat_input = _build_chat_column(config)

    return ChatAreaResult(
        chat_messages=chat_messages,
        chat_input=chat_input,
        refresh_preview=refresh_preview,
    )


def _build_chat_column(
    config: ChatInterfaceConfig,
) -> tuple[ui.column, ui.input]:
    """Build the chat messages column and input.

    Returns:
        (chat_messages, chat_input)
    """
    with (
        ui.column()
        .classes("content-container h-full px-4 pb-1 w-full mx-auto min-w-0")
        .style(f"max-width: {config.max_width}; min-width: {config.min_width};")
    ):
        chat_messages = (
            ui.column()
            .classes("w-full flex-grow overflow-auto p-2 pr-6 pb-12 min-h-0")
            .style("max-width: 100%; opacity: 0; transition: opacity 0.15s ease-in;")
            .props("id=chat-messages-container")
        )

        with ui.row().classes("w-full items-center p-2 border-t gap-2 shrink-0"):
            chat_input = ui.input(placeholder="Type your request...").classes(
                "flex-grow"
            )

    return chat_messages, chat_input


def _setup_turn_handling(
    chat_messages: ui.column,
    chat_input: ui.input,
    agent: "Agent",
    agent_task: Callable,
    session_ctx: SessionContext,
    turn_config: TurnConfig,
    theme_manager: ThemeManager,
    refresh_file_list: Callable,
    refresh_session_list: Callable,
    refresh_preview: Callable | None = None,
):
    async def handle_turn():
        """Handle turn execution (start or stop)."""
        # Stop case
        if chat_input.props.get("disable"):
            if hasattr(agent_task, "cancel"):
                agent_task.cancel(session=session_ctx.namespace)
                ui.notify("Cancelling task...", type="warning")
            return

        # Send case
        if not chat_input.value.strip():
            return

        # Capture user prompt
        user_prompt = chat_input.value

        # UI -> Running
        chat_input.disable()
        send_button.props("icon=stop color=negative")
        send_button.tooltip("Stop generation")

        try:
            await _run_agent_turn_helper(user_prompt)
        finally:
            # UI -> Ready
            chat_input.enable()
            send_button.props("icon=send color=primary")
            send_button.tooltip("Send message")
            chat_input.run_method("focus")

    # Add send button
    with chat_input.parent_slot:  # pyright: ignore
        send_button = (
            ui.button(icon="send", on_click=handle_turn)
            .props("round flat color=primary")
            .classes("ml-2")
            .tooltip("Send message")
        )

    # Bind enter key
    chat_input.on("keydown.enter", handle_turn)

    async def _run_agent_turn_helper(prompt: str):
        await run_agent_turn(
            chat_messages=chat_messages,
            chat_input=chat_input,
            agent=agent,
            agent_task=agent_task,
            prompt=prompt,
            session=session_ctx.namespace,
            config=turn_config,
            dark_mode=theme_manager.dark_mode,
            refresh_file_list_callback=refresh_file_list,
            refresh_session_list_callback=refresh_session_list,
            refresh_preview_callback=refresh_preview,
        )


def _restore_and_greet(
    chat_messages: ui.column,
    chat_input: ui.input,
    agent: "Agent",
    session_ctx: SessionContext,
    config: ChatInterfaceConfig,
    turn_config: TurnConfig,
    theme_manager: ThemeManager,
    refresh_file_list: Callable,
    refresh_session_list: Callable,
    refresh_preview: Callable | None = None,
):
    history_state = restore_chat_history(
        chat_messages=chat_messages,
        chat_input=chat_input,
        agent=agent,
        namespace=session_ctx.namespace,
        dark_mode=theme_manager.dark_mode,
        collapse_actions=turn_config.collapse_agent_activity,
        refresh_file_list_callback=refresh_file_list,
        refresh_session_list_callback=refresh_session_list,
        refresh_preview_callback=refresh_preview,
    )

    if history_state is None:
        # No history - show greeting
        with chat_messages:
            ui.chat_message(
                config.greeting,
                sent=False,
                name=agent.name,
                avatar=config.robot_avatar,
                stamp=get_timestamp(),
            ).classes("w-full").props("bg-color=blue-2")
    else:
        # Set up lazy loading if there's more history
        _setup_lazy_loading(
            history_state=history_state,
            chat_messages=chat_messages,
            chat_input=chat_input,
            agent=agent,
            session_ctx=session_ctx,
            config=config,
            theme_manager=theme_manager,
            turn_config=turn_config,
            refresh_file_list=refresh_file_list,
            refresh_session_list=refresh_session_list,
            refresh_preview=refresh_preview,
        )

    # Scroll to bottom after history loads, then fade in
    ui.timer(
        0.05,
        lambda: ui.run_javascript(
            "var el = document.getElementById('chat-messages-container');"
            "el.scrollTop = 999999;"
            "el.style.opacity = '1';"
        ),
        once=True,
    )

    # Set up intersection observer after scroll (slight delay)
    if history_state is not None and history_state.has_more:
        ui.timer(0.2, setup_history_intersection_observer, once=True)


def _setup_lazy_loading(
    history_state: ChatHistoryState,
    chat_messages: ui.column,
    chat_input: ui.input,
    agent: "Agent",
    session_ctx: SessionContext,
    config: ChatInterfaceConfig,
    theme_manager: ThemeManager,
    turn_config: TurnConfig,
    refresh_file_list: Callable,
    refresh_session_list: Callable,
    refresh_preview: Callable | None,
):
    """Set up the load_more handler for lazy loading history."""
    # Track loading state to prevent concurrent loads
    loading_state = {"is_loading": False}

    async def load_more():
        """Load more history when user scrolls to top."""
        if loading_state["is_loading"]:
            return
        if not history_state.has_more:
            return

        loading_state["is_loading"] = True

        try:
            # Get next chunk
            chunk = history_state.get_next_chunk()
            if not chunk:
                return

            # Render chunk in hidden wrapper (doesn't affect layout yet)
            wrapper_id = render_history_chunk(
                chunk,
                chat_messages,
                chat_input,
                agent,
                session_ctx.namespace,
                theme_manager.dark_mode,
                turn_config.collapse_agent_activity,
                refresh_file_list,
                refresh_session_list,
                refresh_preview,
                prepend=True,
            )

            # Atomically reveal content and adjust scroll position
            if wrapper_id:
                reveal_prepended_chunk(wrapper_id)

            # If no more history, remove sentinel and show greeting
            if not history_state.has_more:
                remove_history_sentinel()
                show_history_start_indicator(
                    chat_messages,
                    greeting=config.greeting,
                    agent_name=agent.name,
                    avatar=config.robot_avatar,
                )

        finally:
            loading_state["is_loading"] = False

    # Register event handler
    ui.on("load_more_history", load_more)