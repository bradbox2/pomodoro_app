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
