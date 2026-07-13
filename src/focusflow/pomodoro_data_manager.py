# pomodoro_data_manager.py
import sqlite3
import os
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
import pandas as pd

# Define the latest version of the database schema
LATEST_DB_VERSION = 8

class PomodoroDataManager:
    """
    Manages all database interactions for the Pomodoro application, 
    including projects, tasks, and sessions.
    """
    def __init__(self, data_dir: str, db_name: str):
        """
        Initializes the data manager, connects to the database, and handles migrations.
        
        Args:
            data_dir: Directory where the database file is stored.
            db_name: Name of the database file.
        """
        self.db_path = os.path.join(data_dir, db_name)
        self._create_connection()
        # Create tables first to ensure they exist before migration
        self._create_tables()
        # Run migration check on startup
        self._run_migrations()

    def _create_connection(self) -> None:
        """Establishes a connection to the SQLite database."""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.execute("PRAGMA foreign_keys = 1")
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            self.conn = None

    def _run_migrations(self) -> None:
        """Checks DB version and applies migrations safely and sequentially."""
        if not self.conn: return
        try:
            cursor = self.conn.cursor()
            cursor.execute('PRAGMA user_version')
            db_version = cursor.fetchone()[0]
            
            print(f"Current DB version: {db_version}, Target version: {LATEST_DB_VERSION}")

            if db_version < 2:
                print("Applying migration to version 2...")
                cursor.execute("PRAGMA table_info('sessions')")
                columns = [info[1] for info in cursor.fetchall()]
                if 'focus_score' not in columns: self.cursor.execute("ALTER TABLE sessions ADD COLUMN focus_score INTEGER")
                if 'end_mood' not in columns: self.cursor.execute("ALTER TABLE sessions ADD COLUMN end_mood TEXT")
                self.conn.execute('PRAGMA user_version = 2')
                self.conn.commit()
                db_version = 2
                print("Migration to version 2 successful.")

            if db_version < 3:
                print("Applying migration to version 3...")
                cursor.execute("PRAGMA table_info('sessions')")
                columns = [info[1] for info in cursor.fetchall()]
                if 'interruption_reason' not in columns: self.cursor.execute("ALTER TABLE sessions ADD COLUMN interruption_reason TEXT")
                self.conn.execute('PRAGMA user_version = 3')
                self.conn.commit()
                db_version = 3
                print("Migration to version 3 successful.")
            
            if db_version < 4:
                print("Applying migration to version 4...")
                cursor.execute("PRAGMA table_info('tasks')")
                columns = [info[1] for info in cursor.fetchall()]
                if 'sound_preference' not in columns:
                    self.cursor.execute("ALTER TABLE tasks ADD COLUMN sound_preference TEXT DEFAULT 'dida'")
                self.conn.execute('PRAGMA user_version = 4')
                self.conn.commit()
                db_version = 4
                print("Migration to version 4 successful.")

            if db_version < 5:
                self.conn.execute('PRAGMA user_version = 5')
                self.conn.commit()
                print("Migration to version 5 successful.")

            if db_version < 6:
                cursor.execute("PRAGMA table_info('focus_items')")
                columns = [info[1] for info in cursor.fetchall()]
                if 'source' not in columns:
                    self.cursor.execute("ALTER TABLE focus_items ADD COLUMN source TEXT NOT NULL DEFAULT 'local'")
                if 'context_label' not in columns:
                    self.cursor.execute("ALTER TABLE focus_items ADD COLUMN context_label TEXT")
                self.conn.execute('PRAGMA user_version = 6')
                self.conn.commit()
                print("Migration to version 6 successful.")

            if db_version < 7:
                self.cursor.execute("DROP INDEX IF EXISTS idx_focus_items_goalsifter_task_id")
                self.conn.execute('PRAGMA user_version = 7')
                self.conn.commit()
                print("Migration to version 7 successful.")

            if db_version < 8:
                cursor.execute("PRAGMA table_info('focus_outbox')")
                columns = [info[1] for info in cursor.fetchall()]
                if 'sync_state' not in columns:
                    self.cursor.execute(
                        "ALTER TABLE focus_outbox ADD COLUMN sync_state TEXT NOT NULL DEFAULT 'pending'"
                    )
                self.conn.execute('PRAGMA user_version = 8')
                self.conn.commit()
                print("Migration to version 8 successful.")

        except sqlite3.Error as e:
            print(f"Database migration failed: {e}")
            
    def _create_tables(self) -> None:
        """Creates the necessary tables if they do not already exist."""
        if not self.conn: return
        try:
            self.cursor.execute('CREATE TABLE IF NOT EXISTS projects (project_name TEXT PRIMARY KEY NOT NULL)')
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    task_name TEXT NOT NULL, project_name TEXT NOT NULL,
                    estimated_pomodoros INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'In Progress',
                    sound_preference TEXT DEFAULT 'dida',
                    PRIMARY KEY (task_name, project_name),
                    FOREIGN KEY (project_name) REFERENCES projects (project_name) ON DELETE CASCADE
                )
            ''')
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY, project_name TEXT NOT NULL, task_name TEXT NOT NULL,
                    session_type TEXT NOT NULL, start_time TEXT NOT NULL, end_time TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL, status TEXT NOT NULL, focus_score INTEGER,
                    end_mood TEXT, interruption_reason TEXT
                )
            ''')
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS focus_items (
                    local_id TEXT PRIMARY KEY,
                    project_name TEXT NOT NULL,
                    task_name TEXT NOT NULL,
                    goalsifter_task_id TEXT,
                    state TEXT NOT NULL DEFAULT 'draft',
                    source TEXT NOT NULL DEFAULT 'local',
                    context_label TEXT,
                    UNIQUE(project_name, task_name)
                )
            ''')
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS focus_outbox (
                    event_id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    sync_state TEXT NOT NULL DEFAULT 'pending'
                )
            ''')
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Table creation error: {e}")
            
    def record_session(self, session_data: Dict[str, Any]) -> str:
        """
        Records a completed or interrupted session to the database.
        
        Args:
            session_data: Dictionary containing session details.
        """
        session_data.setdefault('focus_score', None)
        session_data.setdefault('end_mood', None)
        session_data.setdefault('interruption_reason', None)
        try:
            sql = '''INSERT INTO sessions (
                        session_id, project_name, task_name, session_type, start_time, 
                        end_time, duration_minutes, status, focus_score, 
                        end_mood, interruption_reason
                     ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
            session_id = session_data.get('session_id') or str(uuid.uuid4())
            params = (
                session_id, session_data['project_name'], session_data['task_name'],
                session_data['session_type'], session_data['start_time'].strftime("%Y-%m-%d %H:%M:%S"),
                session_data['end_time'].strftime("%Y-%m-%d %H:%M:%S"), session_data['duration_minutes'],
                session_data['status'], session_data['focus_score'],
                session_data['end_mood'], session_data['interruption_reason']
            )
            self.cursor.execute(sql, params)
            self._queue_bound_completed_session(session_id, session_data)
            self.conn.commit()
            return session_id
            
        except sqlite3.OperationalError as e:
            if "has no column named" in str(e):
                self._run_migrations()
                self.cursor.execute(sql, params)
                self.conn.commit()
                return session_id
            else: raise e

    def _queue_bound_completed_session(self, session_id: str, session_data: Dict[str, Any]) -> None:
        if (
            session_data.get('session_type') != 'Work'
            or session_data.get('status') != 'Completed'
            or not session_data.get('device_id')
        ):
            return
        focus_item = self.ensure_focus_item(session_data['project_name'], session_data['task_name'])
        task_id = focus_item['goalsifter_task_id']
        if not task_id:
            return
        self.cursor.execute('''
            INSERT OR IGNORE INTO focus_outbox (
                event_id, device_id, task_id, started_at, ended_at,
                duration_minutes, status
            ) VALUES (?, ?, ?, ?, ?, ?, 'completed')
        ''', (
            session_id,
            session_data['device_id'],
            task_id,
            session_data['start_time'].isoformat(timespec='seconds'),
            session_data['end_time'].isoformat(timespec='seconds'),
            session_data['duration_minutes'],
        ))

    def ensure_focus_item(self, project_name: str, task_name: str) -> Dict[str, Any]:
        self.cursor.execute('''
            INSERT OR IGNORE INTO focus_items (local_id, project_name, task_name)
            VALUES (?, ?, ?)
        ''', (str(uuid.uuid4()), project_name, task_name))
        self.cursor.execute('''
            SELECT local_id, project_name, task_name, goalsifter_task_id, state
            FROM focus_items WHERE project_name = ? AND task_name = ?
        ''', (project_name, task_name))
        row = self.cursor.fetchone()
        return {
            'local_id': row[0], 'project_name': row[1], 'task_name': row[2],
            'goalsifter_task_id': row[3], 'state': row[4],
        }

    def upsert_goalsifter_focus_item(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Mirror a remote DW locally without treating its KR as a local project."""
        task_id = str(task['task_id'])
        title = str(task['task_name']).strip()
        estimate = int(task['pomo_estimate'])
        if not title or not 1 <= estimate <= 4:
            raise ValueError("GoalSifter task must have a title and estimate between 1 and 4")
        internal_project = f"__goalsifter__:{task_id}"
        context_label = task.get('kr_ref') or None
        self.add_project(internal_project)
        self.cursor.execute('''
            INSERT INTO tasks (project_name, task_name, estimated_pomodoros, status, sound_preference)
            VALUES (?, ?, ?, 'In Progress', 'dida')
            ON CONFLICT(project_name, task_name) DO UPDATE SET
                estimated_pomodoros = excluded.estimated_pomodoros,
                status = 'In Progress'
        ''', (internal_project, title, estimate))
        self.cursor.execute('''
            SELECT local_id FROM focus_items
            WHERE project_name = ? AND source = 'goalsifter'
        ''', (internal_project,))
        existing = self.cursor.fetchone()
        if existing:
            self.cursor.execute('''
                UPDATE focus_items SET task_name = ?, goalsifter_task_id = ?, state = 'bound',
                    context_label = ? WHERE local_id = ?
            ''', (title, task_id, context_label, existing[0]))
        else:
            self.cursor.execute('''
                INSERT INTO focus_items (
                    local_id, project_name, task_name, goalsifter_task_id, state, source, context_label
                ) VALUES (?, ?, ?, ?, 'bound', 'goalsifter', ?)
            ''', (str(uuid.uuid4()), internal_project, title, task_id, context_label))
        self.conn.commit()
        self.cursor.execute('''
            SELECT local_id, project_name, task_name, goalsifter_task_id, state, source, context_label
            FROM focus_items WHERE project_name = ? AND source = 'goalsifter'
        ''', (internal_project,))
        row = self.cursor.fetchone()
        return {
            'local_id': row[0], 'project_name': row[1], 'task_name': row[2],
            'goalsifter_task_id': row[3], 'state': row[4], 'source': row[5],
            'context_label': row[6],
        }

    def bind_focus_item(self, local_id: str, goalsifter_task_id: str, device_id: str | None = None) -> None:
        self.cursor.execute('''
            UPDATE focus_items
            SET goalsifter_task_id = ?, state = 'bound'
            WHERE local_id = ?
        ''', (goalsifter_task_id, local_id))
        if device_id:
            self.cursor.execute('''
                INSERT OR IGNORE INTO focus_outbox (
                    event_id, device_id, task_id, started_at, ended_at,
                    duration_minutes, status
                )
                SELECT session_id, ?, ?, replace(start_time, ' ', 'T'), replace(end_time, ' ', 'T'),
                       duration_minutes, 'completed'
                FROM sessions
                WHERE project_name = (SELECT project_name FROM focus_items WHERE local_id = ?)
                  AND task_name = (SELECT task_name FROM focus_items WHERE local_id = ?)
                  AND session_type = 'Work' AND status = 'Completed'
            ''', (device_id, goalsifter_task_id, local_id, local_id))
        self.conn.commit()

    def get_pending_focusflow_events(self) -> List[Dict[str, Any]]:
        self.cursor.execute('''
            SELECT event_id, device_id, task_id, started_at, ended_at,
                   duration_minutes, status
            FROM focus_outbox WHERE sync_state = 'pending' ORDER BY rowid
        ''')
        return [
            {
                'event_id': row[0], 'device_id': row[1], 'task_id': row[2],
                'started_at': row[3], 'ended_at': row[4],
                'duration_minutes': row[5], 'status': row[6],
            }
            for row in self.cursor.fetchall()
        ]

    def mark_focusflow_event_synced(self, event_id: str) -> None:
        """Clear an event only after the server accepted it or confirmed a duplicate."""
        self.cursor.execute('DELETE FROM focus_outbox WHERE event_id = ?', (event_id,))
        self.conn.commit()

    def record_focusflow_event_error(self, event_id: str, error: str) -> None:
        """Keep a failed event retryable with a concise diagnostic for the user."""
        self.cursor.execute('''
            UPDATE focus_outbox SET attempts = attempts + 1, last_error = ?
            WHERE event_id = ?
        ''', (error[:500], event_id))
        self.conn.commit()

    def mark_focusflow_event_conflict(self, event_id: str, error: str) -> None:
        """Block a permanently conflicting event until the user resolves it."""
        self.cursor.execute('''
            UPDATE focus_outbox SET sync_state = 'blocked', last_error = ?
            WHERE event_id = ?
        ''', (error[:500], event_id))
        self.conn.commit()

    def get_blocked_focusflow_events(self) -> List[Dict[str, Any]]:
        self.cursor.execute('''
            SELECT event_id, device_id, task_id, started_at, ended_at,
                   duration_minutes, status, attempts, last_error
            FROM focus_outbox WHERE sync_state = 'blocked' ORDER BY rowid
        ''')
        columns = [column[0] for column in self.cursor.description]
        return [dict(zip(columns, row)) for row in self.cursor.fetchall()]

    def get_local_focus_items(self) -> List[Dict[str, Any]]:
        """Return active local tasks as offline-first focus-item cards."""
        self.cursor.execute('''
            INSERT OR IGNORE INTO focus_items (local_id, project_name, task_name)
            SELECT lower(hex(randomblob(16))), task.project_name, task.task_name
            FROM tasks AS task
            WHERE task.status = 'In Progress'
              AND task.project_name NOT GLOB '__goalsifter__:*'
        ''')
        self.conn.commit()
        self.cursor.execute('''
            SELECT focus.local_id, focus.project_name, focus.task_name,
                   task.estimated_pomodoros, focus.state,
                   COUNT(session.session_id) AS completed_count
            FROM focus_items AS focus
            JOIN tasks AS task
              ON task.project_name = focus.project_name AND task.task_name = focus.task_name
            LEFT JOIN sessions AS session
              ON session.project_name = focus.project_name
             AND session.task_name = focus.task_name
             AND session.session_type = 'Work'
             AND session.status = 'Completed'
            WHERE task.status = 'In Progress' AND focus.source = 'local' AND focus.state != 'archived'
            GROUP BY focus.local_id, focus.project_name, focus.task_name,
                     task.estimated_pomodoros, focus.state
            ORDER BY focus.project_name, focus.task_name
        ''')
        return [
            {
                'local_id': row[0], 'project_name': row[1], 'task_name': row[2],
                'estimate': row[3], 'state': row[4], 'completed_count': row[5],
            }
            for row in self.cursor.fetchall()
        ]

    def archive_local_focus_item(self, project_name: str, task_name: str) -> None:
        self.cursor.execute('''
            UPDATE focus_items SET state = 'archived'
            WHERE project_name = ? AND task_name = ? AND source = 'local'
        ''', (project_name, task_name))
        self.conn.commit()

    def restore_local_focus_item(self, project_name: str, task_name: str) -> None:
        self.cursor.execute('''
            UPDATE focus_items SET state = 'draft'
            WHERE project_name = ? AND task_name = ? AND source = 'local'
        ''', (project_name, task_name))
        self.conn.commit()

    def get_archived_local_focus_items(self) -> List[Dict[str, Any]]:
        self.cursor.execute('''
            SELECT focus.local_id, focus.project_name, focus.task_name, task.estimated_pomodoros
            FROM focus_items AS focus JOIN tasks AS task
              ON task.project_name = focus.project_name AND task.task_name = focus.task_name
            WHERE focus.source = 'local' AND focus.state = 'archived'
            ORDER BY focus.project_name, focus.task_name
        ''')
        return [
            {'local_id': row[0], 'project_name': row[1], 'task_name': row[2], 'estimate': row[3]}
            for row in self.cursor.fetchall()
        ]

    def get_goalsifter_focus_items(self) -> List[Dict[str, Any]]:
        """Return locally mirrored GoalSifter DWs with their read-only KR context."""
        self.cursor.execute('''
            SELECT focus.local_id, focus.project_name, focus.task_name,
                   task.estimated_pomodoros, focus.state, focus.source,
                   focus.context_label, focus.goalsifter_task_id,
                   COUNT(session.session_id) AS completed_count
            FROM focus_items AS focus
            JOIN tasks AS task
              ON task.project_name = focus.project_name AND task.task_name = focus.task_name
            LEFT JOIN sessions AS session
              ON session.project_name = focus.project_name
             AND session.task_name = focus.task_name
             AND session.session_type = 'Work' AND session.status = 'Completed'
            WHERE focus.source = 'goalsifter' AND focus.state != 'archived'
            GROUP BY focus.local_id, focus.project_name, focus.task_name,
                     task.estimated_pomodoros, focus.state, focus.source,
                     focus.context_label, focus.goalsifter_task_id
            ORDER BY focus.context_label, focus.task_name
        ''')
        return [
            {
                'local_id': row[0], 'project_name': row[1], 'task_name': row[2],
                'estimate': row[3], 'state': row[4], 'source': row[5],
                'context_label': row[6], 'goalsifter_task_id': row[7],
                'completed_count': row[8],
            }
            for row in self.cursor.fetchall()
        ]

    def reconcile_goalsifter_focus_items(self, active_task_ids: set[str]) -> None:
        """Archive remote mirrors absent from the latest active-task snapshot."""
        self.cursor.execute('''
            UPDATE focus_items
            SET state = 'archived'
            WHERE source = 'goalsifter'
              AND goalsifter_task_id NOT IN ({})
        '''.format(','.join('?' for _ in active_task_ids) or "NULL"), tuple(active_task_ids))
        self.conn.commit()

    def merge_from(self, source_db_path: str) -> None:
        """
        Merges data from a source database using a 'Last-Write-Wins' strategy for conflicting tasks.
        
        Args:
            source_db_path: Path to the database file to merge from.
        """
        try:
            # Attach the source database
            self.cursor.execute(f"ATTACH DATABASE '{source_db_path}' AS source_db")
            print("Successfully attached both databases.")

            # 1. Merge 'projects' - Simple insert, no conflicts on other data
            self.cursor.execute("INSERT OR IGNORE INTO main.projects (project_name) SELECT project_name FROM source_db.projects")
            self.conn.commit()

            # 2. Merge 'sessions' - Simple insert, session_id is unique
            self.cursor.execute("""
                INSERT OR IGNORE INTO main.sessions (
                    session_id, project_name, task_name, session_type, start_time,
                    end_time, duration_minutes, status, focus_score, end_mood,
                    interruption_reason
                )
                SELECT 
                    session_id, project_name, task_name, session_type, start_time,
                    end_time, duration_minutes, status, focus_score, end_mood,
                    interruption_reason
                FROM source_db.sessions
            """)
            self.conn.commit()

            # 3. Merge 'tasks' - This is the complex part with conflict resolution
            print("Starting task merge with 'Last-Write-Wins' strategy...")
            
            source_cursor = self.conn.cursor()
            source_cursor.execute("SELECT project_name, task_name, estimated_pomodoros, status, sound_preference FROM source_db.tasks")
            source_tasks = source_cursor.fetchall()
            
            for p_name, t_name, est, status, sound in source_tasks:
                self.cursor.execute("SELECT 1 FROM main.tasks WHERE project_name = ? AND task_name = ?", (p_name, t_name))
                exists = self.cursor.fetchone()

                if not exists:
                    self.cursor.execute("INSERT INTO main.tasks VALUES (?, ?, ?, ?, ?)", (t_name, p_name, est, status, sound))
                else:
                    # Conflict detected, find which one is newer
                    self.cursor.execute("SELECT MAX(end_time) FROM main.sessions WHERE project_name = ? AND task_name = ?", (p_name, t_name))
                    master_time = self.cursor.fetchone()[0] or '1970-01-01'
                    
                    source_cursor.execute("SELECT MAX(end_time) FROM source_db.sessions WHERE project_name = ? AND task_name = ?", (p_name, t_name))
                    source_time = source_cursor.fetchone()[0] or '1970-01-01'
                    
                    if source_time > master_time:
                        self.cursor.execute("UPDATE main.tasks SET estimated_pomodoros=?, status=?, sound_preference=? WHERE project_name=? AND task_name=?", 
                                            (est, status, sound, p_name, t_name))

            self.conn.commit()
            self.cursor.execute("DETACH DATABASE 'source_db'")
            print("Merge successful.")
        except sqlite3.Error as e:
            print(f"Error during database merge: {e}")
            self.conn.rollback() # Rollback changes on error
            raise
    
    def verify_db_schema(self, db_path_to_verify: str) -> bool:
        """
        Verifies if a database file has the expected schema.
        
        Args:
            db_path_to_verify: Path to the database file to verify.
        
        Returns:
            True if schema is valid, False otherwise.
        """
        expected_schema = {
            'projects': ['project_name'],
            'tasks': ['task_name', 'project_name', 'estimated_pomodoros', 'status', 'sound_preference'],
            'sessions': ['session_id', 'project_name', 'task_name', 'session_type', 'start_time', 'end_time', 'duration_minutes', 'status', 'focus_score', 'end_mood', 'interruption_reason']
        }
        try:
            conn = sqlite3.connect(db_path_to_verify)
            cursor = conn.cursor()
            for table, columns in expected_schema.items():
                cursor.execute(f"PRAGMA table_info('{table}')")
                existing_columns = [row[1] for row in cursor.fetchall()]
                if not all(col in existing_columns for col in columns):
                    conn.close()
                    return False
            conn.close()
            return True
        except Exception as e:
            print(f"DB verification failed: {e}")
            return False

    def get_db_last_modified_time(self) -> str:
        """Returns the last modified time of the database file as a string."""
        try:
            mtime = os.path.getmtime(self.db_path)
            return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return "N/A"

    def get_recent_tasks_with_projects(self, limit: int = 3) -> List[Dict[str, str]]:
        """
        Gets the most recently used tasks.
        
        Args:
            limit: Maximum number of tasks to return.
            
        Returns:
            List of dictionaries containing project and task names.
        """
        if not self.conn: return []
        try:
            self.cursor.execute('''
                SELECT project_name, task_name FROM (
                    SELECT project_name, task_name, MAX(start_time) as last_used
                    FROM sessions WHERE session_type = 'Work'
                    GROUP BY project_name, task_name
                ) ORDER BY last_used DESC LIMIT ?
            ''', (limit,))
            return [{"project": row[0], "task": row[1]} for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error fetching recent tasks: {e}")
            return []

    def get_last_feedback_for_task(self, project_name: str, task_name: str) -> Optional[Dict[str, Any]]:
        """Gets the feedback from the most recent session for a specific task."""
        if not all([self.conn, project_name, task_name]): return None
        try:
            self.cursor.execute('''
                SELECT focus_score, end_mood FROM sessions 
                WHERE project_name = ? AND task_name = ? AND focus_score IS NOT NULL
                ORDER BY end_time DESC LIMIT 1
            ''', (project_name, task_name))
            result = self.cursor.fetchone()
            return {"focus_score": result[0], "end_mood": result[1]} if result else None
        except sqlite3.Error as e:
            print(f"Error getting last feedback: {e}")
            return None

    def add_project(self, project_name: str) -> None:
        """Adds a new project to the database."""
        if not self.conn or not project_name: return
        try:
            self.cursor.execute('INSERT OR IGNORE INTO projects (project_name) VALUES (?)', (project_name,))
            self.conn.commit()
            
        except sqlite3.Error as e:
            print(f"Error adding project: {e}")

    def get_all_projects(self) -> List[str]:
        """Returns a list of all project names."""
        if not self.conn: return []
        try:
            self.cursor.execute('SELECT project_name FROM projects ORDER BY project_name')
            return [row[0] for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error getting projects: {e}")
            return []

    def rename_local_project(self, old_name: str, new_name: str) -> None:
        """Rename a local project while preserving all dependent local records."""
        self.cursor.execute('SELECT 1 FROM projects WHERE project_name = ?', (new_name.strip(),))
        if self.cursor.fetchone():
            raise ValueError("Target project already exists; use Merge instead")
        self.merge_local_projects([old_name], new_name)

    def get_local_project_names(self) -> List[str]:
        return [row['project_name'] for row in self.get_local_project_summaries()]

    def merge_local_projects(self, source_names: List[str], target_name: str) -> None:
        """Merge local projects transactionally; duplicate task names must be resolved first."""
        target_name = target_name.strip()
        sources = list(dict.fromkeys(name.strip() for name in source_names if name.strip()))
        sources = [name for name in sources if name != target_name]
        if not target_name or not sources:
            raise ValueError("Source projects and a distinct target project are required")
        if target_name.startswith("__goalsifter__:") or any(name.startswith("__goalsifter__:") for name in sources):
            raise ValueError("GoalSifter mirror projects cannot be managed locally")

        names = sources + [target_name]
        placeholders = ",".join("?" for _ in names)
        self.cursor.execute(f'''
            SELECT task_name FROM tasks
            WHERE project_name IN ({placeholders})
            GROUP BY task_name HAVING COUNT(*) > 1
            ORDER BY task_name
        ''', names)
        conflicts = [row[0] for row in self.cursor.fetchall()]
        if conflicts:
            raise ValueError("Conflicting task names: " + ", ".join(conflicts))

        with self.conn:
            self.conn.execute('INSERT OR IGNORE INTO projects (project_name) VALUES (?)', (target_name,))
            for source in sources:
                self.conn.execute('UPDATE tasks SET project_name = ? WHERE project_name = ?', (target_name, source))
                self.conn.execute('UPDATE sessions SET project_name = ? WHERE project_name = ?', (target_name, source))
                self.conn.execute('UPDATE focus_items SET project_name = ? WHERE project_name = ?', (target_name, source))
                self.conn.execute('DELETE FROM projects WHERE project_name = ?', (source,))

    def get_local_project_summaries(self) -> List[Dict[str, Any]]:
        """Return local-only project counts for the management window."""
        self.cursor.execute('''
            SELECT project.project_name,
                   COUNT(task.task_name) AS task_count,
                   SUM(CASE WHEN focus.state = 'archived' THEN 1 ELSE 0 END) AS archived_count
            FROM projects AS project
            LEFT JOIN tasks AS task ON task.project_name = project.project_name
            LEFT JOIN focus_items AS focus
              ON focus.project_name = task.project_name AND focus.task_name = task.task_name
             AND focus.source = 'local'
            WHERE project.project_name NOT GLOB '__goalsifter__:*'
            GROUP BY project.project_name ORDER BY project.project_name
        ''')
        return [
            {'project_name': row[0], 'task_count': row[1], 'archived_count': row[2] or 0}
            for row in self.cursor.fetchall()
        ]

    def delete_empty_local_project(self, project_name: str) -> None:
        if project_name.startswith("__goalsifter__:"):
            raise ValueError("GoalSifter mirror projects cannot be managed locally")
        self.cursor.execute('SELECT COUNT(*) FROM tasks WHERE project_name = ?', (project_name,))
        if self.cursor.fetchone()[0]:
            raise ValueError("Project contains tasks; merge or archive them first")
        self.cursor.execute('DELETE FROM projects WHERE project_name = ?', (project_name,))
        self.conn.commit()

    def add_or_update_task(self, project_name: str, task_name: str, estimate: int, sound_preference: str = 'dida') -> None:
        """Adds a new task or updates an existing one."""
        if not all([self.conn, project_name, task_name]): return
        if not 1 <= estimate <= 99:
            raise ValueError("Focus item estimate must be between 1 and 99")
        self.add_project(project_name)
        try:
            self.cursor.execute('''
                INSERT INTO tasks (project_name, task_name, estimated_pomodoros, status, sound_preference) 
                VALUES (?, ?, ?, 'In Progress', ?)
                ON CONFLICT(project_name, task_name) DO UPDATE SET 
                    estimated_pomodoros=excluded.estimated_pomodoros,
                    status='In Progress',
                    sound_preference=excluded.sound_preference
            ''', (project_name, task_name, estimate, sound_preference))
            self.ensure_focus_item(project_name, task_name)
            self.conn.commit()
            
        except sqlite3.Error as e:
            print(f"Error adding/updating task: {e}")

    def mark_task_as_complete(self, project_name: str, task_name: str) -> None:
        """Marks a task as completed."""
        if not all([self.conn, project_name, task_name]): return
        try:
            self.cursor.execute("UPDATE tasks SET status = 'Completed' WHERE project_name = ? AND task_name = ?", (project_name, task_name))
            self.conn.commit()
            
        except sqlite3.Error as e:
            print(f"Error marking task as complete: {e}")

    def delete_project(self, project_name: str) -> None:
        """Deletes a project and all its associated tasks (CASCADE)."""
        if not all([self.conn, project_name]): return
        try:
            # Ensure foreign keys are on for CASCADE to work
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.cursor.execute("DELETE FROM projects WHERE project_name = ?", (project_name,))
            self.conn.commit()
            
        except sqlite3.Error as e:
            print(f"Error deleting project: {e}")

    def delete_task(self, project_name: str, task_name: str) -> None:
        """Deletes a specific task."""
        if not all([self.conn, project_name, task_name]): return
        try:
            self.cursor.execute("DELETE FROM tasks WHERE project_name = ? AND task_name = ?", (project_name, task_name))
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error deleting task: {e}")

    def get_tasks_for_project(self, project_name: str, include_completed: bool = False) -> List[str]:
        """Returns a list of tasks for a given project."""
        if not self.conn or not project_name: return []
        try:
            query = 'SELECT task_name FROM tasks WHERE project_name = ?'
            if not include_completed:
                query += " AND status = 'In Progress'"
            query += ' ORDER BY task_name'
            self.cursor.execute(query, (project_name,))
            return [row[0] for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error getting tasks for project: {e}")
            return []

    def get_tasks_with_stats(self, project_name: str, include_completed: bool = False) -> List[Dict[str, Any]]:
        """Returns a list of tasks with their completed session counts."""
        if not self.conn or not project_name: return []
        try:
            # Get tasks
            query = "SELECT task_name FROM tasks WHERE project_name = ?"
            if not include_completed:
                query += " AND status = 'In Progress'"
            query += " ORDER BY task_name"
            
            self.cursor.execute(query, (project_name,))
            tasks = [row[0] for row in self.cursor.fetchall()]
            
            result = []
            for task in tasks:
                 # Count completed WORK sessions for each task
                 count = self.get_completed_work_sessions_for_task(project_name, task)
                 result.append({'name': task, 'count': count})
            return result
        except sqlite3.Error as e:
            print(f"Error getting tasks with stats: {e}")
            return []
            
    def get_task_details(self, project_name: str, task_name: str) -> Optional[Dict[str, Any]]:
        """Returns details for a specific task."""
        if not all([self.conn, project_name, task_name]): return None
        try:
            self.cursor.execute('SELECT estimated_pomodoros, status, sound_preference FROM tasks WHERE project_name = ? AND task_name = ?', (project_name, task_name))
            result = self.cursor.fetchone()
            return {"estimate": result[0], "status": result[1], "sound": result[2]} if result else None
        except sqlite3.Error as e:
            print(f"Error getting task details: {e}")
            return None

    def get_completed_work_sessions_for_task(self, project_name: str, task_name: str) -> int:
        """Returns the count of completed work sessions for a specific task."""
        if not all([self.conn, project_name, task_name]): return 0
        try:
            self.cursor.execute("SELECT COUNT(*) FROM sessions WHERE project_name = ? AND task_name = ? AND session_type = 'Work' AND status = 'Completed'", (project_name, task_name))
            return self.cursor.fetchone()[0]
        except sqlite3.Error as e:
            print(f"Error fetching sessions: {e}")
            return 0
            
    def get_total_completed_work_sessions_today(self) -> int:
        """Returns the total number of work sessions completed today across all tasks."""
        if not self.conn: return 0
        today_str = datetime.now().strftime("%Y-%m-%d")
        try:
            self.cursor.execute("SELECT COUNT(*) FROM sessions WHERE session_type = 'Work' AND status = 'Completed' AND DATE(start_time) = ?", (today_str,))
            return self.cursor.fetchone()[0]
        except sqlite3.Error as e:
            print(f"Error fetching total today's sessions: {e}")
            return 0

    def get_all_sessions_for_analysis(self) -> pd.DataFrame:
        """Returns all session data in a Pandas DataFrame for analysis."""
        if not self.conn: return pd.DataFrame()
        try:
            return pd.read_sql_query("SELECT * FROM sessions", self.conn)
        except Exception:
            try:
                return pd.read_sql_query("SELECT session_id, project_name, task_name, session_type, start_time, end_time, duration_minutes, status FROM sessions", self.conn)
            except:
                return pd.DataFrame()

    def close(self) -> None:
        """Closes the database connection."""
        if self.conn: self.conn.close()
