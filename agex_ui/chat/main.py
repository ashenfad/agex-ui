from typing import Any
from nicegui import ui, app
from agex_ui.chat.agent import agent
import asyncio

from agex_ui.chat.turn import get_timestamp, run_agent_turn

app.add_static_files("/assets", "./assets")


# Configure the main window
ui.query("body").style(
    "background-color: #fcfcfc; display: flex; flex-direction: column; align-items: center; height: 100vh; margin: 0;"
)
ui.page_title("Agex-UI")
with (
    ui.header(elevated=False)
    .style("background-color: #5894c8;")
    .classes("items-center justify-between")
):
    ui.label("Agex-UI").classes("text-2xl")

# Main content area - full width chat
with ui.column().classes("w-full h-full p-4").style("flex-grow: 1; width: 900px;"):
    # Chat messages area that grows and scrolls
    chat_messages = (
        ui.column()
        .classes("w-full overflow-auto p-4")
        .style("height: 75vh; max-height: 75vh;")
        .props("id=chat-messages-container")
    )
    with chat_messages:
        ui.chat_message(
            "Hello! How can I help you today?",
            sent=False,
            name="Agex",
            avatar="assets/robot.png",
            stamp=get_timestamp(),
        ).props("bg-color=blue-2")

    # Chat input area at the bottom
    with ui.row().classes("w-full items-center p-2 border-t"):
        chat_input = ui.input(placeholder="Type your request...").classes("flex-grow")


# Allows the agent to bind 'form_submit' to buttons, etc.
@agent.fn
def form_submit(bound_vars: dict[str, Any]):
    """
    Use as a trigger for form submissions.
    """
    try:
        # Get the currently running asyncio event loop (which is the NiceGUI loop)
        loop = asyncio.get_running_loop()
        # Schedule the async run_agent_turn coroutine to run on the loop
        loop.create_task(
            run_agent_turn(chat_messages, chat_input, bound_vars=bound_vars)
        )
    except RuntimeError:
        # Fallback for safety, though this shouldn't happen in NiceGUI
        asyncio.run(run_agent_turn(chat_messages, chat_input, bound_vars=bound_vars))


async def _handle_chat_input():
    """Handler for when user presses enter in the chat input."""
    await run_agent_turn(chat_messages, chat_input, prompt=chat_input.value)


chat_input.on("keydown.enter", _handle_chat_input)

ui.run()
