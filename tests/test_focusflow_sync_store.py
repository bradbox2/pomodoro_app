from datetime import datetime

from focusflow.pomodoro_data_manager import PomodoroDataManager


def test_bound_completed_work_session_is_queued_once_with_its_session_uuid(tmp_path):
    manager = PomodoroDataManager(str(tmp_path), "focusflow.db")
    manager.add_or_update_task("Local", "Write proposal", 2)

    focus_item = manager.ensure_focus_item("Local", "Write proposal")
    manager.bind_focus_item(focus_item["local_id"], "gs-task-uuid-1")

    session_id = manager.record_session({
        "project_name": "Local",
        "task_name": "Write proposal",
        "session_type": "Work",
        "start_time": datetime(2026, 7, 12, 9, 0),
        "end_time": datetime(2026, 7, 12, 9, 25),
        "duration_minutes": 25,
        "status": "Completed",
        "device_id": "device-uuid-1",
    })

    outbox = manager.get_pending_focusflow_events()

    assert outbox == [{
        "event_id": session_id,
        "device_id": "device-uuid-1",
        "task_id": "gs-task-uuid-1",
        "started_at": "2026-07-12T09:00:00",
        "ended_at": "2026-07-12T09:25:00",
        "duration_minutes": 25,
        "status": "completed",
    }]
    manager.close()


def test_unbound_local_draft_never_enters_the_outbox(tmp_path):
    manager = PomodoroDataManager(str(tmp_path), "focusflow.db")
    manager.add_or_update_task("Local", "Offline draft", 1)

    focus_item = manager.ensure_focus_item("Local", "Offline draft")
    manager.record_session({
        "project_name": "Local",
        "task_name": "Offline draft",
        "session_type": "Work",
        "start_time": datetime(2026, 7, 12, 9, 0),
        "end_time": datetime(2026, 7, 12, 9, 25),
        "duration_minutes": 25,
        "status": "Completed",
        "device_id": "device-uuid-1",
    })

    assert focus_item["state"] == "draft"
    assert manager.get_pending_focusflow_events() == []
    manager.close()


def test_binding_a_completed_local_draft_backfills_its_original_session_event(tmp_path):
    manager = PomodoroDataManager(str(tmp_path), "focusflow.db")
    manager.add_or_update_task("Local", "Write retrospective", 1)
    session_id = manager.record_session({
        "project_name": "Local", "task_name": "Write retrospective",
        "session_type": "Work", "start_time": datetime(2026, 7, 12, 9, 0),
        "end_time": datetime(2026, 7, 12, 9, 25), "duration_minutes": 25,
        "status": "Completed", "device_id": "device-uuid-1",
    })

    focus_item = manager.ensure_focus_item("Local", "Write retrospective")
    manager.bind_focus_item(focus_item["local_id"], "gs-task-uuid-2", "device-uuid-1")

    assert manager.get_pending_focusflow_events()[0]["event_id"] == session_id
    assert manager.get_pending_focusflow_events()[0]["task_id"] == "gs-task-uuid-2"
    manager.close()


def test_outbox_event_is_removed_only_after_explicit_acknowledgement(tmp_path):
    manager = PomodoroDataManager(str(tmp_path), "focusflow.db")
    manager.add_or_update_task("Local", "Sync me", 1)
    focus_item = manager.ensure_focus_item("Local", "Sync me")
    manager.bind_focus_item(focus_item["local_id"], "gs-task-uuid-3", "device-uuid-1")
    session_id = manager.record_session({
        "project_name": "Local", "task_name": "Sync me", "session_type": "Work",
        "start_time": datetime(2026, 7, 12, 9), "end_time": datetime(2026, 7, 12, 9, 25),
        "duration_minutes": 25, "status": "Completed", "device_id": "device-uuid-1",
    })

    manager.mark_focusflow_event_synced(session_id)

    assert manager.get_pending_focusflow_events() == []
    manager.close()


def test_conflicted_outbox_event_is_blocked_and_not_retried(tmp_path):
    manager = PomodoroDataManager(str(tmp_path), "focusflow.db")
    manager.add_or_update_task("Local", "Conflict", 1)
    focus_item = manager.ensure_focus_item("Local", "Conflict")
    manager.bind_focus_item(focus_item["local_id"], "gs-task-conflict", "device-uuid-1")
    session_id = manager.record_session({
        "project_name": "Local", "task_name": "Conflict", "session_type": "Work",
        "start_time": datetime(2026, 7, 12, 9), "end_time": datetime(2026, 7, 12, 9, 25),
        "duration_minutes": 25, "status": "Completed", "device_id": "device-uuid-1",
    })

    manager.mark_focusflow_event_conflict(session_id, "event payload mismatch")

    assert manager.get_pending_focusflow_events() == []
    assert manager.get_blocked_focusflow_events()[0]["event_id"] == session_id
    manager.close()
