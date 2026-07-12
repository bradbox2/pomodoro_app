"""
Test script to verify UI configuration changes
"""
from config import *
from ui_manager import calculate_home_size

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
