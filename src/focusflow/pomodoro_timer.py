# pomodoro_timer.py
import threading
import time
import math
from datetime import datetime

class PomodoroTimer:
    """Handles the core timer logic for the Pomodoro application."""

    def __init__(self, work_min, short_break_min, long_break_min, update_callback, finish_callback):
        """
        Initializes the PomodoroTimer.

        Args:
            work_min (int): Duration of a work session in minutes.
            short_break_min (int): Duration of a short break in minutes.
            long_break_min (int): Duration of a long break in minutes.
            update_callback (callable): Function to call for UI timer updates.
            finish_callback (callable): Function to call when a session finishes.
        """
        self.settings = {
            "Work": work_min,
            "Short Break": short_break_min,
            "Long Break": long_break_min,
        }
        self.update_callback = update_callback
        self.finish_callback = finish_callback

        self.current_session_type = "Work"
        self.start_time = None

        self._timer_thread = None
        self._stop_event = threading.Event()
        self._started_monotonic = None
        self._deadline = None

    def start(self, session_type):
        """
        Starts a new timer session in a separate thread.

        Args:
            session_type (str): The type of session to start ('Work', 'Short Break', 'Long Break').
        """
        if self._timer_thread and self._timer_thread.is_alive():
            return  # Timer is already running

        self.current_session_type = session_type
        self.start_time = datetime.now()
        duration_seconds = self.settings[session_type] * 60
        self._started_monotonic = time.monotonic()
        self._deadline = self._started_monotonic + duration_seconds

        self._stop_event.clear()
        self._timer_thread = threading.Thread(
            target=self._countdown,
            args=(duration_seconds,)
        )
        self._timer_thread.daemon = True
        self._timer_thread.start()

    def reset(self):
        """Stops the current timer."""
        if self._timer_thread and self._timer_thread.is_alive():
            self._stop_event.set()
            self._timer_thread.join() # Wait for the thread to finish

        duration = 0
        status = "Interrupted"
        if self.start_time:
            if self._started_monotonic is not None:
                elapsed_seconds = max(0.0, time.monotonic() - self._started_monotonic)
            else:
                elapsed_seconds = max(0.0, (datetime.now() - self.start_time).total_seconds())
            if elapsed_seconds > 0:
                duration = max(1, math.ceil(elapsed_seconds / 60))

        # Reset to initial state
        self.start_time = None
        self._started_monotonic = None
        self._deadline = None
        return self.current_session_type, duration, status


    def _countdown(self, count):
        """
        The actual countdown logic that runs in a thread.

        Args:
            count (int): The total seconds to count down from.
        """
        deadline = self._deadline or (time.monotonic() + count)
        while not self._stop_event.is_set():
            remaining = max(0, math.ceil(deadline - time.monotonic()))
            mins, secs = divmod(remaining, 60)
            self.update_callback(f"{mins:02d}:{secs:02d}")
            if remaining <= 0:
                break
            if self._stop_event.wait(min(1.0, max(0.0, deadline - time.monotonic()))):
                return

        # Check if the timer finished naturally (was not stopped)
        if not self._stop_event.is_set():
            self.update_callback("00:00")
            duration = self.settings[self.current_session_type]
            self.finish_callback(self.current_session_type, duration, "Completed")
