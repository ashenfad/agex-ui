"""Calendar assistant chat interface using agex-ui core framework."""

from nicegui import app, ui

from agex_ui.cal.agent import agent, handle_prompt
from agex_ui.core.turn import TurnConfig
from agex_ui.templates.chat_interface import ChatInterfaceConfig, create_chat_interface

# Serve static assets
app.add_static_files("/assets", "./assets")

# Configure chat interface
chat_config = ChatInterfaceConfig(
    title="Calendar Assistant",
    page_title="Cal",
    greeting="Hello! I can help you manage your Google Calendar.",
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
chat_messages, chat_input, theme_manager = create_chat_interface(
    agent=agent,
    agent_task=handle_prompt,
    config=chat_config,
    turn_config=turn_config,
)

# You'll need OAuth for Google Calendar access!
# See https://google-calendar-simple-api.readthedocs.io/en/latest/getting_started.html#credentials
ui.run(favicon="📅")
