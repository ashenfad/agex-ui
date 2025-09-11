# Capabilities Primer
# agent: lorem_ipsum
# fingerprint: 9e54051c
# target_chars: 16000
# model: gpt-4.1
# created_at: 2025-09-11T00:43:24.785830+00:00

# Capabilities Primer for Restricted Python Agent
This document provides an organized and deduplicated overview of the main patterns for using the available modules and APIs in your Python environment. It’s designed for agents operating within a limited Python+NiceGUI stack (with some included data science, math, and standard libraries). For each cluster of functionality, you'll find actionable guidance and canonical usage snippets.

Only modules and attributes from the actual API are mentioned—**do not attempt import or usage of anything not reflected here.** See canonical usage, warnings, and best practices in each section.

---

## Table of Contents

1. [Math, Randomness, and Statistics](#math-randomness-and-statistics)
2. [Working with Numbers and Fractions](#working-with-numbers-and-fractions)
3. [Date, Time, and Timing](#date-time-and-timing)
4. [Text, Strings, and Regular Expressions](#text-strings-and-regular-expressions)
5. [Collections and Data Structures](#collections-and-data-structures)
6. [I/O, Temporary Files, and UUIDs](#io-temporary-files-and-uuids)
7. [Data Formats: JSON, CSV, Base64](#data-formats-json-csv-base64)
8. [Hashing and Crypto Utilities](#hashing-and-crypto-utilities)
9. [NiceGUI UI Elements: Creation & Updates](#nicegui-ui-elements-creation--updates)
10. [NiceGUI UI Elements: Layout, Styling & Containers](#nicegui-ui-elements-layout-styling--containers)
11. [NiceGUI Advanced Features: Events, Bindings & Dynamic Resources](#nicegui-advanced-features-events-bindings--dynamic-resources)
12. [Validation, Error Handling, and User Feedback](#validation-error-handling-and-user-feedback)
13. [Graphics, Plots, and Visualization](#graphics-plots-and-visualization)
14. [Data Table and Grid Controls](#data-table-and-grid-controls)
15. [Miscellaneous (Notifications, File Upload, etc.)](#miscellaneous-notifications-file-upload-etc)
16. [Key design & idiom notes](#key-design--idiom-notes)

---

## Math, Randomness, and Statistics

### math

**Use case:** Numeric math, including trigonometry, logarithms, square roots, etc.

- Import: `import math`
- Common methods:
    - `math.sqrt(x)`, `math.log(x, base)`, `math.sin(x)`, `math.factorial(n)`, etc.

```python
import math
r = math.sqrt(16)
a = math.sin(math.pi / 2)
```

### random

**Use case:** Random number generation, selections, shuffling, etc.

- Import: `import random`
- Common methods:
    - `random.random()` (float in [0,1)), 
    - `random.randint(a, b)`,
    - `random.choice(sequence)`,
    - `random.shuffle(list)`.

```python
import random
roll = random.randint(1, 6)
item = random.choice(['apple', 'banana', 'orange'])
random.shuffle(cards)
```

### statistics

**Use case:** Descriptive statistics (mean, median, stdev, etc.)

- Import: `import statistics`
- Typical usage: `statistics.mean(seq)`, `statistics.stdev(seq)`, etc.

```python
import statistics
data = [4, 4, 5, 6, 5]
avg = statistics.mean(data)
stdev = statistics.stdev(data)
```

---

## Working with Numbers and Fractions

### decimal

**Use case:** Accurate decimal fixed-point arithmetic.
- Use `decimal.Decimal` for operations where float imprecision is an issue.

```python
import decimal
d1 = decimal.Decimal("0.1")
d2 = decimal.Decimal("0.2")
sum = d1 + d2  # Accurate decimal addition!
```

### fractions

**Use case:** Exact rational number calculations via numerator/denominator pairs.

```python
import fractions
half = fractions.Fraction(1, 2)
third = fractions.Fraction(1, 3)
result = half + third
```

---

## Date, Time, and Timing

### datetime

**Use case:** Manipulating dates and times, formatting/parsing, arithmetic.
- `datetime.datetime.now()`, `datetime.date.today()`, `datetime.timedelta`, etc.

```python
import datetime
now = datetime.datetime.now()
tomorrow = now + datetime.timedelta(days=1)
```

### time

**Use case:** Access wall clock or monotonic time, sleep, measure durations.

```python
import time
start = time.time()
time.sleep(0.5)
elapsed = time.time() - start
```

---

## Text, Strings, and Regular Expressions

### string

**Use case:** Useful string constants (e.g., `string.ascii_letters`, digits), basic utilities.
```python
import string
letters = string.ascii_letters
```

### re

**Use case:** Regular expressions for matching, splitting, extracting, replacing in strings.

```python
import re
phone = re.sub(r'\D', '', '(555) 123-4567')  # Remove non-digit characters
match = re.match(r'(\w+)@(\w+)\.(\w+)', 'test@example.com')
```

### textwrap

**Use case:** Wrapping text, formatting paragraphs.

```python
import textwrap
text = "This is a very long line of text that needs to be wrapped."
wrapped = textwrap.fill(text, width=40)
```

---

## Collections and Data Structures

### collections

**Use case:** Specialized containers (`Counter`, `defaultdict`, `namedtuple`, etc.).

```python
import collections
counter = collections.Counter(['a', 'b', 'a', 'c', 'b', 'b'])
from collections import defaultdict
d = defaultdict(list)
d['a'].append(1)
```

---

## I/O, Temporary Files, and UUIDs

### tempfile

**Use case:** Create temporary files/directories.
```python
import tempfile
with tempfile.NamedTemporaryFile(mode='w') as f:
    f.write('temp content')
    f.seek(0)
    content = f.read()
```

### io

**Use case:** Buffered streams for text or binary data, e.g. for in-memory file-like operations.

```python
import io
f = io.StringIO()
f.write("abc")
f.seek(0)
print(f.read())
```

### uuid

**Use case:** Generate unique identifiers.

```python
import uuid
unique = uuid.uuid4()
```

---

## Data Formats: JSON, CSV, Base64

### json

**Use case:** Serializing/deserializing JSON.

```python
import json
data = {'a': 1}
j = json.dumps(data)
parsed = json.loads(j)
```

### csv

**Use case:** Reading/writing CSV files or data.

```python
import csv
with open('data.csv', newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    rows = list(reader)
```

### base64

**Use case:** Encode/decode binary data using Base64 (common for transferring binary in JSON/URLs).

```python
import base64
encoded = base64.b64encode(b'some bytes')
decoded = base64.b64decode(encoded)
```

---

## Hashing and Crypto Utilities

### hashlib

**Use case:** Hashing data for integrity, authentication, etc.

```python
import hashlib
h = hashlib.sha256()
h.update(b"abc")
digest = h.hexdigest()
```

---

## NiceGUI UI Elements: Creation & Updates

### General Element Creation

- **Pattern**: `element = ui.SomeElementClass(args...)`
- Each element is a Python object with:
  - Props and attributes that can be set/read.
  - `.update()` for redrawing changes.
  - `.clear()` to remove children, `.delete()` to remove itself.
- Elements support slot-based composition (use `.add_slot(...)` with `with` context to add child UI elements to slots).
  
**Example:**

```python
from nicegui import ui

button = ui.button(text="Click me")
button.set_text("Clicked!")
button.style("color: red;")
button.tooltip("Click to perform an action.")
```

### Value Manipulation

- Use `.set_value()` or assign to `.value` (where present).
- Bindings and two-way updates available (see bindings section).

```python
input_box = ui.input(value="Hello")
input_box.set_value("World")
ui.label(text=input_box.value)
```

### Children and Layout

- Add children to containers via `with` blocks, `.add_slot()`, etc.
- Use `ui.card()`, `ui.column()`, `ui.row()` for layout.

```python
with ui.card():
    ui.label("Header")
    ui.input(label="Name")
```

---

## NiceGUI UI Elements: Layout, Styling & Containers

- UI elements share many styling and layout methods:
    - `.classes()` or `.default_classes()` for CSS classes.
    - `.style()` or `.default_style()` for inline CSS.
    - `.props()` or `.default_props()` for extra HTML attributes/Quasar props.

**Slots and Containers**

- Add elements into `with <container>: ...` blocks.
- Use `.add_slot(name, ...)`, `.add_resource()`, and related methods for advanced slot and resource management.

**Examples:**

```python
row = ui.row()
with row:
    ui.button("A")
    ui.button("B")

ui.separator()  # For horizontal divider
ui.space()      # For filler in flex layouts
```

---

## NiceGUI Advanced Features: Events, Bindings & Dynamic Resources

### Event Wiring

- Every UI element can subscribe to events with `.on(type, handler, ...)`.

```python
def on_click(event):
    print("Button clicked!")

btn = ui.button("Click me")
btn.on("click", on_click)
```

- Use `on_value_change`, `on_click`, and friends for specific events, or `.on()` for custom events.

### Property Bindings

- Use `element.bind_X(target_object, ..., backward/forward)` for two-way data binding.
- Use `element.bind_X_from` and `element.bind_X_to` for one-way binding from/to a property.

```python
ui.input(label="Mirror me").bind_value(target_model, 'input_value')
```

- For visibility: `bind_visibility`, `bind_visibility_from`, `bind_visibility_to`.

### Dynamic Resources

- Elements can expose/serve resources via `.add_resource()` and `.add_dynamic_resource()` (CSS, JS, etc).

---

## Validation, Error Handling, and User Feedback

- UI input elements support validation via the `validation` argument:
    - Pass a dict of error-message/callback pairs, OR a function returning an error string (or None).
    - Validation is triggered on each change by default; call `.without_auto_validation()` to disable.
    - `.validate()` (optionally with `return_result=False` for async) triggers validation.

```python
def email_validator(value):
    if "@" not in value:
        return "Invalid email"
ui.input(label="Email", validation=email_validator)
```

---

## Graphics, Plots, and Visualization

### plotly

**Use case:** Interactive and static graphs.
- Pass either a Plotly `go.Figure` or dict describing the figure.
- Call `ui.plotly(figure)` to render.
- To update, use `.update_figure()`.

```python
from plotly import graph_objs as go
fig = go.Figure()
ui.plotly(fig)
```

### echart/highchart

**Use case:** Advanced charts (options: eCharts, Highcharts).
- Pass options dict or chart objects, update via `.update()`.

```python
chart = ui.echart(options={"xAxis": {}, "series": []})
chart.options['series'].append({"data": [1,2,3]})
chart.update()
```

### matplotlib/pyplot/line_plot

**Use case:** Render Matplotlib charts, live plot data, etc.

```python
with ui.pyplot():
    import matplotlib.pyplot as plt
    plt.plot([1,2,3], [2,4,1])
```

### Other Visualization

- Images: `.set_source()`, `.force_reload()`.
- Interactive images: event handlers yield image coordinates.
- 3D: Use `ui.scene` and related classes and methods for 3D scenes with Three.js.

---

## Data Table and Grid Controls

### ui.table

**Use case:** Interactive tables (Quasar QTable).

- Pass list of dict rows and (optionally) columns.
- Methods: `.add_row(...)`, `.remove_row(...)`, `.update_rows(...)`, `.get_computed_rows()`.
- Convert from pandas/polars via `.from_pandas()` or `.from_polars()`.

```python
rows = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
columns = [{"name": "id"}, {"name": "name"}]
table = ui.table(rows, columns)
table.add_row({"id": 3, "name": "C"})
table.remove_row({"id": 2, "name": "B"})
```

### ui.aggrid

- AG Grid table; methods for sorted/filtered data, selection (`get_selected_row(s)`), dynamic updates, advanced grid API.
- From pandas/polars: `ui.aggrid.from_pandas(df)`, `ui.aggrid.from_polars(df)`.

---

## Miscellaneous (Notifications, File Upload, etc.)

### Notifications

- Display notifications with `ui.notify(...)` (ephemeral) or `ui.notification(...)` (element for persistent/controlled notifications).
- Customize position, content, type (positive, negative, warning, info), colors.

```python
ui.notify("Save successful!", type="positive")
```

### File Upload

- Use `ui.upload()` control for files; handlers: `on_upload`, `on_multi_upload`, `on_rejected`, etc.
- Get files via event arguments, manage uploaded items with methods like `.reset()`. Set options for max files, size, etc.

---

## Key design & idiom notes

- **Elements are stateful objects.** Mutate their attributes, call `.update()` to push changes to the UI.
- **Containers:** Use context managers (`with ...`) or `.add_slot()` for layout and composition.
- **Bindings are a central pattern:** Use them for two-way or one-way sync between Python-side models and UI controls.
- **Events are everywhere:** Attach handlers on every element or globally.
- **Validation:** Centralized and highly reusable.
- **Visualization/updating:** Always update plots/tables via `.update()` or appropriate data-push methods after changing the relevant data.

## Canonical usage patterns

**Create and update an input with event binding:**

```python
value = {"text": ""}

def on_change(event):
    value["text"] = event.value
    print("Changed to", value["text"])

inp = ui.input(label="Type here...", on_change=on_change)
inp.set_value("Initial value")
inp.update()
```

**Display a responsive UI layout:**

```python
with ui.row():
    ui.button("Left")
    ui.space()
    ui.button("Right")

ui.separator()
ui.label("Below the row...")
```

**Show a live-updating plot:**

```python
import math
x = 0
line_plot = ui.line_plot()

def update_plot():
    global x
    x += 1
    y = math.sin(x / 10)
    line_plot.push([x], [[y]])

ui.timer(0.1, update_plot)
```

**Display a table from pandas DataFrame:**

```python
import pandas as pd
df = pd.DataFrame({'A': [1, 2], 'B': ['foo', 'bar']})
table = ui.table.from_pandas(df)
```

**Show a notification, then a controlled, dismissable notification:**

```python
ui.notify("One-time message")
note = ui.notification(message="Sticky warning!", type="warning", timeout=None)
# ...later
note.dismiss()
```

---

**In summary:**  
Write code in a Pythonic event-driven fashion. UI elements are dynamically updated objects; attach handlers and bind properties explicitly. When in doubt, find an element's method for the change you want, perform the change, and call `.update()`.

---

_For further reference, consult the NiceGUI documentation for specific UI components or visit the underlying Quasar docs for additional details on component props and CSS classes._
