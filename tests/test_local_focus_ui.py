import pytest

from ui_manager import parse_focus_estimate


@pytest.mark.parametrize("raw, expected", [("1", 1), ("4", 4), (" 12 ", 12), ("99", 99)])
def test_focus_estimate_accepts_the_local_one_to_ninety_nine_range(raw, expected):
    assert parse_focus_estimate(raw) == expected


@pytest.mark.parametrize("raw", ["", "zero", "0", "100"])
def test_focus_estimate_rejects_values_outside_the_local_range(raw):
    with pytest.raises(ValueError, match="between 1 and 99"):
        parse_focus_estimate(raw)
