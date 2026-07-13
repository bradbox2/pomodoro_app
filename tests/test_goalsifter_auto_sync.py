import logging

from focusflow.main import PomodoroApp


def test_completed_remote_work_requests_outbox_sync():
    app = PomodoroApp.__new__(PomodoroApp)
    app.current_focus_source = "goalsifter"
    calls = []
    app.sync_goalsifter_outbox = lambda: calls.append(True)

    app._sync_goalsifter_after_work()

    assert calls == [True]


def test_completed_local_work_does_not_start_remote_sync():
    app = PomodoroApp.__new__(PomodoroApp)
    app.current_focus_source = "local"
    calls = []
    app.sync_goalsifter_outbox = lambda: calls.append(True)

    app._sync_goalsifter_after_work()

    assert calls == []


def test_startup_auto_connect_only_refreshes_after_local_init():
    app = PomodoroApp.__new__(PomodoroApp)
    app.goalsifter_settings = type("Settings", (), {"auto_connect": True, "is_configured": True})()
    calls = []
    app.refresh_goalsifter_tasks = lambda: calls.append("refresh")
    app.sync_goalsifter_outbox = lambda: calls.append("sync")

    class Root:
        def after(self, delay, callback):
            calls.append((delay, callback))

    app.root = Root()
    app._maybe_auto_connect_goalsifter()

    assert calls[0] == "refresh"
    assert calls == ["refresh"]


def test_remote_task_completion_calls_server_then_refreshes_snapshot():
    app = PomodoroApp.__new__(PomodoroApp)
    app.current_task = "Remote DW"
    app.current_focus_source = "goalsifter"
    app.current_goalsifter_task_id = "dw-1"
    app.is_running = False
    app.goalsifter_client = type("Client", (), {
        "complete_dw_task": lambda _self, task_id: {"task_id": task_id, "status": "已完成"},
    })()
    calls = []
    app.refresh_goalsifter_tasks = lambda: calls.append("refresh")
    app.reset_state_and_ui = lambda: calls.append("reset")

    app._complete_current_goalsifter_task()

    assert calls == ["refresh", "reset"]


def test_child_focus_events_do_not_refresh_goalsifter_state():
    app = PomodoroApp.__new__(PomodoroApp)
    app.goalsifter_settings = type("Settings", (), {"is_configured": True})()
    calls = []
    app.refresh_goalsifter_tasks = lambda: calls.append("refresh")

    app.root = object()
    event = type("Event", (), {"widget": object()})()
    app._on_goalsifter_window_focus(event)

    assert calls == []


def test_window_activation_refresh_is_debounced():
    app = PomodoroApp.__new__(PomodoroApp)
    app.goalsifter_settings = type("Settings", (), {"is_configured": True})()
    app._goalsifter_focus_refresh_job = None
    calls = []
    app.refresh_goalsifter_tasks = lambda: calls.append("refresh")

    class Root:
        def after(self, delay, callback):
            calls.append((delay, callback))
            return "focus-job"
        def after_cancel(self, job):
            calls.append(("cancel", job))

    app.root = Root()
    event = type("Event", (), {"widget": app.root})()
    app._on_goalsifter_window_focus(event)
    app._on_goalsifter_window_focus(event)

    assert calls[0][0] == 250
    assert calls[1] == ("cancel", "focus-job")


def test_refresh_queues_remote_work_without_blocking_tk_callback():
    app = PomodoroApp.__new__(PomodoroApp)
    app.goalsifter_settings = type("Settings", (), {"is_configured": True})()
    app._goalsifter_refresh_in_flight = False
    calls = []
    app._submit_goalsifter_operation = lambda operation, success, failure: calls.append("submitted")
    app.data_manager = type("Data", (), {
        "get_goalsifter_focus_items": lambda *_args: [],
    })()
    app.goalsifter_client = type("Client", (), {
        "get_active_dw_tasks": lambda *_args: [],
    })()
    app.ui = type("UI", (), {
        "refresh_goalsifter_focus_items": lambda *_args: calls.append("ui"),
    })()

    app.refresh_goalsifter_tasks()

    assert calls == ["ui", "submitted"]


def test_closing_stops_remote_worker_before_destroying_window():
    app = PomodoroApp.__new__(PomodoroApp)
    app.is_running = False
    calls = []
    app.root = type("Root", (), {
        "attributes": lambda *_args: None,
        "destroy": lambda *_args: calls.append("destroy"),
    })()
    app.data_manager = type("Data", (), {
        "close": lambda *_args: calls.append("db-close"),
    })()
    app._goalsifter_executor = type("Executor", (), {
        "shutdown": lambda _self, **kwargs: calls.append(("shutdown", kwargs)),
    })()

    app.on_closing()

    assert calls == [
        ("shutdown", {"wait": False, "cancel_futures": True}),
        "db-close",
        "destroy",
    ]


def test_unhandled_tk_callback_is_recorded(caplog):
    error = RuntimeError("callback failed")

    with caplog.at_level(logging.ERROR):
        PomodoroApp._report_callback_exception(
            RuntimeError, error, error.__traceback__
        )

    assert "Unhandled FocusFlow callback exception" in caplog.text


def test_periodic_refresh_runs_every_thirty_seconds():
    app = PomodoroApp.__new__(PomodoroApp)
    app.goalsifter_settings = type("Settings", (), {"is_configured": True})()
    calls = []
    app.refresh_goalsifter_tasks = lambda: calls.append("refresh")

    class Root:
        def after(self, delay, callback):
            calls.append((delay, callback))
            return "job"

    app.root = Root()
    app._schedule_goalsifter_periodic_refresh()
    assert calls[0][0] == 30000
    calls[0][1]()
    assert calls[1] == "refresh"
    assert calls[2][0] == 30000
