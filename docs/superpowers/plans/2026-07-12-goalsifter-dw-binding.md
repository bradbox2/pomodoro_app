# GoalSifter DW Binding Implementation Plan

> **For agentic workers:** Execute this plan inline, task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an offline-first FocusFlow client integration for the locked GoalSifter desktop API contract.

**Architecture:** Keep FocusFlow's SQLite database as the local source for sessions, drafts, focus-item bindings and a durable Outbox. A standard-library HTTP client talks only to a localhost SSH tunnel and never reads GoalSifter internals. The UI may bind a local task to a selected remote DW task or explicitly create a DW task; only bound completed work sessions enter the Outbox.

**Tech Stack:** Python 3.11, SQLite, CustomTkinter, `subprocess` SSH, `urllib.request`, pytest.

---

### Task 1: Persist integration settings and device identity

**Files:**
- Modify: `app_paths.py`, `app_config_manager.py`
- Create: `goalsifter_settings.py`
- Test: `tests/test_goalsifter_settings.py`

- [ ] Write tests for a generated stable `device_id`, a user-data-local settings file, and an empty token being disabled.
- [ ] Implement `GoalSifterSettings` with `ssh_host_alias`, `local_port`, `bearer_token`, and `device_id`; default to disabled until token and alias are both set.
- [ ] Run the focused test, then document the manual token provisioning rule in README and ROADMAP.

### Task 2: Add local focus-item and Outbox persistence

**Files:**
- Modify: `pomodoro_data_manager.py`
- Test: `tests/test_focusflow_sync_store.py`

- [ ] Write failing tests proving a local task receives a stable local focus-item UUID, binding stores only `goalsifter_task_id`, and a completed bound Work session queues exactly one event with its stable session UUID.
- [ ] Add forward-only SQLite migration tables: `focus_items(local_id, project_name, task_name, goalsifter_task_id, state)` and `focus_outbox(event_id, device_id, task_id, started_at, ended_at, duration_minutes, status, attempts, last_error)`.
- [ ] Make `record_session()` accept or generate `session_id`, return it, and atomically add an Outbox item only for completed Work sessions with a bound task.
- [ ] Run focused persistence tests and the full suite.

### Task 3: Implement SSH-tunnel API client

**Files:**
- Create: `goalsifter_client.py`
- Test: `tests/test_goalsifter_client.py`

- [ ] Write tests using a local HTTP server for Authorization headers, the locked task snapshot schema, 401/422 responses, and duplicate event responses.
- [ ] Implement an SSH tunnel manager using `ssh -N -L <local_port>:127.0.0.1:8000 <alias>` and a standard-library JSON client targeting only `http://127.0.0.1:<local_port>/api/v1/focusflow/`.
- [ ] Implement calls for `GET tasks`, `POST pomo-events`, and explicit `POST tasks`; expose typed client errors without silently retrying non-idempotent creation.
- [ ] Run the focused client tests.

### Task 4: Bind and create DW tasks explicitly

**Files:**
- Modify: `main.py`, `ui_manager.py`
- Test: `tests/test_focusflow_binding.py`

- [ ] Write failing controller-level tests for showing only remote snapshot tasks, preserving local drafts, explicit binding by `task_id`, and 422 create failures without creating a local cloud binding.
- [ ] Add a compact GoalSifter action area to select a snapshot DW task, bind the current local task, or explicitly create a DW task from the local name and estimate.
- [ ] Refresh remote tasks only on explicit user action; a network failure keeps local task entry and reports offline status.
- [ ] Run focused UI/controller tests without opening a real window.

### Task 5: Flush Outbox safely after user-triggered sync

**Files:**
- Modify: `main.py`, `pomodoro_data_manager.py`, `ui_manager.py`
- Test: `tests/test_focusflow_outbox.py`

- [ ] Write failing tests for an offline completed session remaining queued, a successful `duplicate: true` response clearing the row, and a 422 response retaining the row with an error.
- [ ] Add an explicit Sync action that establishes the tunnel, uploads pending rows in creation order, and clears only 200 responses carrying the matching `event_id`.
- [ ] Ensure task selection and work sessions remain usable while the tunnel is unavailable.
- [ ] Run full pytest, compile production modules, and record the exact verification output.
