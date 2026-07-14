from pathlib import Path

from focusflow.app_paths import AppPaths
from focusflow.app_config_manager import AppConfigManager
from focusflow.analysis_manager import AnalysisManager


def test_environment_data_root_overrides_default(monkeypatch, tmp_path):
    data_root = tmp_path / "office-data"
    monkeypatch.setenv("FOCUSFLOW_DATA_DIR", str(data_root))

    paths = AppPaths.from_environment(tmp_path / "install")

    assert paths.data_dir == data_root
    assert paths.config_path == data_root / "config.json"
    assert paths.backup_dir == data_root / "backup"
    assert paths.logs_dir == data_root / "logs"
    assert paths.exports_dir == data_root / "exports"


def test_legacy_state_is_copied_once_without_overwriting_user_files(tmp_path):
    install_dir = tmp_path / "install"
    legacy_data = install_dir / "data"
    legacy_data.mkdir(parents=True)
    (legacy_data / "pomodoro_data.db").write_text("legacy-db", encoding="utf-8")
    (install_dir / "config.json").write_text('{"theme":"dark"}', encoding="utf-8")

    data_root = tmp_path / "user-data"
    paths = AppPaths(install_dir=install_dir, data_dir=data_root)
    paths.ensure_ready()

    assert (data_root / "pomodoro_data.db").read_text(encoding="utf-8") == "legacy-db"
    assert paths.config_path.read_text(encoding="utf-8") == '{"theme":"dark"}'

    paths.config_path.write_text('{"theme":"light"}', encoding="utf-8")
    paths.ensure_ready()

    assert paths.config_path.read_text(encoding="utf-8") == '{"theme":"light"}'


def test_configuration_and_exports_use_the_resolved_user_data_directory(tmp_path):
    paths = AppPaths(install_dir=tmp_path / "install", data_dir=tmp_path / "user-data")
    paths.ensure_ready()

    config_manager = AppConfigManager(paths.config_path)
    analysis_manager = AnalysisManager(data_manager=None, exports_dir=paths.exports_dir, config_path=paths.config_path)

    assert Path(config_manager.config_path) == paths.config_path
    assert Path(config_manager.history_manager.history_path).parent == paths.data_dir
    assert Path(analysis_manager.report_path).parent == paths.exports_dir
