"""Client for the locked GoalSifter desktop API contract."""

from __future__ import annotations

import json
import socket
import subprocess
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from focusflow.goalsifter_settings import GoalSifterSettings


class GoalSifterRemoteError(RuntimeError):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class GoalSifterTask:
    task_id: str
    task_name: str
    kr_ref: str | None
    pomo_estimate: int
    pomo_count: int
    status: str
    created_at: str
    last_event_at: str | None


class GoalSifterClient:
    def __init__(self, settings: GoalSifterSettings, request: Callable | None = None):
        self.settings = settings
        self._request = request or self._url_request

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.settings.local_port}/api/v1/focusflow"

    def start_tunnel(self) -> subprocess.Popen:
        if not self.settings.is_configured:
            raise GoalSifterRemoteError(0, "GoalSifter SSH alias and Bearer token are required")
        return subprocess.Popen([
            "ssh", "-N", "-L",
            f"{self.settings.local_port}:127.0.0.1:8000",
            self.settings.ssh_host_alias,
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def is_tunnel_ready(self, timeout: float = 0.5) -> bool:
        """Cheap TCP probe: is the forwarded local port actually accepting connections yet?"""
        try:
            with socket.create_connection(("127.0.0.1", self.settings.local_port), timeout):
                return True
        except OSError:
            return False

    def get_active_dw_tasks(self) -> list[GoalSifterTask]:
        status, body = self._request("GET", f"{self.base_url}/tasks", self._headers())
        data = self._decode(status, body)
        # The deployed server returns the snapshot wrapped as {"tasks": [...]};
        # tolerate a bare list too (older responses / test fixtures).
        if isinstance(data, dict):
            data = data.get("tasks", [])
        if not isinstance(data, list):
            raise GoalSifterRemoteError(500, "GoalSifter task snapshot is not a list")
        return [GoalSifterTask(**task) for task in data]

    def post_pomo_event(self, event: dict[str, Any]) -> dict[str, Any]:
        status, body = self._request(
            "POST", f"{self.base_url}/pomo-events", self._headers(), json.dumps(event).encode()
        )
        return self._decode(status, body)

    def create_dw_task(self, name: str, pomo_estimate: int | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": name}
        if pomo_estimate is not None:
            payload["pomo_estimate"] = pomo_estimate
        status, body = self._request(
            "POST", f"{self.base_url}/tasks", self._headers(), json.dumps(payload).encode()
        )
        return self._decode(status, body)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.settings.bearer_token}"}

    @staticmethod
    def _decode(status: int, body: bytes) -> Any:
        try:
            data = json.loads(body.decode())
        except (UnicodeDecodeError, json.JSONDecodeError):
            data = {}
        if status >= 400:
            detail = data.get("detail") or data.get("error") or f"GoalSifter returned HTTP {status}"
            raise GoalSifterRemoteError(status, str(detail))
        return data

    @staticmethod
    def _url_request(method: str, url: str, headers: dict[str, str], body: bytes | None = None):
        request = Request(url, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=10) as response:
                return response.status, response.read()
        except HTTPError as error:
            return error.code, error.read()
        except URLError as error:
            raise GoalSifterRemoteError(0, f"GoalSifter tunnel unavailable: {error.reason}") from error
