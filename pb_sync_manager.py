# pb_sync_manager.py
# PocketBase sync manager for FocusFlow pomodoro app.
# Replaces the old SyncManager (PocketBase at 38.244.21.35) with the new
# instance on the OpenClaw server, accessed via SSH tunnel.
#
# Architecture:
#   Local SQLite (offline-first SSOT) → sync → PocketBase on OpenClaw server
#   PocketBase webhook → openclaw message send → Feishu reward
#
# Access: PocketBase listens on 127.0.0.1:8090 on the server (not public).
#         Local clients connect via SSH tunnel:
#           ssh -i <key> -N -L 8090:127.0.0.1:8090 ubuntu@106.53.153.227
#         The tunnel manager below handles this automatically.

import subprocess
import threading
import time
import os
import sqlite3
import json
import logging
import uuid
from datetime import datetime, date
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass  # python-dotenv not installed; rely on environment variables

try:
    import requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

logger = logging.getLogger(__name__)

# ── Config (loaded from .env or environment variables) ───────────────────────

# SSH connection uses the "openclaw" alias defined in ~/.ssh/config.
# No key path needed here — identity and host are managed centrally in SSH config.
SSH_HOST = os.environ.get("PB_SSH_HOST", "openclaw")
PB_REMOTE_ADDR  = "127.0.0.1:8090"
PB_LOCAL_PORT   = 18090          # local tunnel port (avoid collision with any local 8090)
PB_URL          = f"http://127.0.0.1:{PB_LOCAL_PORT}"
PB_API_TOKEN  = os.environ.get("PB_API_TOKEN", "")   # preferred: API token (no password needed)
PB_EMAIL      = os.environ.get("PB_EMAIL", "")        # fallback: password auth
PB_PASSWORD   = os.environ.get("PB_PASSWORD", "")
TASKS_REMOTE_ADDR = "127.0.0.1:18091"
TASKS_LOCAL_PORT  = 18091       # local tunnel port for the tasks HTTP server
TASKS_URL         = f"http://127.0.0.1:{TASKS_LOCAL_PORT}"
TUNNEL_RETRY_DELAY = 5
REQUEST_TIMEOUT    = 8


# ── SSH Tunnel Manager ───────────────────────────────────────────────────────

class SSHTunnelManager:
    """Opens and maintains an SSH tunnel to the PocketBase instance on the server."""

    def __init__(self):
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()

    def start(self) -> bool:
        """Start tunnel if not running. Returns True if tunnel is up."""
        with self._lock:
            if self._proc and self._proc.poll() is None:
                return True  # already running
            cmd = [
                "ssh", SSH_HOST,
                "-N",
                "-o", "ExitOnForwardFailure=yes",
                "-L", f"{PB_LOCAL_PORT}:{PB_REMOTE_ADDR}",
                "-L", f"{TASKS_LOCAL_PORT}:{TASKS_REMOTE_ADDR}",
            ]
            try:
                self._proc = subprocess.Popen(
                    cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                time.sleep(1.5)  # give tunnel time to establish
                return self._proc.poll() is None
            except Exception as e:
                logger.warning(f"SSH tunnel start failed: {e}")
                return False

    def stop(self):
        with self._lock:
            if self._proc:
                self._proc.terminate()
                self._proc = None


# ── PocketBase Client ────────────────────────────────────────────────────────

class PBClient:
    """Minimal PocketBase REST client with token caching."""

    def __init__(self):
        self._token: Optional[str] = None
        self._token_expiry: float = 0

    def _auth(self) -> Optional[str]:
        if not REQUESTS_OK:
            return None
        # API token preferred — works even when password auth is disabled
        if PB_API_TOKEN:
            return PB_API_TOKEN
        # Fallback: password-based auth (requires email/password auth enabled server-side)
        now = time.time()
        if self._token and now < self._token_expiry:
            return self._token
        if not PB_EMAIL or not PB_PASSWORD:
            logger.warning("PB auth: no PB_API_TOKEN and PB_EMAIL/PB_PASSWORD not set")
            return None
        try:
            r = requests.post(
                f"{PB_URL}/api/collections/_superusers/auth-with-password",
                json={"identity": PB_EMAIL, "password": PB_PASSWORD},
                timeout=REQUEST_TIMEOUT
            )
            if r.status_code == 200:
                self._token = r.json().get("token")
                self._token_expiry = now + 3600  # tokens valid ~1h
                return self._token
        except Exception as e:
            logger.warning(f"PB auth failed: {e}")
        return None

    def _headers(self) -> dict:
        token = self._auth()
        return {"Authorization": f"Bearer {token}"} if token else {}

    def create_record(self, collection: str, data: dict) -> Optional[dict]:
        try:
            r = requests.post(
                f"{PB_URL}/api/collections/{collection}/records",
                headers=self._headers(), json=data, timeout=REQUEST_TIMEOUT
            )
            if r.status_code in (200, 201):
                return r.json()
        except Exception as e:
            logger.warning(f"PB create_record({collection}) failed: {e}")
        return None

    def upsert_daily_stat(self, date_str: str, task_name: str,
                          task_id: str, kr_ref: str,
                          delta: int = 1, is_breakthrough: bool = False) -> bool:
        """Increment pomodoro count for a task on a given date."""
        try:
            # Find existing record
            filter_q = f'date="{date_str}" && task_name="{task_name}"'
            r = requests.get(
                f"{PB_URL}/api/collections/ff_daily_stats/records",
                headers=self._headers(),
                params={"filter": filter_q, "perPage": 1},
                timeout=REQUEST_TIMEOUT
            )
            if r.status_code != 200:
                return False
            items = r.json().get("items", [])
            if items:
                rec = items[0]
                rec_id = rec["id"]
                new_count = rec.get("pomodoros_done", 0) + delta
                patch = requests.patch(
                    f"{PB_URL}/api/collections/ff_daily_stats/records/{rec_id}",
                    headers=self._headers(),
                    json={"pomodoros_done": new_count},
                    timeout=REQUEST_TIMEOUT
                )
                return patch.status_code == 200
            else:
                # Create new
                self.create_record("ff_daily_stats", {
                    "date": date_str,
                    "task_name": task_name,
                    "task_id": task_id,
                    "kr_ref": kr_ref,
                    "pomodoros_done": delta,
                    "is_breakthrough": is_breakthrough,
                })
                return True
        except Exception as e:
            logger.warning(f"PB upsert_daily_stat failed: {e}")
        return False

    def get_today_stats(self) -> list[dict]:
        """Return today's pomodoro counts per task. Used for morning briefing."""
        today = date.today().strftime("%Y-%m-%d")
        try:
            r = requests.get(
                f"{PB_URL}/api/collections/ff_daily_stats/records",
                headers=self._headers(),
                params={"filter": f'date="{today}"', "perPage": 100},
                timeout=REQUEST_TIMEOUT
            )
            if r.status_code == 200:
                return r.json().get("items", [])
        except Exception as e:
            logger.warning(f"PB get_today_stats failed: {e}")
        return []

    def get_today_tasks(self) -> list[dict]:
        """Fetch today's active tasks from the WEEKLY_BRIDGE tasks server."""
        try:
            r = requests.get(
                f"{TASKS_URL}/focusflow/today-tasks",
                timeout=REQUEST_TIMEOUT
            )
            if r.status_code == 200:
                data = r.json()
                return data.get("tasks", [])
        except Exception as e:
            logger.warning(f"Tasks server get_today_tasks failed: {e}")
        return []


# ── Offline Queue ─────────────────────────────────────────────────────────────

class OfflineQueue:
    """
    Local SQLite queue for operations that failed due to network unavailability.
    On reconnect, flushes all pending ops to PocketBase.
    """

    def __init__(self, queue_db_path: str):
        self.db_path = queue_db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pending_syncs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    op_type TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
            """)

    def enqueue(self, op_type: str, payload: dict):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO pending_syncs (created_at, op_type, payload) VALUES (?, ?, ?)",
                (datetime.now().isoformat(), op_type, json.dumps(payload))
            )

    def flush(self, pb: PBClient) -> int:
        """Flush all pending ops. Returns number successfully synced."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id, op_type, payload FROM pending_syncs ORDER BY id"
            ).fetchall()
        synced = 0
        for row_id, op_type, payload_str in rows:
            payload = json.loads(payload_str)
            ok = False
            if op_type == "session":
                ok = pb.create_record("ff_sessions", payload) is not None
            elif op_type == "daily_stat":
                ok = pb.upsert_daily_stat(**payload)
            if ok:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("DELETE FROM pending_syncs WHERE id = ?", (row_id,))
                synced += 1
        return synced


# ── Main Sync Manager ─────────────────────────────────────────────────────────

class PBSyncManager:
    """
    Drop-in replacement for the old SyncManager.
    Call record_session() after each completed pomodoro.
    """

    def __init__(self, data_dir: str):
        self.tunnel = SSHTunnelManager()
        self.pb = PBClient()
        queue_path = os.path.join(data_dir, "pb_offline_queue.db")
        self.queue = OfflineQueue(queue_path)
        self._connected = False
        self._connect_bg()

    def _connect_bg(self):
        """Try to open tunnel in background thread; retry every 60s until connected."""
        threading.Thread(target=self._reconnect_loop, daemon=True).start()

    def _reconnect_loop(self):
        while not self._connected:
            self._try_connect()
            if not self._connected:
                time.sleep(60)

    def _try_connect(self):
        ok = self.tunnel.start()
        if ok:
            token = self.pb._auth()
            self._connected = token is not None
            if self._connected:
                flushed = self.queue.flush(self.pb)
                if flushed:
                    logger.info(f"PB: flushed {flushed} offline ops")
        else:
            self._connected = False
        logger.info(f"PB connection: {'OK' if self._connected else 'OFFLINE'}")

    def record_session(self, session_data: dict,
                       task_id: str = "", kr_ref: str = "",
                       is_breakthrough: bool = False):
        """
        Called after a Work session completes.
        session_data must contain: session_id, project_name, task_name,
        session_type, start_time, end_time, duration_minutes, status,
        focus_score, end_mood, interruption_reason
        """
        payload = {
            "local_id":            session_data.get("session_id", "") or str(uuid.uuid4()),
            "project_name":        session_data.get("project_name", ""),
            "task_name":           session_data.get("task_name", ""),
            "task_id":             task_id,
            "kr_ref":              kr_ref,
            "session_type":        session_data.get("session_type", "Work"),
            "start_time":          str(session_data.get("start_time", "")),
            "end_time":            str(session_data.get("end_time", "")),
            "duration_minutes":    session_data.get("duration_minutes", 25),
            "status":              session_data.get("status", "Completed"),
            "focus_score":         session_data.get("focus_score"),
            "end_mood":            session_data.get("end_mood"),
            "interruption_reason": session_data.get("interruption_reason"),
            "is_breakthrough":     is_breakthrough,
        }
        stat_payload = {
            "date_str":       date.today().strftime("%Y-%m-%d"),
            "task_name":      session_data.get("task_name", ""),
            "task_id":        task_id,
            "kr_ref":         kr_ref,
            "delta":          1,
            "is_breakthrough": is_breakthrough,
        }
        if self._connected:
            threading.Thread(
                target=self._sync_session,
                args=(payload, stat_payload),
                daemon=True
            ).start()
        else:
            self.queue.enqueue("session", payload)
            self.queue.enqueue("daily_stat", stat_payload)
            logger.info("PB offline: queued session for later sync")

    def _sync_session(self, session_payload: dict, stat_payload: dict):
        # upsert stat FIRST so the reward hook reads the updated count when it fires
        ok2 = self.pb.upsert_daily_stat(**stat_payload)
        ok1 = self.pb.create_record("ff_sessions", session_payload) is not None
        if not (ok1 and ok2):
            self.queue.enqueue("session", session_payload)
            self.queue.enqueue("daily_stat", stat_payload)
        logger.info(f"PB sync: session={'OK' if ok1 else 'FAIL'}, stat={'OK' if ok2 else 'FAIL'}")

    def get_today_stats(self) -> list[dict]:
        """Return today's per-task pomodoro counts for morning briefing."""
        if self._connected:
            return self.pb.get_today_stats()
        return []

    def get_today_tasks(self) -> list[dict]:
        """Return today's active tasks from WEEKLY_BRIDGE.md via the tasks HTTP server."""
        if self._connected:
            return self.pb.get_today_tasks()
        return []

    def stop(self):
        self.tunnel.stop()
