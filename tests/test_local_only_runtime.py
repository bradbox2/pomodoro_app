import inspect
import sys
from datetime import datetime

from pomodoro_data_manager import PomodoroDataManager


def test_recording_a_session_never_loads_or_calls_a_sync_module(tmp_path):
    sys.modules.pop("sync_manager", None)
    manager = PomodoroDataManager(str(tmp_path), "focusflow.db")

    manager.record_session({
        "project_name": "Local Project",
        "task_name": "Local Task",
        "session_type": "Work",
        "start_time": datetime(2026, 7, 12, 9, 0),
        "end_time": datetime(2026, 7, 12, 9, 25),
        "duration_minutes": 25,
        "status": "Completed",
    })

    assert "sync_manager" not in sys.modules
    assert "SyncManager" not in inspect.getsource(PomodoroDataManager)
    assert len(manager.get_all_sessions_for_analysis()) == 1
    manager.close()


def test_local_sqlite_data_persists_after_reopening(tmp_path):
    manager = PomodoroDataManager(str(tmp_path), "focusflow.db")
    manager.add_or_update_task("Office Project", "Prepare report", 2)
    manager.record_session({
        "project_name": "Office Project",
        "task_name": "Prepare report",
        "session_type": "Work",
        "start_time": datetime(2026, 7, 12, 9, 0),
        "end_time": datetime(2026, 7, 12, 9, 25),
        "duration_minutes": 25,
        "status": "Completed",
    })
    manager.close()

    reopened = PomodoroDataManager(str(tmp_path), "focusflow.db")

    assert reopened.get_all_projects() == ["Office Project"]
    assert reopened.get_completed_work_sessions_for_task("Office Project", "Prepare report") == 1
    reopened.close()
