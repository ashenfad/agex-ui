"""Calendar assistant chat interface using agex-ui core framework."""

from nicegui import ui, app

from agex_ui.cal.agent import handle_prompt, state
from agex_ui.core.turn import TurnConfig
from agex_ui.templates.chat_interface import ChatInterfaceConfig, create_chat_interface

# Serve static assets
app.add_static_files("/assets", "./assets")

# Configure chat interface
chat_config = ChatInterfaceConfig(
    title="Calendar Assistant",
    page_title="Cal - Agex UI",
    greeting="Hello! I can help you manage your Google Calendar.",
    agent_name="Cal",
    max_width="1000px",
)

# Configure turn execution
turn_config = TurnConfig(
    show_setup_events=False,  # Hide setup events to reduce clutter
    enable_token_streaming=True,
    auto_scroll=True,
    collapse_agent_activity=True,
)

# Create the chat interface
chat_messages, chat_input = create_chat_interface(
    agent_task=handle_prompt,
    state=state,
    config=chat_config,
    turn_config=turn_config,
)

# Run the app...
# But you'll need oauth for google calendar access!
# See https://google-calendar-simple-api.readthedocs.io/en/latest/getting_started.html#credentials
ui.run()
