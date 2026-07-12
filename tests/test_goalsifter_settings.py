import json
import uuid

from focusflow.app_paths import AppPaths
from focusflow.goalsifter_settings import GoalSifterSettings


def test_settings_are_created_in_user_data_with_a_stable_device_id(tmp_path):
    paths = AppPaths(install_dir=tmp_path / "install", data_dir=tmp_path / "FocusFlow")

    first = GoalSifterSettings.load(paths)
    second = GoalSifterSettings.load(paths)

    assert paths.goalsifter_settings_path.exists()
    assert first.device_id == second.device_id
    assert uuid.UUID(first.device_id)
    assert first.is_configured is False


def test_settings_require_an_alias_and_token_before_enabling(tmp_path):
    paths = AppPaths(install_dir=tmp_path / "install", data_dir=tmp_path / "FocusFlow")
    paths.ensure_ready()
    paths.goalsifter_settings_path.write_text(json.dumps({
        "device_id": str(uuid.uuid4()),
        "ssh_host_alias": "goalsifter",
        "local_port": 18000,
        "bearer_token": "",
    }), encoding="utf-8")

    settings = GoalSifterSettings.load(paths)

    assert settings.ssh_host_alias == "goalsifter"
    assert settings.is_configured is False


def test_auto_connect_defaults_false_and_round_trips(tmp_path):
    paths = AppPaths(install_dir=tmp_path / "install", data_dir=tmp_path / "FocusFlow")

    settings = GoalSifterSettings.load(paths)
    assert settings.auto_connect is False

    settings.update_connection(
        paths,
        ssh_host_alias="  openclaw  ",
        bearer_token="  tok-123  ",
        local_port=18000,
        auto_connect=True,
    )

    reloaded = GoalSifterSettings.load(paths)
    assert reloaded.auto_connect is True
    assert reloaded.ssh_host_alias == "openclaw"   # trimmed
    assert reloaded.bearer_token == "tok-123"       # trimmed
    assert reloaded.is_configured is True
    assert reloaded.device_id == settings.device_id  # unchanged


def test_update_connection_persists_port_as_int(tmp_path):
    paths = AppPaths(install_dir=tmp_path / "install", data_dir=tmp_path / "FocusFlow")
    settings = GoalSifterSettings.load(paths)

    settings.update_connection(
        paths, ssh_host_alias="host", bearer_token="t",
        local_port="18022", auto_connect=False,
    )

    stored = json.loads(paths.goalsifter_settings_path.read_text(encoding="utf-8"))
    assert stored["local_port"] == 18022
    assert stored["auto_connect"] is False
