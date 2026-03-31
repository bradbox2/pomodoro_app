#!/usr/bin/env python3
"""
migrate_projects.py
One-time migration: rename old project names to new OKR-aligned names.

Old → New mapping:
  Review and Outlook  → Q1·职业事业 ⚔️
  Marketing           → Q1·职业事业 ⚔️
  Python Learning     → Q4·智力技术 🧠
  Financial Growth    → Q2·财富投资 💰
  General Tasks       → 🗑️ 冷冻舱

Affects: projects, tasks, sessions tables.
Run once; safe to re-run (idempotent — old names no longer exist after first run).
"""

import sqlite3
import os
import sys
import io
import shutil
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "pomodoro_data.db")
BACKUP_PATH = DB_PATH + f".pre-migrate-{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"

MAPPING = {
    "Review and Outlook": "Q1·职业事业 ⚔️",
    "Marketing":          "Q1·职业事业 ⚔️",
    "Python Learning":    "Q4·智力技术 🧠",
    "Financial Growth":   "Q2·财富投资 💰",
    "General Tasks":      "🗑️ 冷冻舱",
}


def migrate():
    # Backup first
    shutil.copy2(DB_PATH, BACKUP_PATH)
    print(f"Backup created: {BACKUP_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    for old, new in MAPPING.items():
        # tasks
        cur.execute("UPDATE tasks SET project_name=? WHERE project_name=?", (new, old))
        tasks_changed = cur.rowcount
        # sessions
        cur.execute("UPDATE sessions SET project_name=? WHERE project_name=?", (new, old))
        sessions_changed = cur.rowcount
        # projects table
        cur.execute("DELETE FROM projects WHERE project_name=?", (old,))
        # Ensure new project exists in projects table
        cur.execute("INSERT OR IGNORE INTO projects (project_name) VALUES (?)", (new,))

        if tasks_changed or sessions_changed:
            print(f"  '{old}' -> '{new}'  ({tasks_changed} tasks, {sessions_changed} sessions)")

    conn.commit()

    # Verify final state
    print("\nFinal project list:")
    for r in cur.execute("SELECT project_name FROM projects ORDER BY project_name"):
        tasks = cur.execute("SELECT COUNT(*) FROM tasks WHERE project_name=?", (r[0],)).fetchone()[0]
        sessions = cur.execute("SELECT COUNT(*) FROM sessions WHERE project_name=? AND session_type='Work' AND status='Completed'", (r[0],)).fetchone()[0]
        print(f"  {r[0]}  ({tasks} tasks, {sessions} completed Work sessions)")

    conn.close()
    print("\nMigration complete.")


if __name__ == "__main__":
    migrate()
