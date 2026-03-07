# Marimo Assistant — Phase 2: VFS Integration & Widget State

The notebook file and widget state live in the agent's VFS. Changes from
either side (user in editor, agent in sandbox) flow through VFS and generate
file events in the agent's event log.

## Prerequisites (Phase 1 — done)

- Kernel runs as thread (shared memory via patched edit mode)
- Agent reads live objects via `get_kernel_globals()`
- Agent writes notebook via file rewrite
- monkeyfs proven to work with MountFS across threads

## Architecture

```
Agent VFS (shared)
├── notebook.py          ← marimo reads/writes via monkeyfs
├── widget_state.json    ← written on widget changes (debounced)
└── data/                ← shared data files

Kernel thread
├── monkeyfs MountFS active (current_fs ContextVar)
│   ├── /notebooks/ → shared VFS
│   └── everything else → IsolatedFS("/") (real filesystem)
├── Widget change hook on SessionView
└── Cell execution → updates kernel.globals (shared memory)

Agent event log:
  [file] notebook.py modified        ← user edited a cell
  [file] widget_state.json modified  ← user moved slider to 73
  [file] notebook.py modified        ← agent delivered new cells
```

## Steps

### Step 1: Wire monkeyfs into the kernel thread

Route the kernel's file I/O for the notebook directory through a VFS.

- Call `monkeyfs.patching.install()` at startup (global, idempotent)
- Create a `VirtualFS` for the notebook workspace
- Create `MountFS(IsolatedFS("/"), {NOTEBOOK_DIR: workspace_vfs})`
- Patch the kernel thread entry (`launch_kernel` wrapper) to set
  `monkeyfs.current_fs` with the MountFS
- Seed the VFS with the current notebook `.py` file contents

**Validation:** Marimo saves the notebook → write goes to VFS. Read VFS
directly to confirm content matches.

### Step 2: Share the VFS with the agent

Connect the workspace VFS to the agent's filesystem.

- Replace `connect_fs(type="virtual")` with the same VFS instance (or mount
  it within the agent's VFS via MountFS)
- When marimo writes `notebook.py` to VFS, agent can read it
- When agent writes `notebook.py` to VFS, inject `SyncGraphCommand` into the
  kernel to update the editor (preferred — keeps everything in VFS)
- Fallback: if direct command injection is non-viable, write a real file and
  let marimo's file watcher detect it

**Key decision: bypass the file watcher (option B)**

marimo's file watcher watches the real filesystem. With everything in VFS,
the watcher won't fire. Instead of keeping a real file as a sync point, inject
`SyncGraphCommand` directly into the kernel's control queue after an agent
write. This means the notebook truly lives only in VFS.

To implement:
- Parse the VFS notebook file into cells (marimo's own parser or simple
  `@app.cell` splitting)
- Build a `SyncGraphCommand` with the cell IDs and code
- Put it on the kernel's control queue via `session.put_control_request()`

**Validation:** Agent writes `notebook.py` to VFS → editor updates without
any real file on disk.

### Step 3: Build widget ID-to-name mapping

Map UI element object IDs (UUIDs) to Python variable names by scanning the
shared kernel namespace.

- Write `_build_widget_id_map() -> dict[str, str]` that iterates
  `kernel.globals`
- For each value, check if it's a `marimo.ui.*` instance (has `._id` or
  similar attribute)
- Return `{object_id: variable_name}`
- Cache the mapping; invalidate when cells re-execute (hook into post-
  execution callback or cell completion notification)

**Validation:** Notebook has `slider = mo.ui.slider(...)`. Mapping function
returns `{"<uuid>": "slider"}`.

### Step 4: Hook widget state changes

Detect `UpdateUIElementCommand` and write widget state to the shared VFS.

- Monkey-patch `SessionView.add_control_request` (or the `QueueExtension`
  that processes the control queue)
- On `UpdateUIElementCommand`:
  1. Use ID-to-name mapping from Step 3
  2. Build `{"slider": 73, "dropdown": "option_b", ...}`
  3. Debounce writes (~200ms) to handle rapid slider drags
  4. Write `widget_state.json` to the shared VFS

**Debounce approach:** Use a threading timer. Each widget change resets the
timer. When the timer fires, write the accumulated state.

**Validation:** Move slider in editor → `widget_state.json` appears in VFS
within ~200ms with `{"slider": 73}`.

### Step 5: Agent sees file events

Wire VFS changes into agex's event system.

- If the agent's VFS is the same instance, agex may already emit events on
  writes — verify this
- If not, add a write callback/hook on the VFS that emits file events into
  the agent's event stream
- Agent's event log should show:
  - `notebook.py modified` when user edits cells
  - `widget_state.json modified` when user changes widgets

**Validation:** User edits a cell → agent's event log shows file change
without any polling.

### Step 6: Update bridge and primer

- `write_notebook()` → writes to VFS + injects `SyncGraphCommand` (instead
  of writing real file)
- `get_notebook_data()` → reads kernel globals directly (already done)
- Re-add `get_widget_state()` → reads `widget_state.json` from VFS (or
  reads kernel globals + ID mapping directly)
- Update primer: teach agent about file events and widget state awareness
- Agent can now react to events: "I see you changed the threshold to 73..."

## Key Risk: File Watcher Loop

When both marimo and the agent can write `notebook.py`, there's a risk of
echo loops:

1. Agent writes notebook → SyncGraphCommand → kernel updates
2. Kernel normalizes cell signatures → marimo saves → VFS write → event
3. Agent sees event → reads notebook → writes again...

**Mitigation:** Content-hash comparison. Before emitting a file event, check
if the content actually changed (hash the bytes). If the hash matches the
last known state, suppress the event.

## Non-Goals for Phase 2

- Real filesystem persistence (notebook lives only in VFS; persistence comes
  from kvgit in a future phase)
- Branch switching / session switching (future — kvgit swap of VFS contents)
- Full sandtrap instrumentation of cell execution (separate concern)
