from datetime import datetime

import pytest

from focusflow.pomodoro_data_manager import PomodoroDataManager


def test_existing_local_task_is_exposed_as_a_draft_with_progress(tmp_path):
    manager = PomodoroDataManager(str(tmp_path), "focusflow.db")
    manager.add_or_update_task("Office", "Prepare proposal", 2)
    manager.record_session({
        "project_name": "Office", "task_name": "Prepare proposal",
        "session_type": "Work", "start_time": datetime(2026, 7, 12, 9),
        "end_time": datetime(2026, 7, 12, 9, 25), "duration_minutes": 25,
        "status": "Completed",
    })

    items = manager.get_local_focus_items()

    assert len(items) == 1
    assert items[0]["local_id"]
    assert {key: value for key, value in items[0].items() if key != "local_id"} == {
        "project_name": "Office", "task_name": "Prepare proposal",
        "estimate": 2, "completed_count": 1, "state": "draft",
    }
    manager.close()


def test_goalsifter_dw_is_mirrored_by_remote_id_with_kr_context(tmp_path):
    manager = PomodoroDataManager(str(tmp_path), "focusflow.db")

    item = manager.upsert_goalsifter_focus_item({
        "task_id": "dw-42", "task_name": "Validate pricing", "kr_ref": "q2k3",
        "pomo_estimate": 2, "pomo_count": 1, "status": "active",
    })
    same_item = manager.upsert_goalsifter_focus_item({
        "task_id": "dw-42", "task_name": "Validate pricing v2", "kr_ref": "q2k3",
        "pomo_estimate": 3, "pomo_count": 1, "status": "active",
    })

    assert item["local_id"] == same_item["local_id"]
    assert item["source"] == "goalsifter"
    assert item["context_label"] == "q2k3"
    remote_items = manager.get_goalsifter_focus_items()
    assert [{key: value for key, value in row.items() if key != "local_id"} for row in remote_items] == [{
        "project_name": "__goalsifter__:dw-42", "task_name": "Validate pricing v2",
        "estimate": 3, "completed_count": 0, "state": "bound",
        "source": "goalsifter", "context_label": "q2k3", "goalsifter_task_id": "dw-42",
    }]
    manager.close()


def test_goalsifter_mirror_is_not_listed_as_a_local_draft(tmp_path):
    manager = PomodoroDataManager(str(tmp_path), "focusflow.db")
    manager.upsert_goalsifter_focus_item({
        "task_id": "dw-99", "task_name": "Remote only", "kr_ref": "q1k2",
        "pomo_estimate": 1, "pomo_count": 0, "status": "active",
    })

    assert manager.get_local_focus_items() == []
    assert len(manager.get_goalsifter_focus_items()) == 1
    manager.close()


def test_reconcile_goalsifter_focus_items_archives_tasks_missing_from_active_snapshot(tmp_path):
    manager = PomodoroDataManager(str(tmp_path), "focusflow.db")
    manager.upsert_goalsifter_focus_item({
        "task_id": "dw-done", "task_name": "Already done", "kr_ref": None,
        "pomo_estimate": 1, "pomo_count": 0, "status": "active",
    })

    manager.reconcile_goalsifter_focus_items({"dw-other"})

    assert manager.get_goalsifter_focus_items() == []
    manager.close()


def test_reconcile_empty_goalsifter_snapshot_archives_all_remote_tasks(tmp_path):
    manager = PomodoroDataManager(str(tmp_path), "focusflow.db")
    manager.upsert_goalsifter_focus_item({
        "task_id": "dw-done", "task_name": "Already done", "kr_ref": None,
        "pomo_estimate": 1, "pomo_count": 0, "status": "active",
    })

    manager.reconcile_goalsifter_focus_items(set())

    assert manager.get_goalsifter_focus_items() == []
    manager.close()


def test_merge_accepts_database_path_containing_single_quote(tmp_path):
    source_dir = tmp_path / "source's data"
    target_dir = tmp_path / "target"
    source_dir.mkdir()
    target_dir.mkdir()
    source = PomodoroDataManager(str(source_dir), "source.db")
    source.add_or_update_task("Office", "Imported", 2)
    source.close()

    target = PomodoroDataManager(str(target_dir), "target.db")
    target.merge_from(str(source_dir / "source.db"))

    assert target.get_task_details("Office", "Imported")["estimate"] == 2
    target.close()


def test_archived_local_task_leaves_execution_queue_but_keeps_history(tmp_path):
    manager = PomodoroDataManager(str(tmp_path), "focusflow.db")
    manager.add_or_update_task("Local", "Old task", 4)
    manager.archive_local_focus_item("Local", "Old task")

    assert manager.get_local_focus_items() == []
    assert manager.get_archived_local_focus_items()[0]["task_name"] == "Old task"
    manager.restore_local_focus_item("Local", "Old task")
    assert manager.get_local_focus_items()[0]["task_name"] == "Old task"
    manager.close()


@pytest.mark.parametrize("estimate", [0, 5, 100])
def test_local_focus_item_rejects_estimates_outside_one_to_four(tmp_path, estimate):
    manager = PomodoroDataManager(str(tmp_path), "focusflow.db")

    with pytest.raises(ValueError, match="between 1 and 4"):
        manager.add_or_update_task("Office", "Too large", estimate)

    assert manager.get_all_projects() == []
    manager.close()
