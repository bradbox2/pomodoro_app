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
