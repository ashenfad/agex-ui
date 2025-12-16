# agex-ui: Production-Ready Agent-Driven UIs

A clean, reusable framework for building agent-driven user interfaces with [`agex`](https://ashenfad.github.io/agex/) and [NiceGUI](https://nicegui.io/).

**agex-ui** provides production-ready components for creating chat interfaces where AI agents can respond with rich, multi-type outputs including text, dataframes, and plotly visualizations—all with real-time streaming of agent activity.

## Features

✨ **Multi-Type Responses**: Agents can return text (markdown), pandas DataFrames, and Plotly figures in a single response  
🎯 **Agent-Agnostic Core**: Works with any agex task function—bring your own agent  
⚡ **Real-Time Streaming**: Token-by-token rendering of agent actions with thinking and code blocks  
🎨 **Collapsible Activity View**: Agent events displayed in organized, expandable sections  
🔧 **Highly Configurable**: Customize appearance, behavior, and rendering via dataclass configs

## Architecture

```
agex_ui/
├── core/           # Reusable framework components
│   ├── responses.py    # Response type system (Response, ResponsePart, etc.)
│   ├── renderers.py    # UI renderers for responses and events
│   ├── events.py       # Event handling and token streaming
│   └── turn.py         # Turn orchestration (run_agent_turn)
├── templates/      # UI templates
│   └── chat_interface.py  # Standard chat interface template
└── cal/            # Calendar assistant example
    ├── agent.py        # Agent definition with calgebra integration
    ├── main.py         # Application entry point
    ├── primer.py       # Agent system prompts
    └── utils.py        # Calendar-specific utilities
```

## Quick Start

### Installation

```bash
# Clone and install
git clone https://github.com/ashenfad/agex-ui.git
cd agex-ui
pip install -e .
```

### Running the Calendar Assistant

```bash
python -m agex_ui.cal.main
```

Then open your browser to the displayed URL (typically `http://localhost:8080`).

> [!WARNING]
> **Configuration Required**: This example requires valid [Google Calendar credentials](https://google-calendar-simple-api.readthedocs.io/en/latest/getting_started.html#credentials) and a configured [LLM provider](https://ashenfad.github.io/agex/api/agent/#llm-configuration).

## Building Your Own Agent-Driven UI

Here's how to create a custom agent-driven chat interface:

### 1. Define Your Agent Task

```python
# my_agent.py
from agex import Agent, connect_llm
from agex_ui.core.responses import Response
import pandas as pd

agent = Agent(
    name="my_agent",
    primer="You are a helpful assistant...",
    llm_client=connect_llm(provider="anthropic", model="claude-haiku-4-5"),
)

# Register the Response type
agent.cls(Response)

@agent.task
def handle_prompt(prompt: str) -> Response:
    """Process user prompt and return a multi-part response."""
    # Your agent logic here
    return Response(parts=[
        "Here's your analysis:",
        pd.DataFrame({"col1": [1, 2, 3]}),
    ])
```

### 2. Create the Chat Interface

```python
# main.py
from nicegui import ui, app
from agex_ui.templates import create_chat_interface, ChatInterfaceConfig
from agex_ui.core.turn import TurnConfig
from my_agent import handle_prompt

app.add_static_files("/assets", "./assets")

# Create interface
chat_messages, chat_input = create_chat_interface(
    agent_task=handle_prompt,
    config=ChatInterfaceConfig(
        title="My Agent App",
        page_title="My App",
        greeting="Hello! How can I help?",
    ),
    turn_config=TurnConfig(
        show_setup_events=False,
        enable_token_streaming=True,
    ),
)

ui.run()
```

That's it! You now have a full-featured agent-driven chat interface.

## Response Types

Agents can return any combination of:

- **Text (str)**: Rendered as markdown
- **DataFrames (pd.DataFrame)**: Rendered as interactive tables
- **Plotly Figures (go.Figure)**: Rendered as interactive charts
- **Response**: Multi-part container for combining types

```python
from agex_ui.core.responses import Response

# Single type
return "Simple text response"

# Multiple types in one response
return Response(parts=[
    "Analysis complete:",
    dataframe,
    plotly_figure,
    "Additional notes...",
])
```

## Configuration Options

### ChatInterfaceConfig

Customize the chat interface appearance:

```python
ChatInterfaceConfig(
    header_bg_color="#5894c8",     # Header background color
    title="My App",                 # Header title
    page_title="My App",            # Browser page title
    max_width="900px",              # Chat container width
    greeting="Welcome!",            # Initial bot message
    robot_avatar="assets/robot.png",
    human_avatar="assets/human.png",
    agent_name="MyAgent",
)
```

### TurnConfig

Customize turn execution behavior:

```python
TurnConfig(
    show_setup_events=False,        # Show/hide agent setup events
    enable_token_streaming=True,    # Enable real-time token streaming
    auto_scroll=True,                # Auto-scroll to new messages
    collapse_agent_activity=True,   # Start with activity collapsed
)
```

## The Calendar Assistant Example

The included `cal` package demonstrates a production-ready agent that manages Google Calendar using the `calgebra` library. It showcases:

- Complex agent setup with multiple library registrations
- Domain-specific helper functions
- Rich responses combining text, tables, and visualizations
- Custom primer engineering for calendar operations

See [`agex_ui/cal/`](agex_ui/cal/) for the implementation.

## Design Philosophy

**Agent-Agnostic Core**: The framework doesn't create or configure agents. You define your agent with domain-specific setup, then pass its task function to the UI framework.

**Separation of Concerns**:
- **Core**: UI orchestration, rendering, event handling (framework layer)
- **Templates**: Reusable layouts and configurations (presentation layer)
- **Your Agent**: Domain logic, tools, prompts (application layer)

This architecture ensures the framework remains flexible and reusable across different agent implementations.

## Learn More

- **agex Documentation**: [ashenfad.github.io/agex/](https://ashenfad.github.io/agex/)
- **NiceGUI Documentation**: [nicegui.io](https://nicegui.io/)
- **Blog Post**: Building Agent-Driven UIs with agex (coming soon)

## License

MIT License - See [LICENSE](LICENSE) file for details.