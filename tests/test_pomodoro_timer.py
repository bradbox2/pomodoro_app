from datetime import datetime

from focusflow.pomodoro_timer import PomodoroTimer


def test_countdown_uses_monotonic_deadline_and_finishes_once(monkeypatch):
    now = iter([100.0, 100.0, 100.4, 101.0, 101.1])
    monkeypatch.setattr("focusflow.pomodoro_timer.time.monotonic", lambda: next(now))
    waits = []
    updates = []
    finishes = []

    timer = PomodoroTimer(1, 1, 1, updates.append, lambda *args: finishes.append(args))
    timer._stop_event.wait = lambda timeout: waits.append(timeout) or False
    timer._countdown(1)

    assert updates[-1] == "00:00"
    assert finishes == [("Work", 1, "Completed")]
    assert waits


def test_reset_records_at_least_one_minute_for_a_short_interruption(monkeypatch):
    timer = PomodoroTimer(25, 5, 15, lambda *_args: None, lambda *_args: None)
    timer.start_time = datetime.now()
    timer._started_monotonic = 10.0
    monkeypatch.setattr("focusflow.pomodoro_timer.time.monotonic", lambda: 10.2)

    timer._timer_thread = None
    _, duration, status = timer.reset()

    assert duration == 1
    assert status == "Interrupted"
