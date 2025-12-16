"""Event handling and streaming coordination for agent execution.

This module handles real-time event processing, token streaming, and UI updates
during agent execution.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from agex import ActionEvent, Event, OutputEvent, SummaryEvent
from agex.llm.core import StreamToken
from nicegui import ui
from nicegui.elements.html import Html


@dataclass
class ActionStreamRenderer:
    """Handles token-by-token rendering of ActionEvents.
    
    Accumulates streaming tokens (title, thinking, code) and renders them
    into an ActionEvent-style card that updates in real-time.
    """
    
    title_parts: list[str] = field(default_factory=list)
    thinking_parts: list[str] = field(default_factory=list)
    code_parts: list[str] = field(default_factory=list)
    card: Html | None = None
    agent_name: str = ""
    full_namespace: str = ""
    timestamp: datetime | None = None

    def render_html(self) -> str:
        """Generate HTML for current action state."""
        fallback_name = self.agent_name or "agent"
        fallback_namespace = self.full_namespace or fallback_name
        return ActionEvent(
            agent_name=fallback_name,
            full_namespace=fallback_namespace,
            timestamp=self.timestamp or datetime.now(),
            title="".join(self.title_parts).strip(),
            thinking="".join(self.thinking_parts),
            code="".join(self.code_parts),
        )._repr_html_()

    def reset(self):
        """Clear accumulated state for a new action."""
        self.title_parts.clear()
        self.thinking_parts.clear()
        self.code_parts.clear()
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
    
    def update_expansion_label(self):
        """Update the expansion header with current status."""
        label = "Agent Activity"
        if self.current_action_title:
            label = f"{label} — {self.current_action_title}"
        label = f"{label} ({self.event_count} events)"
        self.expansion.text = label

    def handle_event(self, evt: Event, renderer):
        """Process incoming agent events.
        
        Args:
            evt: Event from the agent
            renderer: EventRenderer instance for rendering events
        """
        # Skip setup OutputEvents if configured (but show summary/checkpoint events)
        if not self.show_setup_events and evt.source == "setup" and isinstance(evt, OutputEvent):
            return

        # Handle OutputEvents and SummaryEvents (ActionEvents handled via token streaming)
        if not isinstance(evt, (OutputEvent, SummaryEvent)):
            return

        async def do_ui_update():
            """UI update coroutine executed on main loop."""
            # Increment event count
            self.event_count += 1
            self.update_expansion_label()

            with self.expansion:
                # Render SummaryEvents directly with their HTML
                if isinstance(evt, SummaryEvent):
                    html_content = evt.as_html()
                    ui.html(html_content, sanitize=False).classes("w-full p-0 my-0")
                    return
                
                # Handle OutputEvents (with Plotly extraction)
                # Extract Plotly figures from event parts
                plotly_figures, other_parts = renderer.extract_plotly_figures(evt)

                # Render Plotly figures with custom card
                if plotly_figures:
                    renderer.render_output_event_with_plotly(evt, plotly_figures)

                # Render other parts as HTML
                if other_parts:
                    from agex.agent.events import OutputEvent as OutputEventClass
                    other_event = OutputEventClass(
                        agent_name=evt.agent_name,
                        parts=other_parts,
                        timestamp=evt.timestamp,
                        full_namespace=evt.full_namespace,
                        commit_hash=evt.commit_hash,
                    )
                    html_content = other_event.as_html()
                    ui.html(html_content, sanitize=False).classes("w-full p-0 my-0")

        # Schedule on main loop from background thread
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

                    # Set initial title based on which section we're starting with
                    if token.type == "title":
                        initial_title = "(starting)"
                    elif token.type == "thinking":
                        initial_title = "(thinking...)"
                    else:
                        initial_title = "(coding...)"

                    with self.expansion:
                        self.current_action.card = (
                            ui.html(
                                ActionEvent(
                                    agent_name=self.current_action.agent_name,
                                    full_namespace=self.current_action.full_namespace,
                                    timestamp=self.current_action.timestamp,
                                    title=initial_title,
                                    thinking="",
                                    code="",
                                )._repr_html_(),
                                sanitize=False,
                            )
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

                self.update_expansion_label()
                self.current_action.card.set_content(self.current_action.render_html())
                self.current_action.card.update()

                if token.type == "python" and token.done:
                    # Clear card reference so next title starts fresh
                    self.current_action.card = None

            except Exception as e:
                import traceback
                traceback.print_exc()

        asyncio.run_coroutine_threadsafe(do_ui_update(), self.loop)
