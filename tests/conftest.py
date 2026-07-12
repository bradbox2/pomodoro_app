# Manual / GUI-driven scripts that live under tests/ but are not automated
# unit tests. They open windows or require a real display, so they are
# excluded from automated collection.
collect_ignore = [
    "test_ctk_basic.py",
    "test_dashboard.py",
    "test_dashboard_data.py",
    "test_summary.py",
    "test_all_time.py",
]
