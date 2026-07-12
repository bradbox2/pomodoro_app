"""Locations for mutable FocusFlow user state."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    """Separates immutable application files from per-user data."""

    install_dir: Path
    data_dir: Path

    @classmethod
    def from_environment(cls, install_dir: Path) -> "AppPaths":
        configured_root = os.environ.get("FOCUSFLOW_DATA_DIR")
        default_root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "FocusFlow"
        return cls(install_dir=Path(install_dir), data_dir=Path(configured_root) if configured_root else default_root)

    @property
    def config_path(self) -> Path:
        return self.data_dir / "config.json"

    @property
    def backup_dir(self) -> Path:
        return self.data_dir / "backup"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def exports_dir(self) -> Path:
        return self.data_dir / "exports"

    @property
    def goalsifter_settings_path(self) -> Path:
        return self.data_dir / "goalsifter_settings.json"

    def ensure_ready(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        for directory in (self.backup_dir, self.logs_dir, self.exports_dir):
            directory.mkdir(exist_ok=True)
        self.migrate_legacy_state()

    def migrate_legacy_state(self) -> None:
        """Copy legacy project-root data once, preserving existing user data."""
        legacy_data_dir = self.install_dir / "data"
        if legacy_data_dir.is_dir():
            for legacy_file in legacy_data_dir.iterdir():
                if legacy_file.is_file():
                    destination = self.data_dir / legacy_file.name
                    if not destination.exists():
                        shutil.copy2(legacy_file, destination)

        legacy_config = self.install_dir / "config.json"
        if legacy_config.is_file() and not self.config_path.exists():
            shutil.copy2(legacy_config, self.config_path)
