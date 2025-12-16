"""Agex-UI: Agent-driven UIs with agex and NiceGUI.

This package provides a production-ready framework for building agent-driven
user interfaces using agex and NiceGUI.

Core Components:
    - agex_ui.core: Reusable components (responses, renderers, events, turn orchestration)
    - agex_ui.templates: UI templates (chat interface)
    - agex_ui.cal: Calendar assistant example

Quick Start:
    >>> from agex_ui.templates import create_chat_interface, ChatInterfaceConfig
    >>> from agex_ui.core.turn import TurnConfig
    >>> 
    >>> # Define your agent task (see agex_ui.cal.agent for example)
    >>> def my_task(prompt: str, on_event, on_token, state) -> Response:
    ...     # Your agent logic here
    ...     pass
    >>> 
    >>> # Create chat interface
    >>> chat_messages, chat_input = create_chat_interface(
    ...     agent_task=my_task,
    ...     config=ChatInterfaceConfig(title="My App"),
    ...     turn_config=TurnConfig(),
    ... )
    >>> 
    >>> # Run the app
    >>> from nicegui import ui
    >>> ui.run()
"""

__version__ = "0.2.0"  # Bumped for core framework rebuild
