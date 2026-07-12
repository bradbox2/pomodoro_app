"""Per-device GoalSifter connection settings stored with local user data."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass

from focusflow.app_paths import AppPaths


@dataclass
class GoalSifterSettings:
    device_id: str
    ssh_host_alias: str = ""
    local_port: int = 18000
    bearer_token: str = ""
    auto_connect: bool = False

    @property
    def is_configured(self) -> bool:
        return bool(self.ssh_host_alias.strip() and self.bearer_token.strip())

    def update_connection(
        self,
        paths: AppPaths,
        *,
        ssh_host_alias: str,
        bearer_token: str,
        local_port: int,
        auto_connect: bool,
    ) -> None:
        """Apply user-entered connection settings and persist them."""
        self.ssh_host_alias = ssh_host_alias.strip()
        self.bearer_token = bearer_token.strip()
        self.local_port = int(local_port)
        self.auto_connect = bool(auto_connect)
        self.save(paths)

    @classmethod
    def load(cls, paths: AppPaths) -> "GoalSifterSettings":
        paths.ensure_ready()
        try:
            data = json.loads(paths.goalsifter_settings_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            settings = cls(device_id=str(uuid.uuid4()))
            settings.save(paths)
            return settings

        settings = cls(
            device_id=str(data.get("device_id") or uuid.uuid4()),
            ssh_host_alias=str(data.get("ssh_host_alias", "")),
            local_port=int(data.get("local_port", 18000)),
            bearer_token=str(data.get("bearer_token", "")),
            auto_connect=bool(data.get("auto_connect", False)),
        )
        if data.get("device_id") != settings.device_id:
            settings.save(paths)
        return settings

    def save(self, paths: AppPaths) -> None:
        paths.ensure_ready()
        paths.goalsifter_settings_path.write_text(
            json.dumps(asdict(self), indent=2), encoding="utf-8"
        )
