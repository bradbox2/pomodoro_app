"""
Test script to verify UI configuration changes
"""
import sys
sys.path.insert(0, 'd:/Python311_Project/pomodoro_app')

from config import *

def test_window_size():
    """Verify window size is correctly updated"""
    expected = "360x580"
    actual = WINDOW_GEOMETRY
    assert actual == expected, f"Expected {expected}, got {actual}"
    print(f"✓ Window size test passed: {actual}")

def test_color_constants():
    """Verify new color constants are defined"""
    assert CARD_BG_COLOR == "#2C5F6F", f"CARD_BG_COLOR incorrect: {CARD_BG_COLOR}"
    assert ACCENT_COLOR == "#F4A261", f"ACCENT_COLOR incorrect: {ACCENT_COLOR}"
    assert SUCCESS_COLOR == "#52B788", f"SUCCESS_COLOR incorrect: {SUCCESS_COLOR}"
    assert BUTTON_HOVER == "#21867A", f"BUTTON_HOVER incorrect: {BUTTON_HOVER}"
    print("✓ Color scheme test passed")
    print(f"  - CARD_BG_COLOR: {CARD_BG_COLOR}")
    print(f"  - ACCENT_COLOR: {ACCENT_COLOR}")
    print(f"  - SUCCESS_COLOR: {SUCCESS_COLOR}")
    print(f"  - BUTTON_HOVER: {BUTTON_HOVER}")

def test_spacing_constants():
    """Verify spacing constants are defined"""
    assert PADDING_SMALL == 5, f"PADDING_SMALL incorrect: {PADDING_SMALL}"
    assert PADDING_MEDIUM == 10, f"PADDING_MEDIUM incorrect: {PADDING_MEDIUM}"
    assert PADDING_LARGE == 15, f"PADDING_LARGE incorrect: {PADDING_LARGE}"
    assert PADDING_XLARGE == 20, f"PADDING_XLARGE incorrect: {PADDING_XLARGE}"
    print("✓ Spacing constants test passed")
    print(f"  - PADDING_SMALL: {PADDING_SMALL}")
    print(f"  - PADDING_MEDIUM: {PADDING_MEDIUM}")
    print(f"  - PADDING_LARGE: {PADDING_LARGE}")
    print(f"  - PADDING_XLARGE: {PADDING_XLARGE}")

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
