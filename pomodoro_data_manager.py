# pomodoro_data_manager.py
import sqlite3
import os
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
import pandas as pd
from sync_manager import SyncManager

# Define the latest version of the database schema
LATEST_DB_VERSION = 4

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
                print("Migration to version 4 successful.")

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
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Table creation error: {e}")
            
    def record_session(self, session_data: Dict[str, Any]) -> None:
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
            params = (
                str(uuid.uuid4()), session_data['project_name'], session_data['task_name'],
                session_data['session_type'], session_data['start_time'].strftime("%Y-%m-%d %H:%M:%S"),
                session_data['end_time'].strftime("%Y-%m-%d %H:%M:%S"), session_data['duration_minutes'],
                session_data['status'], session_data['focus_score'],
                session_data['end_mood'], session_data['interruption_reason']
            )
            self.cursor.execute(sql, params)
            self.conn.commit()
            
            # Cloud Sync (Async)
            sync_payload = {
                "project_name": session_data['project_name'],
                "task_name": session_data['task_name'],
                "session_type": session_data['session_type'],
                "start_time": session_data['start_time'].strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": session_data['end_time'].strftime("%Y-%m-%d %H:%M:%S"),
                "duration_minutes": session_data['duration_minutes'],
                "status": session_data['status'],
                "focus_score": session_data.get('focus_score'),
                "end_mood": session_data.get('end_mood'),
                "interruption_reason": session_data.get('interruption_reason')
            }
            SyncManager.sync_data("sessions", sync_payload, record_id=params[0])
            
        except sqlite3.OperationalError as e:
            if "has no column named" in str(e):
                self._run_migrations()
                self.cursor.execute(sql, params)
                self.conn.commit()
            else: raise e

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

    def merge_from_cloud(self, cloud_data: Dict[str, Any]) -> int:
        """
        Merges data pulled from PocketBase into local SQLite.
        Strategy: INSERT OR IGNORE for projects/sessions; Last-Write-Wins for tasks.
        Returns the count of new records inserted.
        """
        if not self.conn or not cloud_data:
            return 0

        def _normalize_dt(dt_str: Optional[str]) -> Optional[str]:
            """Strip PocketBase's milliseconds/timezone: '2024-01-15 10:30:00.123Z' -> '2024-01-15 10:30:00'"""
            if not dt_str:
                return None
            return dt_str.replace('Z', '').split('.')[0].strip()

        merged = 0
        try:
            # 1. Projects — simple upsert, no conflict possible
            for p in cloud_data.get("projects", []):
                name = p.get("project_name")
                if not name:
                    continue
                self.cursor.execute(
                    "INSERT OR IGNORE INTO projects (project_name) VALUES (?)", (name,)
                )
                if self.cursor.rowcount:
                    merged += 1

            # 2. Sessions — local_id in cloud == session_id locally; skip duplicates
            for s in cloud_data.get("sessions", []):
                sid = s.get("local_id")
                if not sid:
                    continue
                try:
                    self.cursor.execute("""
                        INSERT OR IGNORE INTO sessions (
                            session_id, project_name, task_name, session_type,
                            start_time, end_time, duration_minutes, status,
                            focus_score, end_mood, interruption_reason
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        sid,
                        s.get("project_name"), s.get("task_name"), s.get("session_type"),
                        _normalize_dt(s.get("start_time")), _normalize_dt(s.get("end_time")),
                        s.get("duration_minutes"), s.get("status"),
                        s.get("focus_score"), s.get("end_mood"), s.get("interruption_reason")
                    ))
                    if self.cursor.rowcount:
                        merged += 1
                except sqlite3.Error:
                    pass

            # 3. Tasks — Last-Write-Wins via latest session end_time
            cloud_sessions = cloud_data.get("sessions", [])
            for t in cloud_data.get("tasks", []):
                p_name, t_name = t.get("project_name"), t.get("task_name")
                if not p_name or not t_name:
                    continue

                self.cursor.execute(
                    "SELECT 1 FROM tasks WHERE project_name=? AND task_name=?", (p_name, t_name)
                )
                if not self.cursor.fetchone():
                    # New task from cloud — insert
                    self.cursor.execute("""
                        INSERT OR IGNORE INTO tasks
                            (task_name, project_name, estimated_pomodoros, status, sound_preference)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        t_name, p_name,
                        t.get("estimated_pomodoros", 1),
                        t.get("status", "In Progress"),
                        t.get("sound_preference", "dida")
                    ))
                    merged += 1
                else:
                    # Conflict: compare latest session end_time from each side
                    self.cursor.execute(
                        "SELECT MAX(end_time) FROM sessions WHERE project_name=? AND task_name=?",
                        (p_name, t_name)
                    )
                    local_time = self.cursor.fetchone()[0] or "1970-01-01"

                    cloud_times = [
                        _normalize_dt(s.get("end_time")) or "1970-01-01"
                        for s in cloud_sessions
                        if s.get("project_name") == p_name and s.get("task_name") == t_name
                    ]
                    cloud_time = max(cloud_times, default="1970-01-01")

                    if cloud_time > local_time:
                        self.cursor.execute("""
                            UPDATE tasks SET estimated_pomodoros=?, status=?, sound_preference=?
                            WHERE project_name=? AND task_name=?
                        """, (
                            t.get("estimated_pomodoros", 1),
                            t.get("status", "In Progress"),
                            t.get("sound_preference", "dida"),
                            p_name, t_name
                        ))

            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Cloud merge error: {e}")
            self.conn.rollback()

        return merged

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

    def get_all_data_for_sync(self) -> Dict[str, Any]:
        """Returns all local data formatted for a full cloud sync push."""
        if not self.conn:
            return {"projects": [], "tasks": [], "sessions": []}
        try:
            self.cursor.execute('SELECT project_name FROM projects')
            projects = [{"project_name": r[0]} for r in self.cursor.fetchall()]

            self.cursor.execute(
                'SELECT project_name, task_name, estimated_pomodoros, status, sound_preference FROM tasks'
            )
            tasks = [
                {"project_name": r[0], "task_name": r[1], "estimated_pomodoros": r[2],
                 "status": r[3], "sound_preference": r[4]}
                for r in self.cursor.fetchall()
            ]

            self.cursor.execute(
                '''SELECT session_id, project_name, task_name, session_type,
                          start_time, end_time, duration_minutes, status,
                          focus_score, end_mood, interruption_reason FROM sessions'''
            )
            sessions = [
                {"session_id": r[0], "project_name": r[1], "task_name": r[2],
                 "session_type": r[3], "start_time": r[4], "end_time": r[5],
                 "duration_minutes": r[6], "status": r[7], "focus_score": r[8],
                 "end_mood": r[9], "interruption_reason": r[10]}
                for r in self.cursor.fetchall()
            ]
            return {"projects": projects, "tasks": tasks, "sessions": sessions}
        except sqlite3.Error as e:
            print(f"Error fetching data for sync: {e}")
            return {"projects": [], "tasks": [], "sessions": []}

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
            
            # Cloud Sync (Async)
            SyncManager.sync_data("projects", {"project_name": project_name}, record_id=project_name)
            
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

    def add_or_update_task(self, project_name: str, task_name: str, estimate: int, sound_preference: str = 'dida') -> None:
        """Adds a new task or updates an existing one."""
        if not all([self.conn, project_name, task_name]): return
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
            self.conn.commit()
            
            # Cloud Sync (Async)
            sync_payload = {
                "project_name": project_name,
                "task_name": task_name,
                "estimated_pomodoros": estimate,
                "status": "In Progress",
                "sound_preference": sound_preference
            }
            # Use project_name + task_name as a composite unique identifier for sync
            SyncManager.sync_data("tasks", sync_payload, record_id=f"{project_name}_{task_name}")
            
        except sqlite3.Error as e:
            print(f"Error adding/updating task: {e}")

    def mark_task_as_complete(self, project_name: str, task_name: str) -> None:
        """Marks a task as completed."""
        if not all([self.conn, project_name, task_name]): return
        try:
            self.cursor.execute("UPDATE tasks SET status = 'Completed' WHERE project_name = ? AND task_name = ?", (project_name, task_name))
            self.conn.commit()
            
            # Cloud Sync (Async)
            sync_payload = {
                "project_name": project_name,
                "task_name": task_name,
                "status": "Completed"
            }
            SyncManager.sync_data("tasks", sync_payload, record_id=f"{project_name}_{task_name}")
            
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
            
            # Cloud Sync: We don't have a specific delete in SyncManager yet, 
            # but we can add it or just log it. For now, let's just use a special flag or separate method.
            # However, deletions are sensitive. Let's skip for now unless requested or implement a simple delete.
            SyncManager.delete_record("projects", project_name)
            
        except sqlite3.Error as e:
            print(f"Error deleting project: {e}")

    def delete_task(self, project_name: str, task_name: str) -> None:
        """Deletes a specific task."""
        if not all([self.conn, project_name, task_name]): return
        try:
            self.cursor.execute("DELETE FROM tasks WHERE project_name = ? AND task_name = ?", (project_name, task_name))
            self.conn.commit()
            SyncManager.delete_record("tasks", f"{project_name}_{task_name}")
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
