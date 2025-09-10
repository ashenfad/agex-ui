# Capabilities Primer
# agent: chat
# fingerprint: 8c5d601a
# target_chars: 16000
# model: gpt-4.1
# created_at: 2025-09-09T04:31:42.623498+00:00

# Capabilities Primer for NiceGUI + Standard Library Integration

This guide describes typical usage patterns and guidance for leveraging NiceGUI UI components in conjunction with standard Python library utilities. The primary focus is on the **`nicegui.ui`** module and standard modules like `math`, `random`, `statistics`, and familiar data, text, and utility modules. This guide is structured to promote idiomatic, maintainable, and robust NiceGUI apps.

---

## Table of Contents

1. [General Principles](#general-principles)
2. [UI Creation and Interactivity](#ui-creation-and-interactivity)
    - [Basic UI Elements (Labels, Buttons, Icons)](#basic-ui-elements-labels-buttons-icons)
    - [Layouts & Containers](#layouts--containers)
    - [Input Controls](#input-controls)
    - [Feedback & Notifications](#feedback--notifications)
    - [Rich Content Display](#rich-content-display)
    - [Tabular Data and Grids](#tabular-data-and-grids)
    - [Media: Images, Audio, Video](#media-images-audio-video)
    - [Charts and Plots](#charts-and-plots)
    - [Advanced: 3D, Maps, Scenes](#advanced-3d-maps-scenes)
    - [Navigation and Routing](#navigation-and-routing)
3. [Event Handling Patterns](#event-handling-patterns)
    - [Event Handlers and the UI](#event-handlers-and-the-ui)
    - [Global Events](#global-events)
    - [Timers and Refresh](#timers-and-refresh)
4. [State, Data, and Computations](#state-data-and-computations)
    - [State Management](#state-management)
    - [Working with Pandas and DataFrames](#working-with-pandas-and-dataframes)
    - [General Python Utilities](#general-python-utilities)
5. [Element Management, Styling, Slots](#element-management-styling-slots)
6. [Dynamic Resources and Extension](#dynamic-resources-and-extension)
7. [Custom JS, CSS, HTML Injection](#custom-js-css-html-injection)
8. [Best Practices and Patterns](#best-practices-and-patterns)
---

## General Principles

- **Import only required modules**: Use `import nicegui.ui as ui` or `import nicegui.ui` for UI elements, and import standard libraries as needed.
- **UI state and computation are separate**: Let the UI display and user input trigger changes, use Python code (math, pandas, etc.) to process or compute.
- **All interactivity is synchronous**: Avoid using async and await except where NiceGUI expects it (e.g., for certain API calls).

---

## UI Creation and Interactivity

The `nicegui.ui` module provides most of the UI toolkit you need. UI elements are constructed and then can be customized, responded to, and updated in response to user actions.

### Basic UI Elements (Labels, Buttons, Icons)

These are the building blocks for your interface:

- `ui.label(text)`: Displays static text.
- `ui.button(text, on_click=callback[, color, icon])`: Actionable button with optional callback.
- `ui.icon(name[, color, size])`: Iconography, use for decoration or signaling.
- `ui.badge(text[, color])`: Small, visually distinct markers for counts or statuses.
- `ui.chip(text[, icon, color])`: Interactive, optionally selectable tokens.

**Actionable Guidance**:

- Use `.on('click', handler)` to attach handlers where available if you need more than the default.
- Use `.set_text()`, `.set_icon()` etc. to change the appearance of buttons, badges, chips after creation.
- Use `.tooltip()` to provide contextual info.
- Use color and icon to signal status; prefer consistency.

**Example:**

```python
import nicegui.ui as ui

def greet():
    ui.notify('Hello!')

ui.button('Greet', on_click=greet, color='primary', icon='thumb_up')
ui.label('Welcome to the demo app')
```

---

### Layouts & Containers

Compose elements with these primitives:

- **Card**: `ui.card()...` for visually distinct sections, with `ui.card_section`, `ui.card_actions`.
- **Row/Column/Grid**: Use `ui.row()`, `ui.column()`, `ui.grid()` to arrange children linearly or in a grid.
- **List/Menu**: `ui.list()`, `ui.menu()` with `ui.item()`s for navigable or actionable menus.
- **Expansion/Collapse**: `ui.expansion()...` for expandable/collapsible panels.
- **Tabs/Tab Panels**: `ui.tabs()`, `ui.tab_panels()`, `ui.tab()`, `ui.tab_panel()`.
- **Splitter**: `ui.splitter()` to create resizable divisions of space.
- **Page Layout**: `ui.header()`, `ui.footer()`, `ui.drawer()`, `ui.left_drawer()`, `ui.right_drawer()`, `ui.space()` (fills space in a flex container).

**Pattern: Use container elements as context managers for automatic structure:**

```python
with ui.card():
    ui.label('Inside a card')
    with ui.card_section():
        ui.label('Section Content')
```

**Styling containers**: Use `.classes()`, `.style()`, and `.props()` for presentation details; prefer standard Tailwind or Quasar classes.

---

### Input Controls

Use input elements to get user data.

- **Textual Inputs**: `ui.input()`, `ui.textarea()`, `ui.code()`, `ui.codemirror()`, `ui.editor()` (rich text).
- **Numbers**: `ui.number()`, `ui.slider()`, `ui.knob()`, `ui.range()`.
- **Selections**: `ui.select()`, `ui.toggle()`, `ui.radio()`, `ui.input_chips()`. For on/off: `ui.checkbox()`, `ui.switch()`.
- **Dates & Times**: `ui.date()`, `ui.time()`.
- **Color**: `ui.color_input()`, `ui.color_picker()`.
- **Rating**: `ui.rating()`.
- **File Upload**: `ui.upload()`.

Bind values using:
- The `on_change` or `.on('update:model-value', callback)` pattern for custom value handling.
- Use `.value` attribute or `.set_value()` to read/set programmatically.
- For more validation, pass `validation=` argument or use `.validate()`/`.without_auto_validation()`.

**Example:**

```python
def changed(e):
    ui.notify(f'New value: {e.value}')

ui.input('Your name', on_change=changed)
```

---

### Feedback & Notifications

- Use `ui.notify(msg)` for toasts, or `ui.notification(...)` for advanced control.
- Progress bars: `ui.circular_progress()`, `ui.linear_progress()`.
- Spinners: `ui.spinner()`.
- Log view: `ui.log()`.
- Skeleton loaders: `ui.skeleton()` for loading placeholders.

**Pattern**: Update the notification/progress programmatically as tasks proceed.

---

### Rich Content Display

- **Markdown/HTML**: `ui.markdown()`, `ui.html()`, `ui.restructured_text()`.
- **Code/Highlighting**: `ui.code()`, `ui.codemirror()` for syntax highlighting and editing.
- **Mermaid diagrams**: `ui.mermaid()`.
- **JSON Editor**: `ui.json_editor()`.

To render content:
- Update with `.set_content()`, `.update()` or `.bind_content_from(...)` as needed.
- Use `.tooltip()` to enhance.

---

### Tabular Data and Grids

- `ui.table(rows, columns=...)` for classic data tables.
    - Use `.add_row()`, `.add_rows()`, `.update_rows()`, `.remove_row()`, etc.
    - Use `.from_pandas(df)`, `.update_from_pandas(df)` for pandas DataFrames.
- `ui.aggrid(options, ...)` for advanced grid with filtering/editing, or `ui.aggrid.from_pandas(df)`/`.from_polars(df)` for fast DataFrame display.
    - Work with `.get_client_data()`, `.get_selected_row[s]()`, and use AG Grid APIs via `.run_grid_method()` as needed.

**Guidance**:
- Prefer `ui.table.from_pandas()` and `ui.aggrid.from_pandas()` when working with DataFrames.
- Use `on_select` or `.on('select', handler)` for row selection.
- For editable tables, sync back to the server with `.get_client_data()`.

**Example:**

```python
import pandas as pd
df = pd.DataFrame({'a': [1,2,3], 'b': [4,5,6]})
table = ui.table.from_pandas(df)
```

---

### Media: Images, Audio, Video

- **Image**: `ui.image(source)`, supports URLs, files, PIL images, etc.
- **Interactive Image**: `ui.interactive_image(source, on_mouse=callback)` for image + SVG overlays and mouse events.
- **Audio/Video**: `ui.audio(src)`, `ui.video(src)`.
    - Use `.play()`, `.pause()`, `.seek(secs)`, `.set_source(src)` as needed.
    - `on(type='event_name', handler)` for event listening.

**Hint**: Use Interactive Image if you need real-time updates (e.g., for video stream thumbnails).

---

### Charts and Plots

- **Plotly**: `ui.plotly(figure)` for interactive charts, update with `.update_figure()`.
- **ECharts**: `ui.echart(options, ...)` for flexible charting (pie, bar, scatter, etc.), with `on_point_click` callbacks.
- **Line Plot**: `ui.line_plot()`, `push(x, Y, ...)` for streaming data.
- **Matplotlib/Pyplot**: `ui.matplotlib()` and `ui.pyplot()` for scriptable traditional plots.
- **Highcharts**: `ui.highchart()` (if separately installed).

**Pattern**: When updating data, push new figure/options and call `.update()` if required.

---

### Advanced: 3D, Maps, Scenes

- **3D Scene**: `ui.scene()` (Three.js), for 3D geometric visualizations and interaction.
- **Scene View**: `ui.scene_view(scene)`.
- **Map**: `ui.leaflet(center, zoom, ...)` for OpenStreetMap or custom tile maps.
    - Use various layer adding methods (`marker`, `tile_layer`, `image_overlay`, etc.)

**Usage**: Respond to interaction with .on_click or .on_drag_start etc.

---

### Navigation and Routing

- Use `ui.link(text, target=...)` for navigation between pages or anchors.
- `ui.page(path)(builder_function)` decorator to register new app routes.
- `ui.sub_pages({...})` for single-page application (SPA) client-side routing.
- Use `ui.link_target(name)` to define anchors for intra-page navigation.

---

## Event Handling Patterns

### Event Handlers and the UI

- **Attach events**: Use `.on(event_type, handler)` or constructor `on_*` arguments.
- **Common event names**: `'click'`, `'update:model-value'`, `'value-change'`, `'change'`, etc.
- Event handler signature: Often either `callback(event_args)` or just `callback()`.
- For certain input widgets, handler is called with a `ValueChangeEventArguments` object.

**Pattern**:

```python
def handle_change(event):
    ui.notify(f'Changed to {event.value}')

some_input_widget.on('update:model-value', handle_change)
```

### Global Events

You can attach global event listeners:
```python
ui.on('keydown', handler)
```

Or use `ui.keyboard(on_key=callback)` for key events, `ui.timer(...)` for timers.

### Timers and Refresh

- Use `ui.timer(interval, callback)` to run periodic background tasks (e.g., for updating data, refreshing plots).
- Use `.activate()`, `.deactivate()` to control.

---

## State, Data, and Computations

### State Management

Use `ui.state(value)` to create and track state that auto-refreshes relevant UI containers.

```python
counter, set_counter = ui.state(0)
ui.label(f'Count: {counter}')
ui.button('Increment', on_click=lambda: set_counter(counter + 1))
```

Or use classic Python variables if not using state-bound containers.

### Working with Pandas and DataFrames

- Prefer `ui.table.from_pandas(df)` or `ui.aggrid.from_pandas(df)` to visualize DataFrames.
- Use `pandas` for manipulation, filtering, grouping, calculations.
- For changes: update your DataFrame, then `.update_from_pandas(df)`.

### General Python Utilities

All standard modules such as `math`, `random`, `statistics`, `decimal`, `fractions`, `datetime`, `re`, `string`, `textwrap`, `json`, and more are available for processing data.

**Pattern**: Do all calculations, validation, and formatting in Python, only updating the UI as needed.

---

## Element Management, Styling, Slots

### Adding and Removing Children

- Use `.clear()` to remove all children from a container.
- Use `.remove(element)` to remove a specific child.
- Use `.delete()` to remove an element and all its descendants.
- Use `.move(target, index, slot)` to reposition elements within containers.

### Styling and Props

- `.classes(add='myclass')` to add CSS classes (supports tailwind and quasar).
- `.props(add='prop1 prop2')` to add/remove component props/attributes.
- `.style(add='background: red;')` to add inline style.
- Use `.tooltip()`, `.default_classes()`, `.default_props()`, `.default_style()` for element class-wide defaults (set before element creation).

### Slots

Organize complex layouts using slots.
- Use `.add_slot(name)` to create and enter additional named slot.
- Nest other UI creation inside slots using with-contexts.

---

## Dynamic Resources and Extension

- `.add_dynamic_resource(name, function)`: Bind a function as a dynamic resource (for dynamic serving).
- `.add_resource(path)`: Add resource directories for CSS or JS (to include custom or external assets).

---

## Custom JS, CSS, HTML Injection

- Use `ui.add_head_html(code)`, `ui.add_body_html(code)` to insert arbitrary HTML.
- Use `ui.add_css(content)`, `ui.add_scss(content)` or `ui.add_sass(content)` for adding custom styles.
- Use `ui.run_javascript(code)` to execute arbitrary JS on the page (rarely necessary, but useful for integration scenarios).

---

## Best Practices and Patterns

- Use `ui.notify()` for user feedback, avoid print() in handler code.
- For *reactive* UI, use `ui.state()` or `@ui.refreshable` to structure logic.
- Use slots for advanced layout control but prefer simple layouts for maintainability.
- Validate user input either via the widget's own validation parameter or in callback.
- For large updates, `.update()` will re-render an element.
- Chainable methods: Many methods return the element allowing chaining (e.g., `ui.button('OK').classes('myclass').tooltip('Confirm')`)

---

## Canonical Usage Snippets

**Complex UI with DataFrame Table and Plot**:

```python
import nicegui.ui as ui
import pandas as pd
import plotly.graph_objs as go

df = pd.DataFrame({'time': range(10), 'value': [x**2 for x in range(10)]})

with ui.row():
    t = ui.table.from_pandas(df)
    f = go.Figure(data=[go.Scatter(x=df['time'], y=df['value'])])
    p = ui.plotly(f)

def update_table_and_plot():
    # ... compute new df, new f ...
    t.update_from_pandas(df)
    p.update_figure(f)

ui.timer(1, update_table_and_plot)
```

**Slot-based Layout**

```python
with ui.card():
    with ui.card_section():
        ui.label('Dashboard')
    with ui.card_actions():
        ui.button('Action', on_click=lambda: ui.notify('Clicked!'))
```

**Event Handling with Input**

```python
def on_change(event):
    ui.notify('Changed to: ' + str(event.value))
ui.input(label='Name', on_change=on_change)
```

**Image Display and Interactive Markup**

```python
def on_img_click(e):
    ui.notify(f'Clicked at: {e.image_x}, {e.image_y}')

ui.interactive_image('https://url.com/image.png', on_mouse=on_img_click)
```

**Injecting Custom CSS**

```python
ui.add_css("""
.mycustomclass {
  background: pink;
}
""")
```

---
## Summary Table: Key Methods Across Elements

| Category          | Methods                                                     | Use-case Example                   |
|-------------------|------------------------------------------------------------|------------------------------------|
| **Visibility**    | `.set_visibility()`, `.bind_visibility...()`               | Show/hide based on state           |
| **Binding**       | `.bind_value...()`, `.bind_text...()`, etc                 | Sync element property with Python  |
| **Event**         | `.on('event', handler)`, `.on_click()`, `.on_value_change()` | Attach callbacks                   |
| **Update**        | `.set_value()`, `.set_text()`, `.update()`                 | Update UI based on logic           |
| **Structure**     | `.add_slot()`, `.clear()`, `.remove()`, `.move()`, `.delete()`| Arranging and managing hierarchy   |
| **Style/Props**   | `.classes()`, `.default_classes()`, `.props()`, `.style()` | Customize appearance               |
| **JS/HTML/CSS**   | `ui.add_head_html()`, `ui.add_body_html()`, `ui.add_css()` | Custom integration/extensions      |

---

# Closing Advice

Mastering NiceGUI is about combining responsive UI building patterns with idiomatic Python logic. Rely on the Python libraries (`math`, `random`, `statistics`, etc.) for all data manipulations, and only use NiceGUI's UI module methods for display, layout, and user interaction. 

Keep event handling simple, use clear state patterns, and update your UI reactively. When displaying rich data (tables, plots), use the provided helpers to bind your data to the UI. For advanced use cases, slots, custom styling, and direct JavaScript injection are at your disposal.

**Always remember**:

- Prefer NiceGUI-native constructs over raw JavaScript or manual DOM manipulations.
- Structure UI hierarchically using context managers.
- Decouple compute from the UI layer.
- Use built-in validation and feedback mechanisms for robust, user-friendly designs.

For more examples, consult NiceGUI's online documentation and the source code examples—they are an excellent resource for practical idioms and integrations.

---

**End of capabilities primer.**
