"""Calendar assistant chat interface using agex-ui core framework."""

from nicegui import app, ui

from agex_ui.tmnt.agent import agent, handle_prompt
from agex_ui.core.turn import TurnConfig
from agex_ui.templates.chat_interface import ChatInterfaceConfig, create_chat_interface

# Serve static assets
app.add_static_files("/assets", "./assets")

# Configure chat interface
chat_config = ChatInterfaceConfig(
    title="TMNT Calendar Helper",
    page_title="TMNT",
    greeting="Hello! Need help with the turtles' schedules?",
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

# Run the app with turtle emoji favicon
ui.run(favicon="🐢")
