from datetime import datetime

import pytest

from pomodoro_data_manager import PomodoroDataManager


def test_rename_project_preserves_tasks_focus_items_and_sessions(tmp_path):
    manager = PomodoroDataManager(str(tmp_path), "focusflow.db")
    manager.add_or_update_task("Legacy", "Prepare brief", 8)
    manager.record_session({
        "project_name": "Legacy", "task_name": "Prepare brief", "session_type": "Work",
        "start_time": datetime(2026, 7, 12, 9), "end_time": datetime(2026, 7, 12, 9, 25),
        "duration_minutes": 25, "status": "Completed",
    })

    manager.rename_local_project("Legacy", "Strategy")

    assert manager.get_all_projects() == ["Strategy"]
    assert manager.get_tasks_for_project("Strategy") == ["Prepare brief"]
    assert manager.get_completed_work_sessions_for_task("Strategy", "Prepare brief") == 1
    assert manager.get_local_focus_items()[0]["project_name"] == "Strategy"
    manager.close()


def test_rename_project_refuses_an_existing_target(tmp_path):
    manager = PomodoroDataManager(str(tmp_path), "focusflow.db")
    manager.add_project("Source")
    manager.add_project("Existing")

    with pytest.raises(ValueError, match="already exists"):
        manager.rename_local_project("Source", "Existing")

    assert manager.get_all_projects() == ["Existing", "Source"]
    manager.close()


def test_merge_projects_rejects_duplicate_task_names_without_partial_changes(tmp_path):
    manager = PomodoroDataManager(str(tmp_path), "focusflow.db")
    manager.add_or_update_task("Old A", "Same task", 2)
    manager.add_or_update_task("Target", "Same task", 3)

    with pytest.raises(ValueError, match="Same task"):
        manager.merge_local_projects(["Old A"], "Target")

    assert manager.get_all_projects() == ["Old A", "Target"]
    assert manager.get_tasks_for_project("Old A") == ["Same task"]
    manager.close()


def test_merge_projects_moves_all_local_records_and_removes_sources(tmp_path):
    manager = PomodoroDataManager(str(tmp_path), "focusflow.db")
    manager.add_or_update_task("Old A", "Task A", 2)
    manager.add_or_update_task("Old B", "Task B", 3)

    manager.merge_local_projects(["Old A", "Old B"], "Consolidated")

    assert manager.get_all_projects() == ["Consolidated"]
    assert manager.get_tasks_for_project("Consolidated") == ["Task A", "Task B"]
    assert {item["project_name"] for item in manager.get_local_focus_items()} == {"Consolidated"}
    manager.close()


def test_only_empty_local_project_can_be_deleted(tmp_path):
    manager = PomodoroDataManager(str(tmp_path), "focusflow.db")
    manager.add_project("Empty")
    manager.add_or_update_task("Busy", "Keep", 1)

    manager.delete_empty_local_project("Empty")
    with pytest.raises(ValueError, match="contains tasks"):
        manager.delete_empty_local_project("Busy")

    assert manager.get_all_projects() == ["Busy"]
    manager.close()


def test_project_manager_excludes_goalsifter_internal_mirrors(tmp_path):
    manager = PomodoroDataManager(str(tmp_path), "focusflow.db")
    manager.add_project("Local")
    manager.add_project("XXgoalsifterYY:local")
    manager.upsert_goalsifter_focus_item({
        "task_id": "dw-1", "task_name": "Remote", "kr_ref": "q1k1",
        "pomo_estimate": 1, "pomo_count": 0, "status": "active",
    })

    assert [row["project_name"] for row in manager.get_local_project_summaries()] == ["Local", "XXgoalsifterYY:local"]
    manager.close()
