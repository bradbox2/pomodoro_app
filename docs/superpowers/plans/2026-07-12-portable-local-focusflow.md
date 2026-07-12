# FocusFlow Local-Only Portability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore a runnable local FocusFlow installation whose user data survives reinstall and which contains no active cloud-sync behavior.

**Architecture:** Keep application resources beside the executable/source, but resolve mutable user state under `%LOCALAPPDATA%\\FocusFlow`. On first run, copy legacy project-root data/configuration into that location without deleting the original. Remove the PocketBase/SSH synchronization path entirely; local SQLite remains the sole runtime store.

**Tech Stack:** Python 3.11, CustomTkinter, SQLite, pytest, PyInstaller.

---

### Task 1: Establish repeatable local test/runtime setup

**Files:**
- Create: `requirements-dev.txt`
- Create: `pytest.ini`
- Modify: `requirements.txt`

- [ ] Add `pytest>=8.0` to development dependencies and configure pytest to collect only `tests/test_*.py`.
- [ ] Install runtime and development dependencies into `.venv`.
- [ ] Run `.venv\\Scripts\\python.exe -m pytest -q` and record the pre-change result.

### Task 2: Add test-first user-data path and legacy-migration service

**Files:**
- Create: `app_paths.py`
- Create: `tests/test_app_paths.py`

- [ ] Write tests proving that `FOCUSFLOW_DATA_DIR` overrides the default, the default is `%LOCALAPPDATA%\\FocusFlow`, and legacy files are copied once without replacing existing user files.
- [ ] Run the focused test and confirm it fails because `app_paths` does not exist.
- [ ] Implement `AppPaths` with `data_dir`, `config_path`, `backup_dir`, `logs_dir`, `exports_dir`, and `migrate_legacy_state()`.
- [ ] Run the focused test until it passes.

### Task 3: Move mutable state to the user-data location

**Files:**
- Modify: `main.py`
- Modify: `app_config_manager.py`
- Modify: `analysis_manager.py`
- Test: `tests/test_app_paths.py`

- [ ] Add a failing test that starts path setup against a temporary legacy project directory and asserts database/config paths resolve under the temporary user-data root.
- [ ] Replace project-root `data/` and mutable `config.json` assumptions with `AppPaths`; create backup, logs, and exports directories at startup.
- [ ] Pass the resolved export directory to analysis output and the resolved config path to configuration management.
- [ ] Run focused tests and then the full test suite.

### Task 4: Remove all active cloud synchronization behavior

**Files:**
- Modify: `main.py`
- Modify: `pomodoro_data_manager.py`
- Modify: `config.py`
- Delete: `pb_sync_manager.py`
- Delete: `sync_manager.py`
- Delete: `init_pb.py`
- Delete: `.env.example`
- Modify: `requirements.txt`
- Test: `tests/test_local_only_runtime.py`

- [ ] Write a test proving `PomodoroDataManager.record_session()` records a session without importing or calling a sync module.
- [ ] Run it and confirm the existing implementation fails the no-sync expectation.
- [ ] Remove synchronization imports, callbacks, task pulls, UI sync wiring, environment variables, network dependencies, and disabled legacy configuration.
- [ ] Remove `requests` and `python-dotenv` from runtime requirements if no remaining production module imports them.
- [ ] Run the local-only test and the full suite.

### Task 5: Make source and packaged launches consistent

**Files:**
- Modify: `Pomodoro-start.bat`
- Modify: `Pomodoro.bat`
- Modify: `FocusFlow.spec`
- Modify: `README.md`
- Test: `tests/test_launch_contract.py`

- [ ] Write tests/assertions for a single `.venv` launch convention and absence of cloud configuration in packaging documentation.
- [ ] Update both launchers to resolve their own directory and run `.venv\\Scripts\\pythonw.exe`; give an actionable missing-venv message.
- [ ] Update the build spec and README with install, data-location, legacy-migration, backup, and office-PC setup instructions.
- [ ] Run the full suite and compile all production modules.

### Task 6: Validate a clean-machine bootstrap

**Files:**
- Test: `tests/test_app_paths.py`
- Test: `tests/test_local_only_runtime.py`

- [ ] Use a temporary data root to instantiate the data manager, create a project/task/session, and reopen it.
- [ ] Confirm no network/SSH/PocketBase import is needed and data persists across reopen.
- [ ] Run `.venv\\Scripts\\python.exe -m pytest -q` and `.venv\\Scripts\\python.exe -m compileall -q .`.
