import json
import socket

from focusflow.goalsifter_client import GoalSifterClient, GoalSifterRemoteError
from focusflow.goalsifter_settings import GoalSifterSettings


def _configured_settings():
    return GoalSifterSettings(
        device_id="device-1",
        ssh_host_alias="goalsifter",
        local_port=18000,
        bearer_token="token-1",
    )


def test_task_snapshot_uses_localhost_contract_and_bearer_token():
    calls = []

    def request(method, url, headers, body=None):
        calls.append((method, url, headers, body))
        return 200, json.dumps([{
            "task_id": "dw-1", "task_name": "Write", "kr_ref": "kr-1",
            "pomo_estimate": 2, "pomo_count": 0, "status": "active",
            "created_at": "2026-07-12T09:00:00", "last_event_at": None,
        }]).encode()

    tasks = GoalSifterClient(_configured_settings(), request=request).get_active_dw_tasks()

    assert tasks[0].task_id == "dw-1"
    assert calls == [(
        "GET", "http://127.0.0.1:18000/api/v1/focusflow/tasks",
        {"Authorization": "Bearer token-1"}, None,
    )]


def test_task_snapshot_accepts_server_tasks_envelope():
    # The deployed GoalSifter server wraps the snapshot as {"tasks": [...]}.
    def request(_method, _url, _headers, _body=None):
        return 200, json.dumps({"tasks": [{
            "task_id": "dw-2", "task_name": "确定IB开发方向", "kr_ref": None,
            "pomo_estimate": 3, "pomo_count": 0, "status": "活跃",
            "created_at": "2026-07-12T01:04:43", "last_event_at": "2026-07-12 09:04:43",
        }]}).encode()

    tasks = GoalSifterClient(_configured_settings(), request=request).get_active_dw_tasks()

    assert len(tasks) == 1
    assert tasks[0].task_id == "dw-2"
    assert tasks[0].status == "活跃"


def test_empty_tasks_envelope_yields_no_tasks():
    def request(_method, _url, _headers, _body=None):
        return 200, json.dumps({"tasks": []}).encode()

    tasks = GoalSifterClient(_configured_settings(), request=request).get_active_dw_tasks()

    assert tasks == []


def test_duplicate_event_is_a_successful_idempotent_response():
    def request(_method, _url, _headers, _body=None):
        return 200, json.dumps({
            "event_id": "event-1", "duplicate": True, "task_id": "dw-1",
            "pomo_count": 2, "exp_awarded": 0,
        }).encode()

    result = GoalSifterClient(_configured_settings(), request=request).post_pomo_event({
        "event_id": "event-1", "device_id": "device-1", "task_id": "dw-1",
        "started_at": "2026-07-12T09:00:00", "ended_at": "2026-07-12T09:25:00",
        "duration_minutes": 25, "status": "completed",
    })

    assert result["duplicate"] is True


def test_is_tunnel_ready_true_when_port_listening():
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    try:
        settings = GoalSifterSettings(
            device_id="device-1", ssh_host_alias="goalsifter",
            local_port=port, bearer_token="token-1",
        )
        assert GoalSifterClient(settings).is_tunnel_ready() is True
    finally:
        listener.close()


def test_is_tunnel_ready_false_when_nothing_listening():
    # Bind then close to obtain a port that is (almost certainly) now free.
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()

    settings = GoalSifterSettings(
        device_id="device-1", ssh_host_alias="goalsifter",
        local_port=port, bearer_token="token-1",
    )
    assert GoalSifterClient(settings).is_tunnel_ready(timeout=0.2) is False


def test_contract_422_is_exposed_without_retrying():
    def request(_method, _url, _headers, _body=None):
        return 422, b'{"detail":"task is not active dw"}'

    client = GoalSifterClient(_configured_settings(), request=request)

    try:
        client.post_pomo_event({"event_id": "event-1"})
    except GoalSifterRemoteError as error:
        assert error.status_code == 422
    else:
        raise AssertionError("Expected GoalSifterRemoteError")
