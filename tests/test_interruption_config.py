import json

import pytest

from focusflow.app_config_manager import AppConfigManager


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


def test_interruption_categories_and_reasons_can_be_managed_without_losing_ids(tmp_path):
    manager = AppConfigManager(tmp_path / "config.json")

    manager.add_interruption_category("环境")
    reason = manager.add_interruption_reason("环境", "噪音")
    renamed = manager.rename_interruption_reason("环境", reason["id"], "施工噪音")
    manager.rename_interruption_category("环境", "外部环境")

    reasons = manager.get_interruption_reasons()
    assert "环境" not in reasons
    assert reasons["外部环境"] == [{"id": reason["id"], "name": "施工噪音"}]
    assert renamed["id"] == reason["id"]


def test_category_rename_preserves_reason_alias_history(tmp_path):
    manager = AppConfigManager(tmp_path / "config.json")
    reason = manager.add_interruption_reason("External", "原始原因")
    manager.rename_interruption_reason("External", reason["id"], "新原因")

    manager.rename_interruption_category("External", "外部")

    assert "原始原因" in manager.history_manager.get_aliases("新原因")


def test_interruption_categories_and_reasons_can_be_deleted_and_leave_empty_categories(tmp_path):
    manager = AppConfigManager(tmp_path / "config.json")
    reason = manager.add_interruption_reason("External", "临时中断")

    manager.delete_interruption_reason("External", reason["id"])
    assert manager.get_interruption_reasons()["External"]
    assert all(item["id"] != reason["id"] for item in manager.get_interruption_reasons()["External"])

    manager.delete_interruption_category("External")
    assert "External" not in manager.get_interruption_reasons()


def test_feedback_moods_can_be_managed_without_losing_ids_or_alias_history(tmp_path):
    manager = AppConfigManager(tmp_path / "config.json")

    mood = manager.add_feedback_mood("专注", 8)
    renamed = manager.update_feedback_mood(mood["id"], "深度专注", 9)

    assert renamed == {"id": mood["id"], "name": "深度专注", "score": 9}
    assert manager.get_feedback_moods()[-1] == renamed
    assert "专注" in manager.history_manager.get_aliases("深度专注")

    manager.delete_feedback_mood(mood["id"])
    assert all(item["id"] != mood["id"] for item in manager.get_feedback_moods())


@pytest.mark.parametrize("operation", [
    lambda manager: manager.add_feedback_mood(" ", 5),
    lambda manager: manager.add_feedback_mood("重复", 0),
    lambda manager: manager.add_feedback_mood("重复", 11),
    lambda manager: manager.update_feedback_mood("default-mood-1", " ", 5),
])
def test_feedback_editor_rejects_invalid_values(tmp_path, operation):
    manager = AppConfigManager(tmp_path / "config.json")

    with pytest.raises(ValueError):
        operation(manager)


def test_feedback_editor_rejects_duplicate_names_and_deleting_last_mood(tmp_path):
    manager = AppConfigManager(tmp_path / "config.json")

    with pytest.raises(ValueError):
        manager.add_feedback_mood(" Excited ", 5)

    for mood in list(manager.get_feedback_moods())[1:]:
        manager.delete_feedback_mood(mood["id"])
    with pytest.raises(ValueError):
        manager.delete_feedback_mood(manager.get_feedback_moods()[0]["id"])


@pytest.mark.parametrize("operation", [
    lambda manager: manager.add_interruption_category(" "),
    lambda manager: manager.rename_interruption_category("External", " "),
    lambda manager: manager.add_interruption_reason("External", " "),
])
def test_interruption_editor_rejects_empty_names(tmp_path, operation):
    manager = AppConfigManager(tmp_path / "config.json")

    with pytest.raises(ValueError):
        operation(manager)


def test_interruption_editor_rejects_duplicate_sibling_names(tmp_path):
    manager = AppConfigManager(tmp_path / "config.json")

    with pytest.raises(ValueError):
        manager.add_interruption_category("External")
    with pytest.raises(ValueError):
        manager.add_interruption_reason("External", "Noise")
