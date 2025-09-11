# agex-ui: Agent-Driven UIs with NiceGUI

This repository demonstrates how the [`agex`](https://ashenfad.github.io/agex/) framework can be used to create dynamic, agent-driven user interfaces with [NiceGUI](https://nicegui.io/).

The core concept is to give an AI agent direct, sandboxed access to the NiceGUI library, allowing it to build and modify a user interface at runtime in response to natural language prompts.

For a deep-dive check the assicated [blog post](http://127.0.0.1:8000/agex/blog/2025/09/11/deep-dive-building-an-agent-driven-ui-with-agex-ui/).

## Demo 1: Interactive Chat UI

In the [agex_ui/chat](agex_ui/chat/) demo an agent builds and renders UI components (forms, buttons, etc.) directly into the conversation. These components can act as forms, providing structured data back to the agent upon submission for subsequent actions.

Video:

<a href="https://youtu.be/-LaY_QBfkf8">
  <img src="resources/chat.png" width="400" alt="Watch the Agex-UI Demo">
</a>


# Demo 2: Dynamic Page Generation

In the [agex_ui/lorem_ipsum](agex_ui/lorem_ipsum/) demo, an agent to dynamically generates entire pages on the fly for any visited URL (e.g., `/dashboard`, `/profile`), complete with layouts and data visualizations.

Result for `http://127.0.0.1:8080/weather/albany/or`:

<img src="resources/lorem.png" width="400" alt="Notional weather page">

## Running the Demos

First, set up the environment:

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install the project and its dependencies
pip install -e .
```

Then, run one of the examples:

```bash
# To run the chat interface
python -m agex_ui.chat.main

# To run the dynamic page generator
python -m agex_ui.lorem_ipsum.main
```

## The Technical Approach: Bypassing the Tool-Layer

Most agentic frameworks rely on a "tool-layer" abstraction. To allow an agent to build a UI, a developer would need to write explicit wrapper functions (tools) with JSON schemas for every UI component they want the agent to use:

```python
# Traditional approach: A predefined, rigid tool
@agent.tool
def create_button(text: str, color: str, on_click_handler: str):
    """Creates a button with limited, predefined options."""
    # ... logic to create a button from JSON ...
    pass
```

But this doesn't scale well to complex nested components. The ability for an agent
to compose is lost.

`agex` takes a different approach by providing the agent with direct, runtime access to Python libraries. Instead of defining tools, you register the `nicegui` module itself. The agent then writes Python code to call the NiceGUI API directly (while remaining sandboxed):

```python
# (Code an agex agent might generate)

with inputs.col:
    ui.label("Custom Analysis").classes("text-2xl")

    # The agent has access to any NiceGUI component and configuration
    data_input = ui.input("Enter data source")
    chart_type = ui.select(["bar", "line", "pie", "scatter"])
    
    # The agent can compose components and lambda functions
    ui.button("Generate", on_click=lambda: form_submit({
        'data': data_input.value,
        'chart': chart_type.value
    }))

task_success()
```

This allows the agent to combine components, create layouts, and handle interactions in ways not predefined by the developer, enabling novel UI structures at runtime.

For more, see [https://ashenfad.github.io/agex/](https://ashenfad.github.io/agex/).