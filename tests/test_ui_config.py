"""
Test script to verify UI configuration changes
"""
from focusflow.config import *
from focusflow.ui_manager import calculate_home_size
from focusflow.ui_manager import PygameTimerWidget, UIManager
import inspect
from pathlib import Path

def test_window_size():
    """Home and topmost timer use deliberately different window sizes."""
    assert HOME_WINDOW_GEOMETRY == "800x600"
    assert TIMER_WINDOW_GEOMETRY == "300x400"


def test_home_size_follows_content_without_exceeding_screen():
    assert calculate_home_size(430, 690, 1920, 1080) == (430, 690)
    assert calculate_home_size(2000, 1200, 1920, 1080) == (1728, 972)

def test_color_constants():
    """Verify new color constants are defined"""
    assert CARD_BG_COLOR == "#1F1F1F", f"CARD_BG_COLOR incorrect: {CARD_BG_COLOR}"
    assert ACCENT_COLOR == "#F4A261", f"ACCENT_COLOR incorrect: {ACCENT_COLOR}"
    assert SUCCESS_COLOR == "#52B788", f"SUCCESS_COLOR incorrect: {SUCCESS_COLOR}"
    assert BUTTON_HOVER == "#21867A", f"BUTTON_HOVER incorrect: {BUTTON_HOVER}"

def test_spacing_constants():
    """Verify spacing constants are defined"""
    assert PADDING_SMALL == 5, f"PADDING_SMALL incorrect: {PADDING_SMALL}"
    assert PADDING_MEDIUM == 10, f"PADDING_MEDIUM incorrect: {PADDING_MEDIUM}"
    assert PADDING_LARGE == 15, f"PADDING_LARGE incorrect: {PADDING_LARGE}"
    assert PADDING_XLARGE == 20, f"PADDING_XLARGE incorrect: {PADDING_XLARGE}"


def test_particle_widget_restores_full_effect_dimensions():
    signature = inspect.signature(PygameTimerWidget.__init__)
    assert signature.parameters["width"].default == 260
    assert signature.parameters["height"].default == 200
    source = Path(__file__).parents[1].joinpath("src", "focusflow", "ui_manager.py").read_text(encoding="utf-8")
    assert "PygameTimerWidget(pygame_container, width=260, height=200" in source


def test_settings_window_exposes_session_feedback_tab():
    source = Path(__file__).parents[1].joinpath("src", "focusflow", "main.py").read_text(encoding="utf-8")
    assert 'feedback_tab = tabs.add("Session Feedback")' in source
    assert "add_feedback_mood" in source
    assert "update_feedback_mood" in source
    assert "delete_feedback_mood" in source


def test_task_source_actions_are_separated_from_remote_task_list():
    widget_source = inspect.getsource(UIManager._create_widgets)
    quick_start_source = inspect.getsource(UIManager.update_quick_start_buttons)
    remote_list_source = inspect.getsource(UIManager.refresh_goalsifter_focus_items)

    assert 'command=self._on_task_source_changed' in widget_source
    assert 'text="GoalSifter 操作:' in widget_source
    assert 'text="Quick Start:"' in quick_start_source
    assert 'text="刷新 GoalSifter 任务"' not in remote_list_source
    assert 'text="手动同步 Outbox"' not in remote_list_source
    assert 'text="⚙ 连接设置"' not in remote_list_source

if __name__ == "__main__":
    print("=" * 50)
    print("UI Configuration Tests")
    print("=" * 50)
    
    try:
        test_window_size()
        test_color_constants()
        test_spacing_constants()
        print("\n" + "=" * 50)
        print("All tests passed! ✓")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
