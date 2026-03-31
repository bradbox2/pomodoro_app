# pomodoro_timer.py
import threading
import time
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
             # Calculate elapsed time if timer was running
            duration = int((datetime.now() - self.start_time).total_seconds() / 60)
        
        # Reset to initial state
        self.start_time = None
        return self.current_session_type, duration, status


    def _countdown(self, count):
        """
        The actual countdown logic that runs in a thread.

        Args:
            count (int): The total seconds to count down from.
        """
        while count > 0 and not self._stop_event.is_set():
            mins, secs = divmod(count, 60)
            self.update_callback(f"{mins:02d}:{secs:02d}")
            time.sleep(1)
            count -= 1
        
        # Check if the timer finished naturally (was not stopped)
        if not self._stop_event.is_set():
            self.update_callback("00:00")
            duration = self.settings[self.current_session_type]
            self.finish_callback(self.current_session_type, duration, "Completed")
