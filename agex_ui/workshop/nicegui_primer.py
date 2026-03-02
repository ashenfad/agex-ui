"""NiceGUI layout and component best practices."""

NICEGUI_PRIMER = """
## NiceGUI Layout Best Practices

### Required: Global Height Setup (The Unbreakable Height Chain)

For any element to have `height: 100%`, every single one of its ancestors must also have a defined height.
In NiceGUI, this chain starts at the `html` tag. Use `ui.add_head_html` to force the height chain from the root:

```python
ui.add_head_html('''
    <style>
        html, body, #q-app, .q-layout, .q-page-container, .q-page, .nicegui-content {
            height: 100% !important;
            width: 100% !important;
            display: flex !important;
            flex-direction: column !important;
        }
    </style>
''')
```

Alternative (less robust but simpler):

```python
ui.query('body').classes('p-0 m-0 h-full overflow-hidden')
ui.query('.nicegui-content').classes('p-0 m-0 h-full')
```

### The Height Chain Rule

Unlike width, height only flows from parent to child if there's a **continuous chain** of
defined heights. If any element in the middle breaks the chain, children collapse to zero.

```
body (h-full) → .nicegui-content (h-full) → your column (h-full) → content (flex-grow) ✓
body (h-full) → .nicegui-content (missing!) → your column (h-full) → content ✗ collapses
```

### The `ui.refreshable` Bottleneck

The `@ui.refreshable` decorator wraps your content in a `div`. By default, this div has no height,
which collapses all children inside it to zero or their minimum content size.

**Fix:** Target the `.nicegui-refreshable` class with CSS to make it a flex-grow container:

```python
ui.add_css('.nicegui-refreshable { display: flex; flex-direction: column; flex-grow: 1; min-height: 0; width: 100%; }')
```

### The App Shell Pattern

Use this standard structure for full-screen apps:

```python
# Global setup (required)
ui.add_head_html('''
    <style>
        html, body, #q-app, .q-layout, .q-page-container, .q-page, .nicegui-content {
            height: 100% !important;
            width: 100% !important;
            display: flex !important;
            flex-direction: column !important;
        }
        .nicegui-refreshable { display: flex; flex-direction: column; flex-grow: 1; min-height: 0; width: 100%; }
    </style>
''')

# App shell
with ui.column().classes('w-full h-full p-0 m-0 gap-0'):
    # Header - fixed height, won't shrink
    with ui.row().classes('w-full h-12 items-center px-4 border-b shrink-0'):
        ui.label('My App').classes('text-xl font-bold')

    # Main content - flex-grow fills remaining space
    with ui.column().classes('w-full flex-grow min-h-0 overflow-auto'):
        with ui.column().classes('w-full p-4 gap-4'):
            ui.label('Content...')

    # Footer - fixed height, won't shrink
    with ui.row().classes('w-full h-12 items-center px-4 border-t shrink-0'):
        ui.label('Footer')
```

### Why `min-h-0` Is Critical

In flexbox, elements have `min-height: auto` by default, which prevents them from shrinking
below their content size. This causes scroll areas and charts to overflow instead of fitting.

**Always add `min-h-0` to:**
- Any `flex-grow` container that should scroll or contain expanding content
- Scroll areas (`ui.scroll_area`)
- Chart containers

```python
# Without min-h-0: scroll area overflows, no scrolling
with ui.scroll_area().classes('flex-grow'):  # ✗ broken

# With min-h-0: scroll area shrinks to fit, scrolling works
with ui.scroll_area().classes('flex-grow min-h-0'):  # ✓ works
```

Standard layout pattern for scrollable content:

```python
with ui.column().classes('w-full flex-grow min-h-0'):
    with ui.scroll_area().classes('w-full flex-grow min-h-0'):
        ui.table(...)
```

### Avoid `ui.card` for Main Viewports

While `ui.card` is great for small widgets, its internal Quasar classes often apply fixed paddings
or restricted flex behaviors. For a main dashboard area, a standard `ui.column` with a border
and background is often more predictable:

```python
with ui.column().classes('w-full flex-grow min-h-0 p-4 border rounded-lg bg-[var(--bg-card)]'):
    # Your interactive content here
```

### Avoid `100vh` in Preview

In the preview iframe, `100vh` refers to the *parent window's* viewport, not the iframe.
Use flexbox-based layouts instead:
- `h-full` with proper height chain (preferred)
- `calc(100 * var(--iframe-vh))` if you need viewport-relative heights

### Flexbox Reference

- `ui.row()` - horizontal flex, `ui.column()` - vertical flex
- `flex-grow` - expand to fill available space
- `shrink-0` - prevent shrinking (headers/footers)
- `min-h-0` / `min-w-0` - allow shrinking below content size
- `gap-0` - remove default gap between children
- `gap-4` - add spacing between children
- `justify-*` - main axis alignment (start, center, end, between)
- `items-*` - cross axis alignment (start, center, end, stretch)

### Common Classes

**Width:** `w-full`, `w-1/2`, `w-64`, `min-w-0`
**Height:** `h-full`, `h-12`, `min-h-0`
**Flex:** `flex-grow`, `shrink-0`, `gap-0`, `gap-4`
**Overflow:** `overflow-auto`, `overflow-hidden`, `truncate`

### Debugging Layout Issues

1. Add `bg-red-100` to see container boundaries
2. Zero height? Check the height chain from body down - every element needs `h-full` or `flex-grow`
3. Content overflows instead of scrolling? Add `min-h-0` to the flex-grow container
4. Scroll area not scrolling? Add `min-h-0` and ensure parent is flex with defined height
5. Unwanted gaps? Add `gap-0` to the parent container

## Plotly Charts

### Initialization

`ui.plotly()` requires a figure - it cannot be called empty:

```python
# WRONG - TypeError
chart = ui.plotly()

# CORRECT - provide placeholder or create dynamically
chart = ui.plotly(px.scatter(title="Loading..."))

# Or create inside a refreshable
@ui.refreshable
def show_chart():
    if data is not None:
        ui.plotly(px.bar(data, x='x', y='y'))
```

### Theme Compatibility (Light/Dark)

Plotly doesn't inherit CSS variables. For visibility in both themes:

```python
fig.update_layout(
    paper_bgcolor='rgba(0,0,0,0)',  # Transparent background
    plot_bgcolor='rgba(0,0,0,0)',
    font_color='#888',              # Neutral text color
    legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
    margin=dict(l=20, r=100, t=40, b=20),  # Room for legend on right
)
fig.update_xaxes(gridcolor='#444', tickfont_color='#888')
fig.update_yaxes(gridcolor='#444', tickfont_color='#888')
```

### Timezone-Aware Datetimes

`px.timeline` fails with timezone-aware datetimes. Convert to naive:

```python
start = datetime.fromtimestamp(ts, tz=ZoneInfo(tz)).replace(tzinfo=None)
```

### Plotly Config Options

To configure Plotly (e.g., hide toolbar), convert the figure to a dict and add `config`:

```python
fig = px.bar(...)

# Convert to dict and add config
plot_dict = fig.to_dict()
plot_dict['config'] = {'displayModeBar': False, 'responsive': True}

ui.plotly(plot_dict)
```

**Note:** `ui.plotly(fig, config=...)` doesn't work, and `.props()` is unreliable for Plotly config.

### Responsive Chart Container

To make Plotly charts fill their flex container dynamically:
1. Set the figure height to `None` in `fig.update_layout(height=None)`.
2. Enable the responsive config in `ui.plotly`.

```python
fig.update_layout(height=None)  # Let container control height
plot_dict = fig.to_dict()
plot_dict['config'] = {'responsive': True}
ui.plotly(plot_dict).classes('w-full flex-grow min-h-0')
```

For a chart with fixed minimum height:

```python
with ui.column().classes('w-full').style('min-height: 300px'):
    ui.plotly(fig).classes('w-full h-full')
```

## Tables and Data Grids

- `ui.table` - simpler, good for most cases
- `ui.aggrid` - more powerful for large/complex data

### Basic Usage

```python
ui.table.from_pandas(df, pagination=10)  # Always paginate large data
ui.aggrid.from_pandas(df, options={'pagination': True, 'paginationPageSize': 20})
```

### Wide Tables (Many Columns)

```python
ui.aggrid.from_pandas(df, options={
    'suppressSizeToFit': True,  # Allow horizontal scroll
    'defaultColDef': {'minWidth': 100}
})
```

### Large Datasets

For 1000+ rows, always paginate. Never send huge DataFrames without limits:

```python
# Bad - blocks UI
ui.table.from_pandas(huge_df)

# Good - limit or paginate
ui.table.from_pandas(huge_df.head(100), pagination=25)
```

### JSON Serialization Errors

`TypeError: Type is not JSON serializable: Timestamp` - convert before display:

```python
df['date'] = df['date'].dt.strftime('%Y-%m-%d %H:%M')
df['duration'] = df['duration'].astype(str)
```

## UI Components

### Compact Inputs

Use `dense` for space-efficient dashboards:

```python
ui.input("Name").props('dense')
ui.select(["A", "B"], label="Option").props('dense')
ui.button("Go").props('dense')
```

### Cards

```python
with ui.card().classes('w-full'):           # Standard with padding
with ui.card().tight():                      # No padding
with ui.card().classes('flex flex-col'):    # Flex container for growing content
```

### Method Chaining Pitfall

Most NiceGUI methods (`.classes()`, `.style()`, `.props()`) return the element for chaining.
However, `set_visibility()` and `set_text()` return `None`, breaking the chain.

```python
# WRONG - selector becomes None!
selector = ui.select(options).set_visibility(False)

# CORRECT - separate call
selector = ui.select(options)
selector.set_visibility(False)
```

### Initialization Race Conditions

NiceGUI is event-driven. An `on_change` handler may fire during initial script execution
before all elements are defined. Guard with None checks:

```python
# Initialize references
other_element = None

def handle_change():
    if other_element is None:
        return  # Not ready yet
    other_element.set_value(...)

input_elem = ui.input(on_change=handle_change)
other_element = ui.label()  # Now defined
```

### State Management

Use module-level variables or a state dictionary to share state between callbacks:

```python
# Option 1: Module-level variables with global
counter = 0

def increment():
    global counter
    counter += 1
    label.set_text(f"Count: {counter}")

label = ui.label("Count: 0")
ui.button("Add", on_click=lambda _: increment())
```

```python
# Option 2: Dictionary (avoids global keyword)
state = {'count': 0}

def increment():
    state['count'] += 1
    label.set_text(f"Count: {state['count']}")

label = ui.label("Count: 0")
ui.button("Add", on_click=lambda _: increment())
```

### Async Callbacks

NiceGUI natively supports `async def` callbacks. Use them for I/O or any async operation:

```python
async def load_data():
    data = await fetch_remote_data()
    results_view.refresh()

ui.button("Load", on_click=load_data)
```

`.refresh()` on `@ui.refreshable` works as a direct call — no timers needed:

```python
@ui.refreshable
def my_view():
    ui.label(f"Count: {state['count']}")

def increment():
    state['count'] += 1
    my_view.refresh()  # Direct call works

ui.button("Add", on_click=lambda _: increment())
```

## Event Callbacks

### Lambda Callbacks with Parameters (Critical!)

**NiceGUI passes an event argument to callbacks.** If your lambda has any parameters, the event will be
passed as the first argument, overwriting your intended value.

```python
# WRONG - all buttons set selector to the click event, not the fruit!
for fruit in options:
    ui.button(fruit, on_click=lambda f=fruit: selector.set_value(f))
    # NiceGUI calls: callback(ClickEventArguments(...))
    # This overwrites f with the event object!
```

```python
# CORRECT - use _ to absorb the event argument
for fruit in options:
    ui.button(fruit, on_click=lambda _, f=fruit: selector.set_value(f))
    # _ captures the event, f keeps its default value
```

```python
# ALSO CORRECT - explicitly name the event parameter
for fruit in options:
    ui.button(fruit, on_click=lambda e, f=fruit: selector.set_value(f))
```

```python
# ALTERNATIVE - factory function pattern
for fruit in options:
    def make_callback(f=fruit):
        def callback():
            selector.set_value(f)
        return callback
    ui.button(fruit, on_click=make_callback())
```

### Event Arguments

NiceGUI callbacks receive event objects with useful context:

```python
ui.button("Click", on_click=lambda e: print(e.sender))  # The button element
ui.input("Name", on_change=lambda e: print(e.value))    # The new value
ui.select(options, on_change=lambda e: print(e.value))  # Selected value
```

For simple handlers that don't need the event, use `_` to discard it:

```python
ui.button("Refresh", on_click=lambda _: data.refresh())
```

## Common Patterns

### Startup Data Loading

Load data at module level — it runs during script execution before UI renders:

```python
data = load_csv("data/sales.csv")

@ui.refreshable
def dashboard():
    ui.plotly(create_chart(data))

dashboard()
```

### Reactive Updates

Use `@ui.refreshable` for partial UI updates without full reload:

```python
@ui.refreshable
def chart_view():
    ui.plotly(create_figure(current_data))

# Trigger refresh when input changes
date_input = ui.input("Date", on_change=lambda: chart_view.refresh())
```

### Caching Large Data

Load large files once at module level to avoid re-parsing on each refresh:

```python
# Load once at startup
_calendar_cache = {}

def get_calendar(name):
    if name not in _calendar_cache:
        _calendar_cache[name] = parse_ics(f"data/{name}.ics")
    return _calendar_cache[name]
```

### File Operations

Wrap file loading in try-except:

```python
try:
    with open("data/config.json") as f:
        config = json.load(f)
except FileNotFoundError:
    config = {}
```
"""
