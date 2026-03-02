"""Chat history restoration from agex state events.

This module reconstructs the chat UI from historic events stored in agex state.
Supports lazy loading for long conversations.
"""

import html as html_escape
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from agex import Agent

from agex import events, OutputEvent
from agex.agent.events import (
    ActionEvent,
    FileEvent,
    CancelledEvent,
    ClarifyEvent,
    FailEvent,
    SuccessEvent,
    TaskStartEvent,
)
from agex.state import Staged
from nicegui import ui

import plotly.graph_objects as go
from agex_ui.core.events import is_error_output_event, get_error_output_content
from agex_ui.core.renderers import EventRenderer, ResponseRenderer
from agex_ui.core.responses import PlotlyPart, Response
from agex_ui.core.utils import clear_chat_until, format_timestamp


# --- Lazy Loading Infrastructure ---


@dataclass
class RenderUnit:
    """A complete renderable item in chat history.

    Each unit represents something that should be rendered together,
    preserving the task grouping logic (user message + actions + response).
    """
    unit_type: str  # "task" or "user_file"

    # For task units - activity_items preserves chronological order of actions and errors
    task_start: TaskStartEvent | None = None
    activity_items: list[ActionEvent | OutputEvent] = field(default_factory=list)
    completion_event: Any = None  # SuccessEvent, FailEvent, ClarifyEvent, CancelledEvent
    revert_commit: str | None = None
    is_interrupted: bool = False
    interrupt_reason: str = ""

    # For user file upload units
    file_event: FileEvent | None = None


@dataclass
class ChatHistoryState:
    """Tracks lazy loading state for chat history."""
    render_units: list[RenderUnit]  # All render units (computed once)
    loaded_index: int  # Index of oldest loaded unit
    chunk_size: int = 8  # Units per chunk (not raw events)
    fully_loaded: bool = False

    @property
    def has_more(self) -> bool:
        return self.loaded_index > 0

    def get_initial_chunk(self) -> list[RenderUnit]:
        """Get the initial chunk (most recent units)."""
        start_index = max(0, len(self.render_units) - self.chunk_size)
        self.loaded_index = start_index
        if start_index == 0:
            self.fully_loaded = True
        return self.render_units[start_index:]

    def get_next_chunk(self) -> list[RenderUnit]:
        """Get the next chunk of older units to render."""
        if not self.has_more:
            return []

        end_index = self.loaded_index
        start_index = max(0, end_index - self.chunk_size)
        self.loaded_index = start_index

        if start_index == 0:
            self.fully_loaded = True

        return self.render_units[start_index:end_index]


def _events_to_render_units(main_events: list[Any]) -> list[RenderUnit]:
    """Convert a list of events into render units.

    Preserves the task grouping logic from the original restore_chat_history.
    """
    render_units: list[RenderUnit] = []

    current_task_start: TaskStartEvent | None = None
    current_activity: list[ActionEvent | OutputEvent] = []
    revert_commit: str | None = None

    def flush_incomplete_task(reason: str):
        """Flush current task as interrupted."""
        nonlocal current_task_start, current_activity, revert_commit
        if current_task_start is not None:
            render_units.append(RenderUnit(
                unit_type="task",
                task_start=current_task_start,
                activity_items=current_activity.copy(),
                revert_commit=revert_commit,
                is_interrupted=True,
                interrupt_reason=reason,
            ))
        current_task_start = None
        current_activity = []
        revert_commit = None

    for event in main_events:
        if isinstance(event, TaskStartEvent):
            # New task starting - flush previous incomplete task if exists
            flush_incomplete_task("(Task in progress or interrupted)")

            # Start new task group
            current_task_start = event
            current_activity = []
            revert_commit = event.commit_hash

        elif isinstance(event, ActionEvent):
            current_activity.append(event)

        elif isinstance(event, OutputEvent):
            # Capture error OutputEvents for display in activity (in chronological order)
            if is_error_output_event(event):
                current_activity.append(event)

        elif isinstance(event, FileEvent):
            if event.file_source == "user":
                # User file upload - flush any pending task first
                flush_incomplete_task("(Task interrupted by file upload)")

                # Add user file upload as its own unit
                render_units.append(RenderUnit(
                    unit_type="user_file",
                    file_event=event,
                ))

            # Agent file events are not rendered as separate units

        elif isinstance(event, (SuccessEvent, FailEvent, ClarifyEvent, CancelledEvent)):
            if current_task_start is not None:
                # Complete task unit
                render_units.append(RenderUnit(
                    unit_type="task",
                    task_start=current_task_start,
                    activity_items=current_activity.copy(),
                    completion_event=event,
                    revert_commit=revert_commit,
                ))

            # Reset for next task
            current_task_start = None
            current_activity = []
            revert_commit = None

    # Handle case where last task is still in progress
    if current_task_start is not None:
        render_units.append(RenderUnit(
            unit_type="task",
            task_start=current_task_start,
            activity_items=current_activity.copy(),
            revert_commit=revert_commit,
            is_interrupted=True,
            interrupt_reason="",  # No message for in-progress tasks
        ))

    return render_units




def _render_single_unit(
    unit: RenderUnit,
    chat_messages: ui.column,
    chat_input: ui.input,
    agent: "Agent",
    namespace: str,
    state,
    event_renderer: EventRenderer,
    response_renderer: ResponseRenderer,
    agent_name: str,
    collapse_actions: bool,
    refresh_file_list_callback: Callable[[], None] | None = None,
    refresh_session_list_callback: Callable[[], None] | None = None,
    refresh_preview_callback: Callable[[], None] | None = None,
) -> ui.element | None:
    """Render a single RenderUnit to the chat container.

    Returns the outermost element created (for prepend positioning).
    """
    if unit.unit_type == "user_file" and unit.file_event:
        # User file upload
        _render_user_message(
            chat_messages,
            event_renderer.render_file_event(unit.file_event),
            unit.file_event.timestamp,
            agent,
            namespace,
            state,
            unit.file_event.commit_hash,
            refresh_file_list_callback,
            refresh_session_list_callback,
            refresh_preview_callback,
        )
        return None  # Can't easily get ref to created element

    elif unit.unit_type == "task" and unit.task_start:
        prompt = unit.task_start.inputs.get("prompt", "")

        # Render user message
        _render_user_message(
            chat_messages,
            prompt,
            unit.task_start.timestamp,
            agent,
            namespace,
            state,
            unit.revert_commit,
            refresh_file_list_callback,
            refresh_session_list_callback,
            refresh_preview_callback,
            chat_input,
            restore_prompt=prompt,
        )

        # Render activity (actions and error outputs in chronological order)
        _render_action_events(
            chat_messages, unit.activity_items, event_renderer, collapse_actions,
        )

        # Render response
        if unit.is_interrupted:
            if unit.interrupt_reason:
                _render_agent_response(
                    chat_messages,
                    unit.interrupt_reason,
                    None,
                    agent_name,
                    response_renderer,
                    is_error=True,
                )
            # If no interrupt_reason, task is still in progress - no response to show
        elif unit.completion_event:
            message = ""
            is_error = False

            if isinstance(unit.completion_event, SuccessEvent):
                message = unit.completion_event.result
            elif isinstance(unit.completion_event, (FailEvent, ClarifyEvent)):
                message = unit.completion_event.message
                is_error = isinstance(unit.completion_event, FailEvent)
            elif isinstance(unit.completion_event, CancelledEvent):
                message = "Task was cancelled."
                is_error = True

            _render_agent_response(
                chat_messages,
                message,
                unit.completion_event.timestamp,
                agent_name,
                response_renderer,
                is_error=is_error,
            )

    return None


def _render_user_message(
    chat_messages: ui.column,
    message: str,
    timestamp: datetime | None,
    agent: "Agent",
    namespace: str,
    state,
    revert_commit: str | None,
    refresh_file_list_callback: Callable[[], None] | None = None,
    refresh_session_list_callback: Callable[[], None] | None = None,
    refresh_preview_callback: Callable[[], None] | None = None,
    chat_input: ui.input | None = None,
    restore_prompt: str | None = None,
) -> None:
    """Render a user chat message with optional revert button."""
    with chat_messages:
        message_container = ui.column().classes("self-end relative group max-w-full min-w-0")

        with message_container:
            with ui.chat_message(
                sent=True,
                name="You",
                avatar="assets/human.png",
                stamp=format_timestamp(timestamp),
            ):
                ui.markdown(message)

        # Add revert button for Staged state
        if isinstance(state, Staged) and revert_commit:

            async def undo_to_commit():
                """Reset state to this commit and remove subsequent UI elements."""
                if not state.reset_to(revert_commit):
                    ui.notify("Failed to reset state", type="negative")
                    return

                # Recalculate title after revert
                update_session_title_from_state(agent, namespace)

                if refresh_file_list_callback:
                    refresh_file_list_callback()

                if refresh_session_list_callback:
                    refresh_session_list_callback()

                if refresh_preview_callback:
                    refresh_preview_callback()

                # Restore input if provided
                if chat_input and restore_prompt:
                    chat_input.value = restore_prompt

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


def _render_error_output_html(error_content: str) -> str:
    """Generate HTML for an error OutputEvent card."""
    escaped_content = html_escape.escape(error_content)
    return f"""
    <div class="themed-event-card">
        <div class="themed-event-header" style="color: var(--accent-error);">
            ⚠️ Error
        </div>
        <div style="overflow-x: auto;">
            <pre style="font-family: monospace; font-size: 13px;
                        padding: 8px; background: var(--bg-code);
                        border-radius: 4px; color: var(--accent-error);
                        border-left: 3px solid var(--accent-error);
                        margin: 0; white-space: pre;">{escaped_content}</pre>
        </div>
    </div>
    """


def _render_activity_item(
    item: ActionEvent | OutputEvent,
    event_renderer: EventRenderer,
) -> None:
    """Render a single activity item (ActionEvent or error OutputEvent)."""
    if isinstance(item, ActionEvent):
        file_actions = getattr(item, "file_actions", [])
        html_content = event_renderer.render_action_event(
            agent_name=item.agent_name,
            full_namespace=item.full_namespace,
            timestamp=item.timestamp,
            title=item.title if hasattr(item, "title") else "",
            thinking=item.thinking,
            code=item.code or "",
            terminal=item.terminal or "",
            dark_mode=event_renderer.dark_mode,
            file_actions=file_actions,
        )
        ui.html(html_content, sanitize=False).classes("w-full p-0 my-0")
    elif isinstance(item, OutputEvent):
        # Error OutputEvent
        error_content = get_error_output_content(item)
        ui.html(
            _render_error_output_html(error_content),
            sanitize=False,
        ).classes("w-full p-0 my-0")


def _render_action_events(
    chat_messages: ui.column,
    activity_items: list[ActionEvent | OutputEvent],
    event_renderer: EventRenderer,
    collapsed: bool = True,
) -> None:
    """Render activity items (ActionEvents and error OutputEvents) in a collapsed expansion panel.

    Items are rendered in chronological order as they appear in the list.
    When collapsed=True, content is rendered lazily on first expand.
    """
    if not activity_items:
        return

    # Build label from last ActionEvent title
    last_title = ""
    for item in reversed(activity_items):
        if isinstance(item, ActionEvent) and item.title:
            last_title = item.title
            break

    if last_title:
        label = f"Activity — {last_title}"
    else:
        label = "Activity"

    with chat_messages:
        expansion = ui.expansion(label, icon="psychology").classes(
            "w-full border border-gray-200 rounded-lg text-gray-500"
        )
        expansion.value = not collapsed

        def add_collapse_footer():
            """Add a collapse link at the bottom of expanded content."""
            ui.label("Collapse ↑").classes(
                "w-full text-center text-xs text-gray-400 cursor-pointer hover:text-gray-600"
            ).style("margin-top: -12px; margin-bottom: -6px;").on(
                "click", lambda: setattr(expansion, 'value', False)
            )

        if collapsed:
            # Lazy rendering - only render content on first expand
            rendered = False

            def render_on_expand(e):
                nonlocal rendered
                if e.value and not rendered:
                    rendered = True
                    with expansion:
                        for item in activity_items:
                            _render_activity_item(item, event_renderer)
                        add_collapse_footer()

            expansion.on_value_change(render_on_expand)
        else:
            # Not collapsed - render immediately
            with expansion:
                for item in activity_items:
                    _render_activity_item(item, event_renderer)
                add_collapse_footer()


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
            .props(f'bg-color={bg_color} stamp="{format_timestamp(timestamp)}"')
        ) as agent_message:
            response_renderer.render_response(result)

            # Check if result contains wide content (Plotly only)
            has_wide_content = False
            if isinstance(result, go.Figure):
                has_wide_content = True
            elif isinstance(result, Response):
                # Check if any part is wide (Plotly only)
                for part in result.parts:
                    if isinstance(part, (PlotlyPart, go.Figure)):
                        has_wide_content = True
                        break

            # Apply wide style if needed
            if has_wide_content:
                agent_message.classes("wide-message")


def update_session_title_from_state(
    agent: "Agent",
    namespace: str,
) -> str | None:
    """Recalculate and update the session title based on the current state history.

    Writes the title to the state as a special key and commits.

    Returns:
        The new title if updated, else None
    """
    from agex_ui.core.sessions import SESSION_TITLE_KEY, SESSION_UPDATED_KEY

    state = agent.state(namespace)
    if state is None:
        return None

    all_events = events(state)
    main_events = [e for e in all_events if e.source != "setup"]

    # Find the last ActionEvent with a title
    last_title = ""
    last_timestamp = None
    for event in reversed(main_events):
        if isinstance(event, ActionEvent) and event.title:
            last_title = event.title
            last_timestamp = event.timestamp
            break

    title_to_set = last_title or "New Chat"
    state[SESSION_TITLE_KEY] = title_to_set
    if last_timestamp:
        state[SESSION_UPDATED_KEY] = last_timestamp.isoformat()
    state.commit()
    return title_to_set


# --- Lazy Loading Functions ---


def load_chat_history_state(agent: "Agent", namespace: str) -> ChatHistoryState | None:
    """Load all events and convert to render units without rendering.

    Returns None if no history exists.
    """
    state = agent.state(namespace)
    if state is None:
        return None

    all_events = events(state)
    if not all_events:
        return None

    # Filter out setup events
    main_events = [e for e in all_events if e.source != "setup"]
    if not main_events:
        return None

    # Convert to render units
    render_units = _events_to_render_units(main_events)
    if not render_units:
        return None

    return ChatHistoryState(render_units=render_units, loaded_index=len(render_units))


def render_history_chunk(
    units: list[RenderUnit],
    chat_messages: ui.column,
    chat_input: ui.input,
    agent: "Agent",
    namespace: str,
    dark_mode: bool,
    collapse_actions: bool,
    refresh_file_list_callback: Callable[[], None] | None = None,
    refresh_session_list_callback: Callable[[], None] | None = None,
    refresh_preview_callback: Callable[[], None] | None = None,
    prepend: bool = False,
) -> str | None:
    """Render a chunk of render units.

    Args:
        units: Units to render (in chronological order)
        prepend: If True, insert at beginning of chat (after sentinel)

    Returns:
        When prepend=True, returns the wrapper element ID for use with
        reveal_prepended_chunk(). Returns None when prepend=False.
    """
    state = agent.state(namespace)
    response_renderer = ResponseRenderer(dark_mode=dark_mode)
    event_renderer = EventRenderer(dark_mode=dark_mode)
    agent_name = agent.name

    if prepend:
        # Create a single wrapper for all prepended content.
        # Use position:absolute so it doesn't affect layout until revealed.
        # This prevents scroll jitter when content is added.
        wrapper_id = f"prepend-wrapper-{uuid.uuid4().hex[:8]}"
        with chat_messages:
            wrapper = (
                ui.column()
                .classes("w-full")
                .props(f'id="{wrapper_id}"')
                .style(
                    "position: absolute; "
                    "visibility: hidden; "
                    "top: 0; "
                    "left: 0; "
                    "right: 0;"
                )
            )
            # Move wrapper after sentinel (index 0)
            wrapper.move(target_index=1)

        # Render all units inside the wrapper in chronological order
        for unit in units:
            _render_single_unit(
                unit,
                wrapper,
                chat_input,
                agent,
                namespace,
                state,
                event_renderer,
                response_renderer,
                agent_name,
                collapse_actions,
                refresh_file_list_callback,
                refresh_session_list_callback,
                refresh_preview_callback,
            )

        return wrapper_id
    else:
        # Normal append - just render in order
        for unit in units:
            _render_single_unit(
                unit,
                chat_messages,
                chat_input,
                agent,
                namespace,
                state,
                event_renderer,
                response_renderer,
                agent_name,
                collapse_actions,
                refresh_file_list_callback,
                refresh_session_list_callback,
                refresh_preview_callback,
            )
        return None


def reveal_prepended_chunk(wrapper_id: str) -> None:
    """Reveal a prepended chunk and adjust scroll position atomically.

    This is called after render_history_chunk(prepend=True) to:
    1. Make the wrapper part of normal flow (but still invisible)
    2. Measure the height now that it has correct width/layout
    3. Adjust scrollTop by that height (so visible content stays in place)
    4. Make the wrapper visible

    All operations happen in a single JS execution to prevent visual jitter.
    """
    ui.run_javascript(f'''
        (function() {{
            const wrapper = document.getElementById('{wrapper_id}');
            const container = document.getElementById('chat-messages-container');
            if (!wrapper || !container) return;

            // Step 1: Switch to normal flow but keep invisible
            // This ensures correct width for accurate height measurement
            wrapper.style.position = 'relative';
            wrapper.style.top = '';
            wrapper.style.left = '';
            wrapper.style.right = '';

            // Step 2: Measure height now that it's in normal document flow
            const wrapperHeight = wrapper.offsetHeight;

            // Step 3: Adjust scroll position to compensate for new content
            container.scrollTop += wrapperHeight;

            // Step 4: Make visible
            wrapper.style.visibility = 'visible';
        }})();
    ''')


def create_history_sentinel(chat_messages: ui.column) -> ui.element:
    """Create an invisible sentinel element at the top of the chat.

    When it becomes visible (user scrolled up), triggers loading more history.
    """
    with chat_messages:
        sentinel = (
            ui.element("div")
            .props('id="history-sentinel"')
            .classes("w-full")
            .style("height: 1px;")
        )
        sentinel.move(target_index=0)
    return sentinel


def setup_history_intersection_observer() -> None:
    """Set up JavaScript Intersection Observer to watch the sentinel.

    Emits 'load_more_history' event when sentinel becomes visible.
    """
    ui.run_javascript('''
        (function() {
            const sentinel = document.getElementById('history-sentinel');
            if (!sentinel) return;

            // Disconnect any existing observer
            if (window.__historyObserver) {
                window.__historyObserver.disconnect();
            }

            let timeout = null;
            const observer = new IntersectionObserver((entries) => {
                if (entries[0].isIntersecting) {
                    // Debounce: wait 100ms before triggering
                    if (timeout) clearTimeout(timeout);
                    timeout = setTimeout(() => {
                        emitEvent('load_more_history');
                    }, 100);
                }
            }, {
                root: document.getElementById('chat-messages-container'),
                threshold: 0.1,
                rootMargin: '200px 0px 0px 0px'  // Trigger before fully visible
            });

            observer.observe(sentinel);
            window.__historyObserver = observer;
        })();
    ''')


def remove_history_sentinel() -> None:
    """Remove the sentinel and observer when all history is loaded."""
    ui.run_javascript('''
        const sentinel = document.getElementById('history-sentinel');
        if (sentinel) sentinel.remove();
        if (window.__historyObserver) {
            window.__historyObserver.disconnect();
            window.__historyObserver = null;
        }
    ''')


def show_history_start_indicator(
    chat_messages: ui.column,
    greeting: str = "Hello! How can I help you today?",
    agent_name: str = "Agent",
    avatar: str = "assets/robot.png",
) -> None:
    """Show the agent greeting at the start of conversation history."""
    with chat_messages:
        msg = (
            ui.chat_message(
                greeting,
                sent=False,
                name=agent_name,
                avatar=avatar,
            )
            .classes("w-full")
            .props("bg-color=blue-2")
        )
        msg.move(target_index=0)




def restore_chat_history(
    chat_messages: ui.column,
    chat_input: ui.input,
    agent: "Agent",
    namespace: str,
    dark_mode: bool = False,
    collapse_actions: bool = True,
    refresh_file_list_callback: Callable[[], None] | None = None,
    refresh_session_list_callback: Callable[[], None] | None = None,
    refresh_preview_callback: Callable[[], None] | None = None,
) -> ChatHistoryState | None:
    """Restore chat history from agent state events with lazy loading.

    Reconstructs the chat UI from historic events stored in the agent's state.
    Only renders the most recent chunk initially; older messages load on scroll.

    Returns:
        ChatHistoryState if history exists (for lazy loading), None if no history
    """
    # Load history state (events converted to render units)
    history_state = load_chat_history_state(agent, namespace)
    if history_state is None:
        return None

    # Get initial chunk (most recent units)
    initial_chunk = history_state.get_initial_chunk()

    # Render initial chunk
    render_history_chunk(
        initial_chunk,
        chat_messages,
        chat_input,
        agent,
        namespace,
        dark_mode,
        collapse_actions,
        refresh_file_list_callback,
        refresh_session_list_callback,
        refresh_preview_callback,
        prepend=False,
    )

    # Add sentinel and observer if there's more history
    if history_state.has_more:
        create_history_sentinel(chat_messages)
        # Observer will be set up after scroll to bottom (in chat_interface.py)

    # Update session title from history
    update_session_title_from_state(agent, namespace)
    if refresh_session_list_callback:
        refresh_session_list_callback()

    return history_state
