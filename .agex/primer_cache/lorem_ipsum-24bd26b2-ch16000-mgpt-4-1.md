# Capabilities Primer
# agent: lorem_ipsum
# fingerprint: 24bd26b2
# target_chars: 16000
# model: gpt-4.1
# created_at: 2025-09-09T05:31:31.923217+00:00

# Agent Capabilities Primer: NiceGUI and Python Modules (2024 Edition)

This primer catalogs and clusters patterns of use for the capabilities exposed by your current Python environment. The primary interface is the powerful [NiceGUI](https://nicegui.io/) module and its rich UI components under `nicegui.ui`. This environment also provides classic Python modules for mathematics, data handling, and various infrastructural tasks.

Below is an organized summary of capabilities, deduplicated and de-redundified. Each section provides actionable guidance and code snippets for canonical operations.

---

## 1. NiceGUI UI: Fundamental Patterns

### 1.1 Instantiating UI Elements

All interface components (buttons, tables, dialogs, etc.) are created as instances of their respective classes in `nicegui.ui` (often imported simply as `ui`). To create and place elements:

```python
from nicegui import ui

ui.label('Welcome to the app!')
ui.button('Click me', on_click=lambda: ui.notify('Button pressed'))
ui.input(label='Your name')
ui.table(rows=[{'id': 1, 'name': 'Foo'}, {'id': 2, 'name': 'Bar'}])

ui.run()
```

#### Guidance:
- Instantiate components directly at module level or inside a decorated page function (`@ui.page`).
- Properties such as `label`, `value`, `on_change`, etc. nearly always accept both initial and dynamic updates.
- Most elements support `.update()`, `.set_visibility()`, `.tooltip()`, and have properties for styling and visibility.
- Use feature-specific methods for advanced interaction (e.g., `.clicked()` for buttons, `.on_value_change()` for inputs).

---

### 1.2 Layout and Containers

To organize elements horizontally, vertically, in columns, as cards, or in complex layouts:

```python
with ui.row():
    ui.button('Button 1')
    ui.button('Button 2')

with ui.column(wrap=True):
    ui.label('Column Label')
    ui.input()

with ui.card():
    ui.label('In a card')
    with ui.card_section():
        ui.label('Card section')
```

#### Guidance:
- Use `with` blocks to define child element nesting.
- Elements like `ui.card`, `ui.row`, and `ui.column` provide structure with optional style hooks.
- For grid layouts, use `ui.grid(rows=3, columns=2)`.

---

### 1.3 Visibility, Enabling, and State

##### Show / Hide / Enable / Disable / Binding

All elements offer `.set_visibility(True/False)`, `.enable()`, `.disable()`, and the ability to bind properties to application state.

```python
label = ui.label('Conditional Label')
label.set_visibility(False)

input_box = ui.input('Name')
input_box.disable()
input_box.enable()
```

#### Binding:
Connect an element's property to another variable/object for two-way or one-way updating.

```python
my_var = {'flag': True}
button = ui.button('Go')
button.bind_enabled_from(my_var, 'flag')
```

---

### 1.4 Slotted Composition & Content

NiceGUI supports Vue's slot concept, which allows for complex child placement:

```python
card = ui.card()
with card.add_slot('header'):
    ui.label('Card Header')
with card.add_slot('body'):
    ui.label('Card Body')
```

---

## 2. Event Handling

### 2.1 Events: Generic and Specific

#### Generic `.on()`

Attach handlers to nearly any UI event, both browser- and server-side:

```python
def handler(event):
    print('Event:', event.args)

ui.button('Click me').on('click', handler)
```

#### Specific (Convenience) Methods

Some elements offer shortcut methods like `.on_value_change()` for commonly used events:

```python
ui.input('Email').on_value_change(lambda e: print('Input changed:', e.value))
```

#### Throttling events

Pass `throttle` to `.on()` to limit how often your handler executes.

---

### 2.2 Clicks, Changes, Selections

- **Button**: `.on_click(handler)`; also `await button.clicked()`
- **Table**: `.on_select(handler)`, `.on_pagination_change(handler)`
- **Switch/Checkbox/Slider/Knob**: `.on_value_change(handler)`
- **Input**: `.on_value_change(handler)` or use `.bind_value` for binding

#### Canonical usage:

```python
def select_handler(e):
    selected = e.args
    print('Selected:', selected)

table = ui.table(rows=[...], selection='multiple')
table.on_select(select_handler)
```

---

### 2.3 Special: Keyboard, Timer, Upload, Joystick, Scroll

- **Keyboard events**: `ui.keyboard(on_key=handler)`
- **Timer**: `ui.timer(interval=1, callback=handler, active=True)`
- **File upload**: `ui.upload(on_upload=handler)`
- **Scroll events**: `ui.scroll_area(on_scroll=handler)`
- **Joystick**: `ui.joystick(on_move=handler)`

```python
ui.timer(1.0, lambda: print("Tick!"))
ui.keyboard(on_key=lambda e: print(f"Key {e.key} was pressed."))
```

---

## 3. Value, Property, and State Management

### 3.1 Immediate & Programmatic Update

Elements have `.set_value()`, `.set_text()`, `.set_icon()`, etc., depending on their nature.

```python
lbl = ui.label('Start')
lbl.set_text('Updated!')

inp = ui.input(label='Default')
inp.set_value('New value')
```

### 3.2 Bindings

Elements support bind-property mechanics for two-way, one-way, and reverse binding:

```python
# Two way
checkbox.bind_value(my_model, 'my_bool_var')
# From source
input_box.bind_label_from(my_model, 'dynamic_label')
# To target
slider.bind_value_to(my_model, 'slider_value')
```

Binding is standard for value, text, enabled/visibility, label, icon, and more.

---

## 4. Data Display & Manipulation

### 4.1 Tables

- `ui.table(rows=[...], columns=[...])`
- Support for selection, filtering, pagination, editable cells, dynamic updating
- Can import from Pandas/Polars: `ui.table.from_pandas(df)`

**API Highlights:**

- `.rows`/`.columns` are mutable
- `.add_row()` / `.add_rows()` and `.remove_row()` / `.remove_rows()`
- `.update_rows()`, `.update_from_pandas(df)`, `.update()`
- `.on_select(handler)`, `.on_pagination_change(handler)`
- Computed data: `await table.get_computed_rows_number()`

**Example:**

```python
df = ...  # some DataFrame
table = ui.table.from_pandas(df, selection='single')
table.on_select(lambda e: print('Row selected:', e.args))
```

---

### 4.2 AG Grid

For advanced data grids: `ui.aggrid(options, ...)`
- AG Grid supports rich data interactivity: editing, sorting, filtering.
- You can get and update client-edited data:

```python
ag = ui.aggrid(...)
new_data = await ag.get_client_data()
await ag.load_client_data()
```

---

### 4.3 Tree, Radio, Select/Dropdown, Toggle, Chips, Input Chips

**Tree**

```python
tree = ui.tree(nodes=[...], on_select=handler)
tree.expand()
tree.collapse()
```

**Toggle, Radio, Select**

```python
opts = {'1': 'One', '2': 'Two'}
ui.radio(options=opts, value='1').on_value_change(handler)
ui.select(options=list(opts.values())).on_value_change(handler)
ui.toggle(options=list(opts.keys())).on_value_change(handler)
```

**Chips/Input Chips**

```python
chips = ui.input_chips(value=['A', 'B'])
chips.on_value_change(lambda e: print(e.value))
```

---

## 5. Visualization: Plotting, Charts, and Graphs

### 5.1 Matplotlib, Pyplot, and Line Plot

- **Matplotlib**: `ui.matplotlib()` to show figures directly.
- **Line Plot**: real-time data plotting.
- **Pyplot context**: `with ui.pyplot():`

```python
with ui.pyplot():
    import matplotlib.pyplot as plt
    plt.plot([1,2,3,4], [4,3,2,1])
```

### 5.2 Plotly, EChart, Highchart

**Plotly:**
```python
import plotly.graph_objs as go
fig = go.Figure(go.Bar(y=[2, 3, 1]))
ui.plotly(fig)
```

**EChart:**
```python
opts = {'xAxis': {...}, 'yAxis': {...}, 'series': [...]}
ui.echart(options=opts)
```

**Highcharts**: Similar; available if installed.

---

### 5.3 Timeline, Timeline Entries

```python
timeline = ui.timeline()
ui.timeline_entry(title='Start', subtitle='Kickoff', body='Process started', color='green')
```

---

### 5.4 Mermaid & Markdown, ReStructuredText (Diagrams and Docs)

- `ui.mermaid('graph TD;A-->B;')`
- `ui.markdown('# Title\nSome **markdown** here')`
- `ui.restructured_text('Heading\n=======\nBody text.')`

Markdown supports extras for tables/code: `extras=['fenced-code-blocks', 'tables']`.

---

## 6. Multimedia & Embedded Content

### 6.1 Images, Interactive Images, Audio, Video

```python
ui.image('picture.png')
ui.audio('song.mp3', autoplay=True)
ui.video('movie.mp4', controls=True, loop=True)
```

**Interactive images** allow SVG overlay and per-pixel event reporting.

---

## 7. Dialogs, Drawers, Menus, Notifications

- **Dialogs**: `dlg = ui.dialog(); dlg.open(); dlg.close()`
- **Drawers**: `ui.drawer(side='left')`, `.show()`, `.hide()`
- **Menus & ContextMenu**: popover menus.
- **Notifications**: `ui.notify('Message', type='info')` or persistent notifications via `ui.notification(...)`.

---

## 8. Forms, Inputs, Sliders, Validation

- `ui.input(label='Name', on_change=handler)`
- `ui.textarea(label='Details')`
- `ui.number(label='Age', min=0, max=120, step=1)`
- `ui.slider(min=0, max=100)`
- `ui.knob(min=0, max=10)`
- `ui.switch(text='On/Off', value=True)`
- `ui.checkbox(text='Agree?')`
- Most support validation: `validation={'Too small': lambda v: v > 3}`

Disable auto-validation: `.without_auto_validation()`.

---

## 9. File Uploads

```python
ui.upload(multiple=True, on_upload=handler, max_file_size=10_000_000)
```

Event handlers:
- `on_begin_upload`: Start of upload
- `on_upload`: per-file
- `on_multi_upload`: after all files
- `on_rejected`: if invalid files

---

## 10. Scripting, Styling, and Theming

- **JS Injection**: `await ui.run_javascript("alert('Hi!')")`
- **CSS/SCSS/SASS**: `ui.add_css('body { background: red; }')`, `ui.add_scss('...')`
- **Theming**: `ui.colors(primary='#3498db', accent='#e67e22')`
- **Dark mode**: `ui.dark_mode(True)`

---

## 11. Routing, Navigation, and Pages

- **Page decorator**: `@ui.page('/home')`
- **SPA Routing**: `ui.sub_pages(routes={'/profile': page_func, ...})`
- **Links and Anchors**: `ui.link('Profile', target='/profile')`; anchors with `ui.link_target('section-id')`

---

## 12. Advanced: Refreshable, State, Query, Teleport

- **Refreshable functions**: `@ui.refreshable`; call `.refresh()` to rerun and update content.
- **App state**: `val, set_val = ui.state(0)`; `set_val(42)` auto-refreshes UI containers.
- **Query**: `el = ui.query('body'); el.style('background: black;')`; targets static DOM elements.
- **Teleport**: allows placing content in arbitrary DOM nodes.

---

## 13. Math & Statistics Modules

### 13.1 Standard Library

- `math`: All scalar math functions (`sqrt`, `sin`, etc.).
- `statistics`: `mean`, `median`, `stdev`...
- `random`: `random.random()`, `random.choices()`, etc.
- `decimal` and `fractions`: For precise and rational number calculations.
- `time`, `datetime`: For timestamps, delays, date formatting, etc.
- `collections`: `Counter`, `defaultdict`, named tuples, etc.
- `csv`: Saving/loading CSV data.
- `json`: For serializing/deserializing data.

### 13.2 Example Usage

```python
import math, random
r = math.sqrt(144)
val = random.randint(0, 10)
import statistics
stats = statistics.mean([1,2,3])
```

---

## 14. String, Regex, and IO

- **String manipulation**: `string` module for constants and helpers.
- **Regex**: `re` offers full regular expression support.
- **Textwrap**: for word-wrapping and filling.
- **IO**: `io.StringIO()`, etc.

---

## 15. Hashing, UUID, and Encoding

- **Hashlib**: For digests: `hashlib.md5(b'data').hexdigest()`.
- **UUID**: For unique IDs: `uuid.uuid4()`
- **Base64**: For encoding/decoding binary data to string: `base64.b64encode(b'data')`

---

## 16. Temporary Files

Use the `tempfile` module for creating temp dirs/files:

```python
import tempfile
with tempfile.TemporaryFile() as f:
    f.write(b'Some temp data')
```

---

## 17. Type Hinting & Typing

The `typing` module is fully available for hinting and type-specific logic.

```python
from typing import List, Dict, Any, Optional
def f(x: List[Dict[str, Any]]) -> Optional[int]:
    ...
```

---

## 18. Plotly and ECharts

### 18.1 Plotly

To create and update interactive charts:

```python
import plotly.graph_objs as go
fig = go.Figure(go.Bar(y=[1, 2, 3]))
pl = ui.plotly(fig)
pl.update_figure({...})
```

### 18.2 ECharts

```python
opts = {'series': [{'data': [1,2,3]}]}
ec = ui.echart(opts)
# Call methods as needed:
await ec.run_chart_method('resize', [])
```

---

**Tips for Safe, Idiomatic Use:**

- Always check documentation for optional arguments and [available Quasar props](https://quasar.dev/vue-components/).
- Prefer canonical convenience methods for events and property changes.
- For editing tables or grids: always `.update()` after mutating `.rows` or `.columns`.
- Use `.bind_...` methods for dynamic state—binding eliminates the need for manual UI refresh.
- Use `.clear()` to remove all children, `.delete()` to remove element itself.
- Prefer `await` on async methods when results are needed (`.get_client_data()`, `.initialize()`, etc.).
- For capabilities not covered here, peruse the method signatures (all methods and parameters are fully documented above).

---

This primer serves as a reference for canonical patterns. For complex patterns (dynamic slots, advanced event emission, page refresh, file uploads with progress, etc.), build from the code templates above and consider augmenting with page-level or app-level state as needed.

**Happy building with NiceGUI!**
