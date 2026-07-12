import json

from app_config_manager import AppConfigManager


def test_config_manager_creates_default_at_the_requested_user_path(tmp_path):
    config_path = tmp_path / "FocusFlow" / "config.json"

    manager = AppConfigManager(config_path)

    assert config_path.exists()
    assert "External" in manager.get_interruption_reasons()
    assert any(mood["name"] == "Excited" for mood in manager.get_feedback_moods())


def test_config_manager_migrates_legacy_strings_at_the_requested_user_path(tmp_path):
    config_path = tmp_path / "FocusFlow" / "config.json"
    config_path.parent.mkdir()
    config_path.write_text(json.dumps({
        "interruptions": {"External": ["Aliens"], "Internal": ["Hunger"]},
        "feedback": {"moods": ["Sleepy"]},
    }), encoding="utf-8")

    manager = AppConfigManager(config_path)

    assert manager.get_interruption_reasons()["External"][0]["name"] == "Aliens"
    assert manager.get_feedback_moods()[0]["name"] == "Sleepy"
