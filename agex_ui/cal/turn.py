import asyncio
from datetime import datetime
from nicegui import ui
from agex import Event, ActionEvent, OutputEvent, TaskClarify, TaskFail, TaskTimeout
from agex_ui.cal.agent import handle_prompt, state
import plotly.graph_objects as go
import pandas as pd


def get_timestamp() -> str:
    return datetime.now().strftime("%-I:%M:%S %p")


async def scroll_chat_to_bottom(chat_container: ui.column):
    """Scroll the chat container to the bottom with proper timing."""
    await asyncio.sleep(0.11)  # Wait for DOM to update per NiceGUI discussion
    with chat_container:
        ui.run_javascript(
            "document.getElementById('chat-messages-container').scrollTop = 999999"
        )


def _to_component(result: str | pd.DataFrame | go.Figure):
    match result:
        case pd.DataFrame():
            ui.table.from_pandas(result).classes("w-full")
        case go.Figure():
            ui.plotly(result).classes("w-full h-80").style("width: 640px")
        case _:
            ui.markdown(
                result, extras=["fenced-code-blocks", "tables", "cuddled-lists"]
            )


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

    def on_agent_event(evt: Event):
        """A thread-safe callback to handle agent events."""
        print("Event received: ", evt)
        nonlocal current_expansion, event_count
        if not isinstance(evt, (ActionEvent, OutputEvent)):
            return

        async def do_ui_update():
            """This coroutine will be executed on the main UI loop."""
            nonlocal current_expansion, event_count

            # Add event to the current expansion
            event_count += 1
            current_expansion.text = f"Agent Activity ({event_count} events)"

            with current_expansion:
                ui.html(evt.as_html()).classes("w-full p-0 my-0")

        # Safely schedule the UI update on the main loop from the background thread.
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
            handle_prompt, prompt, on_event=on_agent_event, state=state
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
