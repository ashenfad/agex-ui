import asyncio
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
from agex import ActionEvent, Event, OutputEvent, TaskClarify, TaskFail, TaskTimeout
from agex.llm.core import StreamToken
from nicegui import ui
from nicegui.elements.html import Html

from agex_ui.cal.agent import Response, agent, handle_prompt, state


def get_timestamp() -> str:
    return datetime.now().strftime("%-I:%M:%S %p")


async def scroll_chat_to_bottom(chat_container: ui.column):
    """Scroll the chat container to the bottom with proper timing."""
    await asyncio.sleep(0.11)  # Wait for DOM to update per NiceGUI discussion
    with chat_container:
        ui.run_javascript(
            "document.getElementById('chat-messages-container').scrollTop = 999999"
        )


def _to_component(result: str | pd.DataFrame | go.Figure | Response):
    match result:
        case Response():
            # Render each part of a multi-part response
            for part in result.parts:
                _to_component(part)
        case pd.DataFrame():
            ui.table.from_pandas(result).classes("w-full")
        case go.Figure():
            ui.plotly(result).classes("w-full h-80").style("width: 640px")
        case _:
            ui.markdown(
                str(result), extras=["fenced-code-blocks", "tables", "cuddled-lists"]
            )


@dataclass
class ActionRenderState:
    title_parts: list[str] = field(default_factory=list)
    thinking_parts: list[str] = field(default_factory=list)
    code_parts: list[str] = field(default_factory=list)
    card: Html | None = None
    agent_name: str = ""
    full_namespace: str = ""
    timestamp: datetime | None = None


async def run_agent_turn(
    chat_messages: ui.column,
    chat_input: ui.input,
    prompt: str,
):
    """Run one turn of agent interaction after a user prompt."""

    with chat_messages:
        ui.chat_message(
            prompt,
            sent=True,
            name="You",
            avatar="assets/human.png",
            stamp=get_timestamp(),
        ).classes("self-end")
    chat_input.value = ""  # Clear input immediately for better UX

    await scroll_chat_to_bottom(chat_messages)

    # Get the current asyncio event loop, which is the main UI loop.
    loop = asyncio.get_running_loop()

    # Create agent activity expansion first
    with chat_messages:
        current_expansion = ui.expansion("Agent Activity", icon="psychology").classes(
            "w-full border border-gray-200 rounded-lg text-gray-500"
        )
        current_expansion.value = False  # Start collapsed

    # Reset event count for new user interaction
    event_count = 0
    current_action_title = ""

    def _update_activity_label():
        nonlocal current_expansion
        label = "Agent Activity"
        if current_action_title:
            label = f"{label} — {current_action_title}"
        label = f"{label} ({event_count} events)"
        current_expansion.text = label

    def on_agent_event(evt: Event):
        """A thread-safe callback to handle agent events."""
        print("Event received: ", evt)
        nonlocal current_expansion, event_count
        if not isinstance(evt, OutputEvent):
            return

        async def do_ui_update():
            """This coroutine will be executed on the main UI loop."""
            nonlocal current_expansion, event_count

            # Add event to the current expansion
            event_count += 1
            _update_activity_label()

            with current_expansion:
                ui.html(evt.as_html()).classes("w-full p-0 my-0")

        # Safely schedule the UI update on the main loop from the background thread.
        asyncio.run_coroutine_threadsafe(do_ui_update(), loop)

    # Track the in-flight action assembled from token stream
    current_action = ActionRenderState()

    def _render_action_html() -> str:
        fallback_name = current_action.agent_name or agent.name
        fallback_namespace = current_action.full_namespace or fallback_name
        return ActionEvent(
            agent_name=fallback_name,
            full_namespace=fallback_namespace,
            timestamp=current_action.timestamp or datetime.now(),
            title="".join(current_action.title_parts).strip(),
            thinking="".join(current_action.thinking_parts),
            code="".join(current_action.code_parts),
        )._repr_html_()

    def on_agent_token(token: object):
        """Stream token chunks into an ActionEvent-style card."""
        if not isinstance(token, StreamToken):
            return

        async def do_ui_update():
            nonlocal event_count, current_action_title

            # Start a new action when a new title section begins
            if token.type == "title" and token.start:
                current_action.title_parts.clear()
                current_action.thinking_parts.clear()
                current_action.code_parts.clear()
                current_action.agent_name = token.agent_name or agent.name
                current_action.full_namespace = (
                    token.full_namespace or current_action.agent_name
                )
                current_action.timestamp = token.timestamp

                with current_expansion:
                    current_action.card = (
                        ui.html(
                            ActionEvent(
                                agent_name=current_action.agent_name,
                                full_namespace=current_action.full_namespace,
                                timestamp=current_action.timestamp,
                                title="(starting)",
                                thinking="",
                                code="",
                            )._repr_html_()
                        )
                        .classes("w-full p-0 my-0")
                        .style("transition: opacity 120ms ease-in")
                    )

                event_count += 1
                current_action_title = "(starting)"
                _update_activity_label()

            # No card means nothing to update yet
            if current_action.card is None:
                return

            if token.type == "title":
                current_action.title_parts.append(token.content)
                new_title = "".join(current_action.title_parts).strip()
                if new_title:
                    current_action_title = new_title
            elif token.type == "thinking" and not token.done:
                current_action.thinking_parts.append(token.content)
            elif token.type == "python" and not token.done:
                current_action.code_parts.append(token.content)

            _update_activity_label()
            current_action.card.set_content(_render_action_html())
            current_action.card.update()

            if token.type == "python" and token.done:
                # Clear current action card reference so the next title starts fresh
                current_action.card = None

        asyncio.run_coroutine_threadsafe(do_ui_update(), loop)

    # Create the agent response immediately with a spinner
    with chat_messages:
        with (
            ui.chat_message(name="Agex", sent=False, avatar="assets/robot.png")
            .classes("w-full")
            .props("bg-color=blue-2") as agent_message
        ):
            with ui.row().classes("items-center"):
                ui.spinner(size="sm", type="dots")

    # Run the prompt handling task in a background thread
    try:
        result = await asyncio.to_thread(
            handle_prompt,
            prompt,
            on_event=on_agent_event,
            on_token=on_agent_token,
            state=state,
        )
    except (TaskClarify, TaskFail) as e:
        result = e.message
    except TaskTimeout as e:
        result = "Sorry, I got stuck. Please try again."

    # Replace spinner with actual content
    with agent_message:
        agent_message.clear()
        _to_component(result)

    # Set the stamp now that the agent's response is ready
    agent_message.props(f'stamp="{get_timestamp()}"')
    agent_message.update()

    # Auto-scroll for all agent responses
    await scroll_chat_to_bottom(chat_messages)
