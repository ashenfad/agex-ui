"""Event handling and streaming coordination for agent execution.

This module handles real-time event processing, token streaming, and UI updates
during agent execution.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime

from agex import Event, OutputEvent, SummaryEvent
from agex.agent.datatypes import EditAction, FileAction
from agex.eval.objects import PrintAction
from agex.llm.core import StreamToken
from nicegui import ui
from nicegui.elements.html import Html

from agex_ui.core.renderers import EventRenderer


# Keywords that indicate an OutputEvent contains error content
ERROR_KEYWORDS = ("💥", "Error:", "Exception:", "Traceback", "ERROR:")


def is_error_output_event(evt: OutputEvent) -> bool:
    """Check if an OutputEvent contains error content.

    Used to filter error-related OutputEvents for display in the activity panel,
    while skipping regular output events (which are shown in the final response).
    """
    for part in evt.parts:
        if isinstance(part, PrintAction):
            content = " ".join(str(item) for item in part)
            if any(keyword in content for keyword in ERROR_KEYWORDS):
                return True
    return False


def get_error_output_content(evt: OutputEvent) -> str:
    """Extract the error message content from an error OutputEvent."""
    parts = []
    for part in evt.parts:
        if isinstance(part, PrintAction):
            parts.append(" ".join(str(item) for item in part))
        else:
            parts.append(str(part))
    return "\n".join(parts)


@dataclass
class ActionStreamRenderer:
    """Handles token-by-token rendering of ActionEvents.

    Accumulates streaming tokens (title, thinking, code, terminal) and renders them
    into an ActionEvent-style card that updates in real-time.
    """

    title_parts: list[str] = field(default_factory=list)
    thinking_parts: list[str] = field(default_factory=list)
    code_parts: list[str] = field(default_factory=list)
    terminal_parts: list[str] = field(default_factory=list)
    file_parts: dict[str, list[str]] = field(default_factory=dict)
    file_modes: dict[str, str] = field(default_factory=dict)
    current_file_path: str | None = None
    # Edit action tracking
    edit_actions: list[EditAction] = field(default_factory=list)
    current_edit: dict | None = None  # Accumulates path, search, replace, replace_all
    card: Html | None = None
    agent_name: str = ""
    full_namespace: str = ""
    timestamp: datetime | None = None
    event_renderer: EventRenderer | None = None

    def render_html(self) -> str:
        """Generate HTML for current action state using themed renderer."""
        fallback_name = self.agent_name or "agent"
        fallback_namespace = self.full_namespace or fallback_name

        # Build file actions from accumulated parts
        file_actions: list[FileAction | EditAction] = []
        for path, parts in self.file_parts.items():
            content = "".join(parts)
            mode = self.file_modes.get(path, "write")
            file_actions.append(FileAction(path=path, content=content, mode=mode))  # type: ignore[arg-type]

        # Add completed edit actions
        file_actions.extend(self.edit_actions)

        renderer = self.event_renderer or EventRenderer()
        return renderer.render_action_event(
            agent_name=fallback_name,
            full_namespace=fallback_namespace,
            timestamp=self.timestamp or datetime.now(),
            title="".join(self.title_parts).strip(),
            thinking="".join(self.thinking_parts),
            code="".join(self.code_parts),
            terminal="".join(self.terminal_parts),
            dark_mode=renderer.dark_mode,
            file_actions=file_actions,
        )

    def reset(self):
        """Clear accumulated state for a new action."""
        self.title_parts.clear()
        self.thinking_parts.clear()
        self.code_parts.clear()
        self.terminal_parts.clear()
        self.file_parts.clear()
        self.file_modes.clear()
        self.current_file_path = None
        self.edit_actions.clear()
        self.current_edit = None
        self.card = None


@dataclass
class EventHandler:
    """Coordinates event processing and UI updates.

    Handles both complete events (OutputEvent, ActionEvent) and streaming
    tokens, scheduling UI updates on the main asyncio loop.
    """

    loop: asyncio.AbstractEventLoop
    expansion: ui.expansion
    event_count: int = 0
    current_action_title: str = ""
    current_action: ActionStreamRenderer = field(default_factory=ActionStreamRenderer)
    show_setup_events: bool = False
    dark_mode: bool = False

    def __post_init__(self):
        """Initialize the event renderer after dataclass init."""
        self.event_renderer = EventRenderer(dark_mode=self.dark_mode)
        self.current_action.event_renderer = self.event_renderer

    def update_expansion_label(self):
        """Update the expansion header with current status."""
        label = "Activity"
        if self.current_action_title:
            label = f"{label} — {self.current_action_title}"
        self.expansion.text = label

    def handle_event(self, evt: Event, renderer: EventRenderer | None = None):
        """Process incoming agent events.

        Args:
            evt: Event from the agent
            renderer: EventRenderer instance for rendering events (optional)
        """
        # Skip setup OutputEvents if configured (but show summary/checkpoint events)
        if (
            not self.show_setup_events
            and evt.source == "setup"
            and isinstance(evt, OutputEvent)
        ):
            return

        # Handle OutputEvents: show errors in activity, skip others
        if isinstance(evt, OutputEvent):
            if not is_error_output_event(evt):
                return
            # Render error OutputEvent
            self._render_error_output_event(evt)
            return

        # Handle SummaryEvents (ActionEvents handled via token streaming)
        if not isinstance(evt, SummaryEvent):
            return

        async def do_ui_update():
            """UI update coroutine executed on main loop."""
            # Increment event count
            self.event_count += 1
            self.update_expansion_label()

            with self.expansion:
                # Render SummaryEvents with themed styling
                with ui.element("div").classes("themed-event-card"):
                    ui.html(
                        f"""
                        <div class="themed-event-header">📊 Summary</div>
                        <div>{evt.as_html()}</div>
                    """
                    )

        # Schedule on main loop from background thread
        asyncio.run_coroutine_threadsafe(do_ui_update(), self.loop)

    def _render_error_output_event(self, evt: OutputEvent):
        """Render an error OutputEvent in the activity panel."""
        import html as html_escape

        error_content = get_error_output_content(evt)

        async def do_ui_update():
            self.event_count += 1
            self.update_expansion_label()

            with self.expansion:
                with ui.element("div").classes("themed-event-card"):
                    escaped_content = html_escape.escape(error_content)
                    ui.html(
                        f"""
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
                        """,
                        sanitize=False,
                    )

        asyncio.run_coroutine_threadsafe(do_ui_update(), self.loop)

    def handle_token(self, token: object, agent_name: str = "agent"):
        """Process streaming tokens for real-time updates.

        Args:
            token: Token object from agent streaming
            agent_name: Default agent name to use
        """
        if not isinstance(token, StreamToken):
            return

        async def do_ui_update():
            """UI update coroutine executed on main loop."""
            try:
                # Start a new action when any section begins and we don't have a card
                if token.start and self.current_action.card is None:
                    self.current_action.reset()
                    self.current_action.agent_name = token.agent_name or agent_name
                    self.current_action.full_namespace = (
                        token.full_namespace or self.current_action.agent_name
                    )
                    self.current_action.timestamp = token.timestamp
                    self.current_action.event_renderer = self.event_renderer

                    # Set initial title based on which section we're starting with
                    if token.type == "title":
                        initial_title = "(starting)"
                    elif token.type == "thinking":
                        initial_title = "(thinking...)"
                    else:
                        initial_title = "(coding...)"

                    with self.expansion:
                        # Create initial card with themed HTML
                        initial_html = self.event_renderer.render_action_event(
                            agent_name=self.current_action.agent_name,
                            full_namespace=self.current_action.full_namespace,
                            timestamp=self.current_action.timestamp,
                            title=initial_title,
                            thinking="",
                            code="",
                        )
                        self.current_action.card = (
                            ui.html(initial_html, sanitize=False)
                            .classes("w-full p-0 my-0")
                            .style("transition: opacity 120ms ease-in")
                        )

                    self.event_count += 1
                    self.current_action_title = initial_title
                    self.update_expansion_label()

                # No card means nothing to update yet
                if self.current_action.card is None:
                    return

                # Accumulate content by type
                if token.type == "title":
                    self.current_action.title_parts.append(token.content)
                    new_title = "".join(self.current_action.title_parts).strip()
                    if new_title:
                        self.current_action_title = new_title
                elif token.type == "thinking" and not token.done:
                    self.current_action.thinking_parts.append(token.content)
                elif token.type == "python" and not token.done:
                    self.current_action.code_parts.append(token.content)
                elif token.type == "terminal" and not token.done:
                    self.current_action.terminal_parts.append(token.content)
                elif token.type == "file" and not token.done:
                    # Parse file metadata or accumulate content
                    if token.content.startswith("path="):
                        # Metadata: "path=foo.py,mode=append"
                        import re
                        path_match = re.search(r"path=([^,]+)", token.content)
                        mode_match = re.search(r"mode=([^,]+)", token.content)

                        if path_match:
                            self.current_action.current_file_path = path_match.group(1)
                            self.current_action.file_parts[self.current_action.current_file_path] = []
                            self.current_action.file_modes[self.current_action.current_file_path] = (
                                mode_match.group(1) if mode_match else "write"
                            )
                    elif self.current_action.current_file_path:
                        # Content for the current file
                        self.current_action.file_parts[self.current_action.current_file_path].append(token.content)
                elif token.type == "file" and token.done:
                    # File section complete
                    self.current_action.current_file_path = None
                elif token.type == "edit" and not token.done:
                    # Parse edit metadata or accumulate content
                    # Metadata format: "path=foo.py,match_all=false"
                    # Content contains <SEARCH>...</SEARCH> and one of
                    # <REPLACE>...</REPLACE>, <INSERT-AFTER>...</INSERT-AFTER>, or <INSERT-BEFORE>...</INSERT-BEFORE>
                    import re

                    if token.content.startswith("path="):
                        # Start new edit action
                        path_match = re.search(r"path=([^,]+)", token.content)
                        match_all_match = re.search(r"match_all=(true|false)", token.content, re.IGNORECASE)

                        if path_match:
                            self.current_action.current_edit = {
                                "path": path_match.group(1),
                                "content": [],  # Raw content with SEARCH/operation tags
                                "match_all": match_all_match and match_all_match.group(1).lower() == "true",
                            }
                    elif self.current_action.current_edit:
                        # Accumulate raw content
                        self.current_action.current_edit["content"].append(token.content)
                elif token.type == "edit" and token.done:
                    # Edit section complete - parse SEARCH and operation tags
                    import re

                    if self.current_action.current_edit:
                        edit = self.current_action.current_edit
                        raw_content = "".join(edit["content"])

                        # Parse SEARCH tag (always required)
                        search_match = re.search(
                            r"<SEARCH>(.*?)</SEARCH>",
                            raw_content,
                            re.DOTALL | re.IGNORECASE,
                        )

                        # Parse operation tag - REPLACE, INSERT-AFTER, or INSERT-BEFORE
                        replace_match = re.search(
                            r"<REPLACE>(.*?)</REPLACE>",
                            raw_content,
                            re.DOTALL | re.IGNORECASE,
                        )
                        insert_after_match = re.search(
                            r"<INSERT-AFTER>(.*?)</INSERT-AFTER>",
                            raw_content,
                            re.DOTALL | re.IGNORECASE,
                        )
                        insert_before_match = re.search(
                            r"<INSERT-BEFORE>(.*?)</INSERT-BEFORE>",
                            raw_content,
                            re.DOTALL | re.IGNORECASE,
                        )

                        # Determine content and operation from matched tag
                        content = None
                        operation = "replace"
                        if replace_match:
                            content = replace_match.group(1)
                            operation = "replace"
                        elif insert_after_match:
                            content = insert_after_match.group(1)
                            operation = "insert-after"
                        elif insert_before_match:
                            content = insert_before_match.group(1)
                            operation = "insert-before"

                        if search_match and content is not None:
                            self.current_action.edit_actions.append(
                                EditAction(
                                    path=edit["path"],
                                    search=search_match.group(1),
                                    content=content,
                                    operation=operation,
                                    match_all=edit.get("match_all", False),
                                )
                            )
                        self.current_action.current_edit = None

                self.update_expansion_label()
                self.current_action.card.set_content(self.current_action.render_html())
                self.current_action.card.update()

                if token.done and token.type in ("python", "terminal"):
                    # Clear card reference so next title starts fresh
                    self.current_action.card = None

            except Exception:
                import traceback

                traceback.print_exc()

        asyncio.run_coroutine_threadsafe(do_ui_update(), self.loop)
