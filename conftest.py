from pathlib import Path


MANUAL_TESTS = {
    "test_all_time.py",
    "test_ctk_basic.py",
    "test_dashboard.py",
    "test_dashboard_data.py",
    "test_summary.py",
    "test_sync_manual.py",
}


def pytest_ignore_collect(collection_path: Path, config) -> bool:
    return collection_path.name in MANUAL_TESTS
