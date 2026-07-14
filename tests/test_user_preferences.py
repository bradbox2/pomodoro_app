import json

import pytest

from focusflow.app_config_manager import AppConfigManager
from focusflow.main import PomodoroApp


def _manager(tmp_path):
    return AppConfigManager(tmp_path / "config.json")


def test_missing_preferences_use_timer_window_and_display_defaults(tmp_path):
    manager = _manager(tmp_path)

    preferences = manager.get_preferences()

    assert preferences == {
        "work_minutes": 25,
        "short_break_minutes": 5,
        "long_break_minutes": 15,
        "long_break_interval": 4,
        "reset_long_break_on_restart": True,
        "feedback_interval": 3,
        "always_on_top": True,
        "focused_transparency": 0.8,
        "theme_mode": "dark",
        "enable_animations": True,
        "font_size_scale": 1.0,
    }
    saved = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert saved["preferences"] == preferences


def test_preferences_update_is_partial_and_persisted(tmp_path):
    manager = _manager(tmp_path)

    updated = manager.update_preferences({"work_minutes": 25, "theme_mode": "light"})
    reloaded = AppConfigManager(tmp_path / "config.json")

    assert updated["work_minutes"] == 25
    assert updated["short_break_minutes"] == 5
    assert updated["theme_mode"] == "light"
    assert reloaded.get_preferences() == updated


@pytest.mark.parametrize("key,value", [
    ("work_minutes", 0),
    ("short_break_minutes", 61),
    ("long_break_minutes", 121),
    ("long_break_interval", 0),
    ("feedback_interval", 21),
    ("focused_transparency", 0.49),
    ("font_size_scale", 1.51),
    ("theme_mode", "blue"),
])
def test_preferences_reject_values_outside_user_ranges(tmp_path, key, value):
    manager = _manager(tmp_path)

    with pytest.raises(ValueError):
        manager.update_preferences({key: value})


def test_old_config_without_preferences_is_upgraded_without_losing_custom_sections(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"interruptions": {"Custom": [{"name": "Door"}]}}), encoding="utf-8")

    manager = AppConfigManager(config_path)

    assert "Custom" in manager.get_interruption_reasons()
    assert manager.get_preferences()["theme_mode"] == "dark"
    saved = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved["preferences"]["work_minutes"] == 25


def test_invalid_config_root_falls_back_to_defaults_instead_of_crashing(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")

    manager = AppConfigManager(config_path)

    assert manager.get_preferences()["work_minutes"] == 25


def test_apply_preferences_updates_runtime_without_resetting_current_timer(monkeypatch):
    app = PomodoroApp.__new__(PomodoroApp)
    app.preferences = dict(AppConfigManager.DEFAULT_PREFERENCES)
    app.is_running = True
    app.config_manager = type("Config", (), {
        "update_preferences": lambda _self, updates: {**app.preferences, **updates},
    })()
    app.timer = type("Timer", (), {
        "settings": {"Work": 25, "Short Break": 5, "Long Break": 15},
    })()
    root_calls = []
    app.root = type("Root", (), {
        "attributes": lambda _self, *args: root_calls.append(args),
    })()
    ui_calls = []
    app.ui = type("UI", (), {
        "apply_display_preferences": lambda _self, prefs: ui_calls.append(prefs),
    })()
    theme_calls = []
    monkeypatch.setattr("focusflow.main.ThemeManager.set_mode", lambda mode: theme_calls.append(mode))

    result = app.apply_preferences({
        "work_minutes": 25,
        "theme_mode": "light",
        "focused_transparency": 0.7,
        "always_on_top": False,
    })

    assert result["work_minutes"] == 25
    assert app.timer.settings == {"Work": 25, "Short Break": 5, "Long Break": 15}
    assert app.is_running is True
    assert root_calls == [("-topmost", False), ("-alpha", 0.7)]
    assert theme_calls == ["light"]
    assert ui_calls[-1]["theme_mode"] == "light"
