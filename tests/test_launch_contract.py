from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_launchers_use_the_project_virtual_environment():
    for launcher_name in ("Pomodoro-start.bat", "Pomodoro.bat"):
        launcher = (PROJECT_ROOT / launcher_name).read_text(encoding="utf-8")
        assert ".venv\\Scripts\\pythonw.exe" in launcher
        assert "envipomo" not in launcher


def test_packaging_has_no_cloud_sync_dependencies():
    spec = (PROJECT_ROOT / "FocusFlow.spec").read_text(encoding="utf-8")
    requirements = (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8")

    assert "requests" not in spec
    assert "requests" not in requirements
    assert "dotenv" not in requirements
