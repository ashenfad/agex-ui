# Marimo Assistant — Implementation Plan

An agex-ui demo where an agent helps users build and refine marimo notebooks.
Chat on the left, live marimo editor on the right. The agent gets real Python
objects from the notebook, iterates in its sandbox, and delivers verified cells.

## Architecture

```
FastAPI process
├── NiceGUI chat UI                  — /
├── marimo editor (edit mode hack)   — /notebook/
├── agex agent (in-process)
│
│   Read path (in-process):
│   ├── marimo read tools            — cell code, variable schemas, errors
│   │   (GetLightweightCellMap, GetCellRuntimeData, GetTablesAndVariables, etc.)
│   ├── app.embed()                  — real Python objects from notebook
│   │   (async-native, safe from within agex async tasks)
│
│   Write path (file-based):
│   └── rewrite notebook .py file    — marimo editor picks up via watcher
```

## File Structure

```
agex_ui/
└── marimo_assistant/
    ├── __init__.py
    ├── main.py              # Process setup: FastAPI + NiceGUI + marimo mount
    ├── agent.py             # agex agent definition + registered functions
    ├── primer.py            # Agent system prompt
    ├── marimo_bridge.py     # In-process bridge to marimo (read tools + data access)
    └── marimo_mount.py      # NyanCAD-style edit-mode ASGI mount
```

## Implementation Phases

### Phase 1: Mount marimo in edit mode

**Goal:** Get marimo's editor running as a mounted ASGI app inside the FastAPI
process.

**File:** `marimo_mount.py`

**Approach:** Follow the NyanCAD workaround — manually construct a
`SessionManager` with `SessionMode.EDIT` and `NoopLspServer`, then call
marimo's internal `create_starlette_app()`. This gives a functional editor
without LSP autocomplete (acceptable — agent writes the cells, not the user).

**Steps:**
1. Install marimo as a dependency
2. Create `marimo_mount.py` with a `create_edit_app(notebook_path) -> Starlette`
   function that:
   - Creates a `SessionManager` with `mode=SessionMode.EDIT`
   - Uses `AppFileRouter.from_filename()` for the notebook path
   - Calls `create_starlette_app(session_manager)`
   - Returns the Starlette app (also saved for ToolContext use in Phase 3)
3. Reference NyanCAD's `server.py` for the exact internal imports needed:
   https://github.com/NyanCAD/Mosaic
4. Test: mount at `/notebook/`, open in browser, verify editor works

**Risk:** Private API — may break across marimo versions. Pin marimo version
in dependencies.

**Validation:** Can you open the editor in a browser, edit cells, and run them?

---

### Phase 2: Basic chat + marimo side-by-side UI

**Goal:** Chat panel on the left, marimo editor iframe on the right. No agent
intelligence yet — just the layout.

**Files:** `main.py`

**Approach:** Reuse `create_chat_interface` from the templates but replace the
app preview panel with a marimo iframe panel. Disable `enable_app_preview` and
add a custom right panel.

**Steps:**
1. Create `main.py` modeled on `workshop/main.py`
2. Replace `create_preview_panel` with a simple iframe pointing to `/notebook/`
3. Modify `ChatInterfaceConfig`:
   - `enable_app_preview=False` (no NiceGUI preview)
   - `max_width="100%"` (side-by-side layout)
4. Create a starter notebook at `./notebooks/scratch.py` with a few example cells
   (e.g., load a CSV, basic DataFrame operations)
5. Test: chat panel appears on left, marimo editor on right, both functional

**Reuse:** `chat_interface.py`, `turn.py`, `sessions.py`, `theme.py`,
`responses.py`, all from `agex_ui/core/`.

**Validation:** Both panels render. You can type in chat (no agent response yet)
and edit cells in marimo independently.

---

### Phase 3: marimo bridge — read tools + data access

**Goal:** Give the agent functions to read notebook state and get real data.

**File:** `marimo_bridge.py`

**Approach:** Two channels:

1. **marimo read tools (in-process):** Construct a `ToolContext` from the
   Starlette app created in Phase 1. Wrap the tools as simple Python functions
   the agent can call.

2. **`app.embed()` for real objects:** Import the notebook's `App`, clone it,
   call `embed()` to get `defs` with real Python objects. Use `embed()` (async)
   rather than `run()` (sync, can't be called from async context).

**Read tool wrappers:**
```python
async def read_cells() -> dict:
    """Get all cells with their code, defined variables, and errors."""
    # Calls GetLightweightCellMap + GetCellRuntimeData
    ...

async def get_variable_info(variable_names: list[str]) -> dict:
    """Get type info and schemas for notebook variables."""
    # Calls GetTablesAndVariables
    ...

async def get_errors() -> dict:
    """Get all notebook errors organized by cell."""
    # Calls GetNotebookErrors
    ...
```

**Data access wrapper:**
```python
async def get_notebook_data() -> dict:
    """Run the notebook and return all defined variables as real objects."""
    from notebooks.scratch import app as notebook_app
    cloned = notebook_app.clone()
    result = await cloned.embed()
    return dict(result.defs)
```

**Steps:**
1. Create `marimo_bridge.py` with the wrapper functions above
2. Store a module-level reference to the Starlette app from Phase 1
   (needed for ToolContext)
3. Handle session_id discovery: call `GetActiveNotebooks` first, use the
   session_id for subsequent tool calls
4. Handle `app.embed()` caveats:
   - Clone the app before each call (`app.clone()`) to avoid shared state
   - Handle the case where the notebook has import errors
   - Consider caching/invalidation — re-import the module when the file changes
5. Test: call each wrapper from a Python script, verify you get cell data
   and real DataFrames back

**Key caveat:** `app.embed()` returns data from a fresh execution with default
widget values, not the live session's state. Acceptable for v1 — the agent gets
real data structure/content, just not widget-adjusted views.

**Validation:** `read_cells()` returns cell code matching what's in the editor.
`get_notebook_data()` returns real DataFrames you can call `.describe()` on.

---

### Phase 4: Agent definition

**Goal:** Configure the agex agent with the right registrations and primer.

**Files:** `agent.py`, `primer.py`

**Approach:** Standard agex agent setup. Register the bridge functions from
Phase 3, plus data science libraries the agent will use in its sandbox.

**agent.py outline:**
```python
agent = Agent(
    name="Marimo Assistant",
    primer=PRIMER,
    llm=connect_llm(...),
    state=connect_state(type="versioned", storage="disk", path="/tmp/agex/marimo"),
    fs=connect_fs(type="virtual"),
    max_iterations=15,  # may need more turns for iteration
)

# Data libraries for the sandbox
register_stdlib(agent, io_friendly=True)
register_pandas(agent, io_friendly=True)
register_plotly(agent, io_friendly=True)

# Bridge functions
agent.fn(read_cells, visibility="high")
agent.fn(get_variable_info, visibility="high")
agent.fn(get_errors, visibility="high")
agent.fn(get_notebook_data, visibility="high")

# Cell delivery function (Phase 5)
agent.fn(write_notebook, visibility="high")
```

**primer.py key points:**
- You help users build marimo notebooks
- Use `read_cells()` to see current notebook state
- Use `get_notebook_data()` to get real data into your workspace
- Iterate: write code, test it against the real data, verify it works
- When satisfied, use `write_notebook()` to deliver cells
- Follow marimo conventions: cells return variables, use `mo.md()` for markdown
- Include a brief marimo cell syntax reference

**Validation:** Agent responds to prompts, can call bridge functions, sees
real data in its sandbox.

---

### Phase 5: Cell delivery via file write

**Goal:** Agent writes verified cells back to the notebook file, marimo editor
picks them up.

**File:** Add `write_notebook()` to `marimo_bridge.py`

**Approach:** The agent produces marimo cell code. A registered function writes
it to the `.py` file. marimo's file watcher detects the change and streams
updates to the editor.

**The tricky part:** marimo notebooks have a specific format. The agent needs to
produce valid marimo `.py` files. The function should handle the formatting.

```python
def write_notebook(cells: list[dict]) -> None:
    """Write cells to the notebook file.

    Args:
        cells: List of dicts with 'name' and 'code' keys.
               Each becomes an @app.cell function.
    """
    # Generate valid marimo .py file from cell definitions
    # Write to the notebook path
    # marimo's watcher picks up the change
    ...
```

**Format considerations:**
- marimo `.py` files have a specific header and `App()` instantiation
- Each cell is an `@app.cell` decorated function
- Cell function names can be `_` for anonymous cells
- Function parameters declare dependencies (inputs from other cells)
- Return tuples declare outputs
- The agent should ideally produce the full file, not patch individual cells,
  for v1 simplicity

**Steps:**
1. Study the exact format of a marimo `.py` file (read a few examples)
2. Implement `write_notebook()` — takes cell code, wraps in proper format,
   writes to disk
3. Configure marimo to watch the file (may need watcher_on_save config)
4. Test: call `write_notebook()` manually, verify marimo editor updates

**Alternative approach:** Instead of the agent generating raw marimo `.py`
format, it could produce plain Python code blocks and `write_notebook()` handles
the `@app.cell` wrapping and dependency inference (parse the code for variable
reads/writes). This is friendlier for the agent but more complex to implement.

**Validation:** Agent delivers cells, they appear in the marimo editor, user
can run them, they produce correct results.

---

### Phase 6: End-to-end wiring

**Goal:** Connect everything. User chats, agent reads notebook, iterates,
delivers cells.

**Steps:**
1. Wire `handle_prompt` task in `agent.py`
2. Set up the `setup` parameter on the task to auto-read notebook state
3. Add the marimo iframe panel to the chat interface layout
4. Test the full loop:
   - User has a notebook with some data loaded
   - User asks "add a cell that shows revenue by region"
   - Agent calls `read_cells()` to see current notebook
   - Agent calls `get_notebook_data()` to get the real DataFrame
   - Agent writes and tests code in its sandbox
   - Agent calls `write_notebook()` to deliver
   - Cells appear in marimo editor
   - User runs them, sees correct results

**Validation:** The full loop works. Agent-delivered cells work on first try
because the agent tested them against real data.

---

## Dependencies to add

```toml
# In pyproject.toml
dependencies = [
    ...
    "marimo>=0.12.0,<0.13.0",  # pin to avoid private API breakage
]
```

## Open Questions

1. **marimo watcher in ASGI mode:** Does the file watcher work when marimo is
   mounted via the NyanCAD hack, or only via `marimo edit` CLI? If not, may need
   to trigger a reload via marimo's internal session refresh mechanism.

2. **Session ID discovery:** The read tools need a `session_id`. When marimo is
   mounted as ASGI, how are sessions identified? Need to test
   `GetActiveNotebooks` to see what comes back.

3. **Concurrent access to notebook file:** Both the user (saving in editor) and
   the agent (writing via `write_notebook()`) can write the file. For v1, the
   agent should only write when the user explicitly asks (via chat), reducing
   conflict risk. No automated writes.

4. **`app.embed()` module caching:** When the agent rewrites the `.py` file,
   the previously imported module is stale. Need `importlib.reload()` or
   re-import to get the updated app. This adds complexity to
   `get_notebook_data()`.

5. **Notebook format generation:** Should the agent produce raw marimo `.py`
   format, or should `write_notebook()` handle the wrapping? The latter is
   more robust but requires parsing Python code for variable dependencies.

## Non-Goals for v1

- Widget state capture/restore
- kvgit versioning of the notebook file (future — Phase 2 of the broader vision)
- Bidirectional sync conflict resolution
- monkeyfs interception of marimo file I/O
- Branch switching = notebook switching
- MCP protocol (using in-process tool calls instead)
