# main.py - FocusFlow 3.0
import os
import sys
import shutil
import random
import filecmp
import logging
import threading
from pathlib import Path
import customtkinter as ctk
from tkinter import messagebox, filedialog  # Keep these for dialogs
from datetime import datetime
import re
from typing import Optional

from config import *
from ctk_theme_config import ThemeManager
from pb_sync_manager import PBSyncManager
from pomodoro_timer import PomodoroTimer
from pomodoro_data_manager import PomodoroDataManager
from sound_manager import SoundManager
from ui_manager import UIManager, DateRangeDialog
from analysis_manager import AnalysisManager
from feedback_window import FeedbackWindow
from interruption_window import InterruptionWindow

def get_base_path():
    """Gets the base path, ensuring it works for both script and PyInstaller-packaged exe."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

class PomodoroApp:
    """
    Main controller for the FocusFlow Pomodoro application.
    Coordinates between UI, Timer, Data, and Sound managers.
    """
    def __init__(self, root: ctk.CTk):
        """
        Initializes the application, sets up paths, and instantiates managers.
        
        Args:
            root: The main CustomTkinter window.
        """
        self.root = root
        
        # --- Initialize Theme System ---
        ThemeManager.initialize(DEFAULT_THEME_MODE)
        
        # --- Paths ---
        self.base_dir = get_base_path()
        self.data_dir = os.path.join(self.base_dir, "data")
        self.image_dir = os.path.join(self.base_dir, "images")
        self.sound_dir = os.path.join(self.base_dir, "sound")
        
        # Ensure directories exist
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.image_dir, exist_ok=True)
        os.makedirs(self.sound_dir, exist_ok=True)

        # --- Icon ---
        try:
            icon_path = os.path.join(self.image_dir, "Microsoft-Fluentui-Emoji-Flat-Tomato-Flat.512.ico")
            self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"Icon Error: {e}")

        # --- DB Backup ---
        self._manage_db_backups()

        # --- Modules (Initialized in Order) ---
        self.data_manager = PomodoroDataManager(self.data_dir, DB_NAME)
        
        # 1. SoundManager (含事件系统)
        self.sound_manager = SoundManager(self.sound_dir) 
        
        self.analysis_manager = AnalysisManager(self.data_manager, self.base_dir) 
        self.timer = PomodoroTimer(WORK_MIN, SHORT_BREAK_MIN, LONG_BREAK_MIN, self.update_timer_display, self.on_timer_finish)
        
        # --- UI ---
        all_projects = self.data_manager.get_all_projects()
        self.ui = UIManager(
            self.root,
            self.handle_action_button,
            self.mark_current_task_complete,
            self.show_analysis_dialog,
            self.quick_start_session,
            self.load_backup,
            self.merge_databases,
            self.sync_to_cloud,
            self.switch_sound_mode,
            self.delete_project_handler,
            self.delete_task_handler,
            self.handle_home_button,
            self.toggle_theme,  # New callback
            self.image_dir,
            all_projects,
            self.sound_manager  # Pass sound_manager reference
        )
        
        # --- State ---
        self.is_running = False
        self.current_session_type = 'Work'
        self.current_project = ""
        self.current_task = ""
        self.current_task_estimate = 1
        self.current_kr_ref = ""
        self._cloud_task_map: dict = {}    # display_str → {task, kr, pomodoros_est, ...}
        self._cloud_projects: dict = {}    # project_name → [display_str, ...]

        # --- Init ---
        self.setup_window_properties()
        self.reset_state_and_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.bind("<<ProjectSelected>>", self.on_project_selected)
        self.root.bind("<<TaskSelected>>", self.on_task_selected)

        # === 【新增】启动事件监听循环 ===
        self.check_pygame_events()

        # --- PocketBase Sync (OpenClaw server, async, non-blocking) ---
        self.pb_sync = PBSyncManager(self.data_dir, on_connected=self._on_pb_connected)

        # --- Startup Cloud Pull (async, non-blocking) ---
        self._startup_cloud_pull()

        # --- Runtime Session Tracking ---
        # Stores session counts for the current runtime: {(project_name, task_name): count}
        self.local_session_counts = {}

    def check_pygame_events(self) -> None:
        """
        Polls Pygame events every 100ms.
        Used with SoundManager's set_endevent for smart music switching.
        """
        if hasattr(self, 'sound_manager'):
            self.sound_manager.check_music_events()
        
        # 100毫秒后再次调用自己，保持心跳
        self.root.after(100, self.check_pygame_events)

    def _manage_db_backups(self) -> None:
        """
        Manages rolling database backups (bak1, bak2).
        Only backs up if changes are detected compared to the last backup.
        """
        db_path = os.path.join(self.data_dir, DB_NAME)
        bak1_path = db_path + ".bak1"
        bak2_path = db_path + ".bak2"
        
        # Setup basic logging
        logging.basicConfig(filename=os.path.join(self.data_dir, 'backup.log'), 
                            level=logging.INFO, 
                            format='%(asctime)s - %(levelname)s - %(message)s')

        try:
            if not os.path.exists(db_path):
                logging.warning(f"Database not found at {db_path}. Skipping backup.")
                return

            # Check if backup is needed (compare with bak1)
            if os.path.exists(bak1_path) and filecmp.cmp(db_path, bak1_path, shallow=False):
                logging.info("Database unchanged since last backup. Skipping backup.")
                return

            # Proceed with rolling backup
            if os.path.exists(bak2_path):
                try:
                    os.remove(bak2_path)
                except OSError as e:
                    logging.error(f"Failed to remove old backup {bak2_path}: {e}")
            
            if os.path.exists(bak1_path):
                try:
                    os.rename(bak1_path, bak2_path)
                except OSError as e:
                     logging.error(f"Failed to rotate backup {bak1_path} to {bak2_path}: {e}")

            shutil.copy2(db_path, bak1_path)
            logging.info(f"Backup successful: {bak1_path} created.")
            
        except Exception as e:
            error_msg = f"Critical error during database backup: {e}"
            print(error_msg)
            logging.error(error_msg)

    def setup_window_properties(self) -> None:
        """Sets window properties like 'Always on Top' based on configuration."""
        if ALWAYS_ON_TOP: self.root.attributes('-topmost', 1)

    def _truncate_text(self, text: str, max_length: int = 20) -> str:
        """Truncates text with ellipsis if it exceeds max_length."""
        return text[:max_length-3] + "..." if len(text) > max_length else text

    def _get_clean_task_name(self, task_name: str) -> str:
        """Removes display suffixes: ' (N🍅)' cloud format or ' (N)' local format."""
        if not task_name: return ""
        m = re.match(r"^(.*) \(\d+🍅\)$", task_name)
        if m: return m.group(1)
        m = re.match(r"^(.*) \(\d+\)$", task_name)
        return m.group(1) if m else task_name

    def update_db_status(self) -> None:
        """Updates the database status timestamp in the UI."""
        mod_time = self.data_manager.get_db_last_modified_time()
        self.ui.update_db_status(mod_time)

    def switch_sound_mode(self, mode: str) -> None:
        """Handles UI callback for switching sound modes (Ticking/Music/Mute)."""
        self.ui.set_sound_choice(mode)
        self.sound_manager.play_mode(mode)

    def load_backup(self) -> None:
        """Prompts user to select a backup file and restores it."""
        backup_path = filedialog.askopenfilename(initialdir=self.data_dir, title="Select backup", filetypes=[("DB Backups", "*.bak*"), ("All files", "*.*")])
        if not backup_path: return
        if not self.data_manager.verify_db_schema(backup_path):
            messagebox.showerror("Error", "Invalid database file.")
            return
        if messagebox.askyesno("Confirm Restore", "Overwrite current data with backup?"):
            try:
                self.data_manager.close()
                shutil.copy(backup_path, os.path.join(self.data_dir, DB_NAME))
                messagebox.showinfo("Success", "Backup restored.")
                self.data_manager = PomodoroDataManager(self.data_dir, DB_NAME)
                self.reset_state_and_ui()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to restore: {e}")
                self.data_manager = PomodoroDataManager(self.data_dir, DB_NAME)

    def merge_databases(self) -> None:
        """Prompts user to select a database file to merge data from."""
        source_db_path = filedialog.askopenfilename(title="Merge From", initialdir=self.data_dir, filetypes=[("Database Files", "*.db*"), ("All Files", "*.*")])
        if not source_db_path: return
        if not self.data_manager.verify_db_schema(source_db_path):
            messagebox.showerror("Error", "Invalid source database.")
            return
        if messagebox.askyesno("Confirm Merge", "Merge new data from selected file?"):
            try:
                self.data_manager.merge_from(source_db_path)
                messagebox.showinfo("Success", "Merge successful.")
                self.reset_state_and_ui()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to merge: {e}")

    def _startup_cloud_pull(self) -> None:
        """On startup, PBSyncManager handles its own async connection + offline queue flush.
        Schedule a cloud task fetch after the tunnel has time to connect (~4s)."""
        self.root.after(4000, self._refresh_cloud_tasks)

    def _on_pb_connected(self) -> None:
        """Called by PBSyncManager background thread when tunnel + auth succeed.
        Runs _refresh_cloud_tasks on the main thread so the task list updates
        even if the initial 4s startup fetch fired before the connection was ready."""
        self.root.after(0, self._refresh_cloud_tasks)

    def _refresh_cloud_tasks(self) -> None:
        """Fetch today's active tasks from cloud, group by project, populate dropdowns."""
        def _fetch():
            tasks = self.pb_sync.get_today_tasks()
            if not tasks:
                return
            by_project: dict = {}
            display_map: dict = {}
            for t in tasks:
                proj = t.get("project", "FocusFlow")
                est = t.get("pomodoros_est", 0)
                display = f"{t['task']} ({est}🍅)" if est else t['task']
                by_project.setdefault(proj, []).append(display)
                display_map[display] = t

            def _update():
                self._cloud_task_map = display_map
                self._cloud_projects = by_project
                cloud_proj_list = list(by_project.keys())
                local_projects = self.data_manager.get_all_projects()
                merged = cloud_proj_list + [p for p in local_projects if p not in cloud_proj_list]
                self.ui.project_combobox.configure(values=merged)
                if cloud_proj_list:
                    self.ui.project_var.set(cloud_proj_list[0])
                    self.ui.set_task_list(by_project[cloud_proj_list[0]])
                    self.ui.task_var.set('')

            self.root.after(0, _update)

        threading.Thread(target=_fetch, daemon=True).start()

    def sync_to_cloud(self) -> None:
        """Manually flushes offline-queued sessions to PocketBase and refreshes cloud tasks."""
        if not PB_SYNC_ENABLED:
            messagebox.showinfo("Sync Disabled", "Cloud sync is disabled in config.")
            return

        self.ui.set_sync_button_state("Syncing...", "#F4A261")

        def _flush():
            try:
                flushed = self.pb_sync.queue.flush(self.pb_sync.pb)
                label = f"Synced {flushed} ✓" if flushed else "Synced ✓"
                self.root.after(0, lambda: self.ui.set_sync_button_state(label, "#52B788"))
                self.root.after(3000, lambda: self.ui.set_sync_button_state("Sync", "#888888"))
                # Refresh task list from cloud
                self.root.after(500, self._refresh_cloud_tasks)
            except Exception:
                self.root.after(0, lambda: self.ui.set_sync_button_state("Sync Failed", "#e76f51"))
                self.root.after(3000, lambda: self.ui.set_sync_button_state("Sync", "#888888"))

        threading.Thread(target=_flush, daemon=True).start()

    def delete_project_handler(self) -> None:
        """Handles deletion of the currently selected project."""
        project = self.ui.get_project_name()
        if not project: return
        if messagebox.askyesno("Confirm Delete", f"Delete project '{project}' and ALL its tasks?"):
            self.data_manager.delete_project(project)
            self.reset_state_and_ui()

    def delete_task_handler(self) -> None:
        """Handles deletion of the currently selected task."""
        project = self.ui.get_project_name()
        raw_task = self.ui.get_task_name()
        task = self._get_clean_task_name(raw_task)
        if not project or not task: return
        if messagebox.askyesno("Confirm Delete", f"Delete task '{task}'?"):
            self.data_manager.delete_task(project, task)
            self.on_project_selected() 

    def handle_action_button(self) -> None:
        """Handles the main Start/Abort action button."""
        if self.is_running: self.abort_session()
        else: self.start_session()
    
    def handle_home_button(self) -> None:
        """Returns to setup screen, aborting any active session with 'Task Switching' reason."""
        if self.is_running:
            # Stop timer and get session info
            start_time = self.timer.start_time
            session_type, duration, status = self.timer.reset()
            self.sound_manager.stop_bg_sound()
            self.is_running = False
            
            # Record interruption for Work sessions with hardcoded reason
            if session_type == 'Work' and self.current_project and self.current_task:
                session_data = {
                    'project_name': self.current_project,
                    'task_name': self.current_task,
                    'session_type': session_type,
                    'start_time': start_time,
                    'end_time': datetime.now(),
                    'duration_minutes': duration,
                    'status': "Interrupted",
                    'interruption_reason': "Task Switching"
                }
                self.data_manager.record_session(session_data)
                self.pb_sync.record_session(session_data, kr_ref=self.current_kr_ref)  # async, non-blocking

            # Disable particles
            self.ui.set_timer_mode('None')
        
        # Always return to setup
        self.reset_state_and_ui()

    def toggle_theme(self) -> None:
        """Toggles between Light and Dark visual modes."""
        ThemeManager.toggle()

    def show_analysis_dialog(self) -> None:
        """Displays the analysis date range selection dialog."""
        DateRangeDialog(self.root, self.analysis_manager.generate_and_show_report)

    def quick_start_session(self, project: str, task: str) -> None:
        """Instantly starts a session for a specific project/task."""
        self.start_session(project_name=project, task_name=task)

    def mark_current_task_complete(self) -> None:
        """Marks the current task as completed in the database."""
        if not self.current_task: return
        if messagebox.askyesno("Confirm", f"Mark '{self.current_task}' as complete?"):
            if self.is_running: self.abort_session(is_completing=True)
            else: self.data_manager.mark_task_as_complete(self.current_project, self.current_task)
            self.reset_state_and_ui()

    def on_project_selected(self, event=None) -> None:
        """Callback when a project is selected; refreshes task list."""
        project_name = self.ui.get_project_name()
        if not project_name:
            return
        self.ui.task_var.set('')
        self.ui.estimate_var.set('1')
        self.ui.update_progress("")
        if project_name in self._cloud_projects:
            self.ui.set_task_list(self._cloud_projects[project_name])
            return
        self.ui.set_sound_choice('dida')
        tasks_data = self.data_manager.get_tasks_with_stats(project_name, include_completed=False)
        formatted_tasks = [f"{t['name']} ({t['count']})" for t in tasks_data]
        self.ui.set_task_list(formatted_tasks)

    def on_task_selected(self, event=None) -> None:
        """Callback when a task is selected; refreshes task details and progress."""
        project_name = self.ui.get_project_name()
        raw_task_name = self.ui.get_task_name()

        # Cloud task: look up in map by display string, extract kr_ref and estimate
        if raw_task_name in self._cloud_task_map:
            t = self._cloud_task_map[raw_task_name]
            self.current_kr_ref = t.get("kr", "")
            est = t.get("pomodoros_est", 1) or 1
            self.ui.set_estimate(est)
            # Show local progress if any prior sessions exist
            clean = t["task"]
            done = self.data_manager.get_completed_work_sessions_for_task(project_name, clean)
            self.ui.update_progress(f"({done} / {est})" if done else "")
            return

        self.current_kr_ref = ""
        task_name = self._get_clean_task_name(raw_task_name)
        if project_name and task_name:
            details = self.data_manager.get_task_details(project_name, task_name)
            if details:
                self.ui.set_estimate(details["estimate"])
                completed_count = self.data_manager.get_completed_work_sessions_for_task(project_name, task_name)
                self.ui.update_progress(f"({completed_count} / {details['estimate']})")
                if details.get("sound"):
                    self.ui.set_sound_choice(details["sound"])

    def update_timer_display(self, time_str: str) -> None:
        """Thread-safe update of the timer UI."""
        self.root.after(0, self.ui.update_timer_display, time_str)

    def on_timer_finish(self, session_type: str, duration: int, status: str) -> None:
        """Callback triggered when a timer session finishes naturally."""
        self.root.after(0, self._handle_session_finish, session_type, duration, status)
        
    def on_closing(self) -> None:
        """Handles application close event with confirmation if timer is running."""
        self.root.attributes('-alpha', 1.0)
        if self.is_running:
            if messagebox.askyesno("Timer Running", "Quit while timer is running?"):
                self.abort_session(is_closing=True)
                self.data_manager.close()
                self.pb_sync.stop()
                self.root.destroy()
        else:
            self.data_manager.close()
            self.pb_sync.stop()
            self.root.destroy()

    def start_session(self, project_name: Optional[str] = None, task_name: Optional[str] = None) -> None:
        """Initiates a Work or Break session."""
        is_manual_start = (project_name is None and task_name is None and self.current_task)
        if is_manual_start:
            project_name, task_name = self.current_project, self.current_task
        elif project_name is None: 
            project_name = self.ui.get_project_name()
            raw_task = self.ui.get_task_name()
            task_name = self._get_clean_task_name(raw_task)
        
        if not project_name: project_name = "General Tasks"
        if not task_name:
             messagebox.showwarning("Input Required", "Please enter a task name.")
             return
        
        self.is_running = True
        self.ui.toggle_action_button(is_running=True)
        self.ui.toggle_secondary_button(is_running=True)
        self.ui.show_timer_view()
        
        from ctk_theme_config import ThemeManager
        pygame_bg = ThemeManager.get_color("bg")
        if hasattr(self.ui, 'pygame_widget'):
            self.ui.pygame_widget.set_background_color(pygame_bg)
            self.ui.pygame_widget.update_display()
        
        if self.current_session_type == 'Work':
            self.root.attributes('-alpha', FOCUSED_TRANSPARENCY)
            self.current_project, self.current_task = project_name, task_name
            details = self.data_manager.get_task_details(project_name, task_name)
            self.current_task_estimate = details['estimate'] if details else self.ui.get_estimate()
            
            sound_choice = self.ui.get_sound_choice() 
            self.data_manager.add_or_update_task(project_name, task_name, self.current_task_estimate, sound_choice)
            
            self.ui.update_header(self._truncate_text(task_name), GREEN)
            self.update_progress_display()
            self.sound_manager.play_mode(sound_choice)
            self.ui.set_timer_mode('Work')

        else: # Break
            self.root.attributes('-alpha', 1.0)
            self.ui.update_header("Break", PINK if self.current_session_type == 'Short Break' else RED)
            self.ui.update_complete_button_status(is_completed=True)
            self.ui.set_timer_mode(self.current_session_type)
        self.timer.start(self.current_session_type)

    def abort_session(self, is_closing: bool = False, is_completing: bool = False) -> None:
        """Aborts the current active session."""
        if not self.is_running: return
        start_time = self.timer.start_time
        session_type, duration, status = self.timer.reset()
        if session_type == 'Work' and start_time:
            self._get_and_record_feedback(start_time, duration, status, is_interruption=True)
        if not is_closing and not is_completing:
            self.sound_manager.stop_bg_sound()
            self._setup_next_work_session()

    def reset_state_and_ui(self) -> None:
        """Resets the application state and UI to the setup screen."""
        self.current_session_type = 'Work'
        if hasattr(self, 'sound_manager'):
            self.sound_manager.stop_bg_sound()

        self.is_running = False
        self.current_kr_ref = ""
        self.ui.toggle_action_button(is_running=False)
        self.ui.toggle_secondary_button(is_running=False)
        self.root.attributes('-alpha', 1.0)

        local_projects = self.data_manager.get_all_projects()
        if self._cloud_projects:
            cloud_proj_list = list(self._cloud_projects.keys())
            merged = cloud_proj_list + [p for p in local_projects if p not in cloud_proj_list]
            self.ui.set_project_list(merged)
            first = cloud_proj_list[0]
            self.ui.project_var.set(first)
            self.ui.set_task_list(self._cloud_projects[first])
        else:
            self.ui.set_project_list(local_projects)
            if local_projects:
                first_local = local_projects[0]
                self.ui.project_var.set(first_local)
                local_tasks = self.data_manager.get_tasks_for_project(first_local)
                self.ui.set_task_list(local_tasks)
            else:
                self.ui.set_task_list([])

        self.ui.task_var.set('')
        self.ui.estimate_var.set('1')

        recent_tasks = self.data_manager.get_recent_tasks_with_projects()
        self.ui.update_quick_start_buttons(recent_tasks)

        self.current_project, self.current_task = "", ""
        self.ui.show_setup_view()
        self.ui.set_timer_mode("Idle")
        self.update_progress_display()
        self.update_db_status()

    def _setup_next_work_session(self) -> None:
        """Prepares the UI for the next work session (after a break or abort)."""
        self.is_running = False
        self.ui.toggle_action_button(is_running=False)
        self.ui.toggle_secondary_button(is_running=True)
        self.root.attributes('-alpha', 1.0)
        self.update_progress_display()
        self.ui.set_timer_mode("Idle")
        self.current_session_type = 'Work'
        self.ui.update_header(self._truncate_text(self.current_task or "Timer"), GREEN)
        self.ui.update_timer_display(f"{WORK_MIN:02d}:00")

    def update_progress_display(self) -> None:
        """Updates the visual progress bar and daily checkmarks."""
        if self.current_project and self.current_task:
            completed_for_task = self.data_manager.get_completed_work_sessions_for_task(self.current_project, self.current_task)
            details = self.data_manager.get_task_details(self.current_project, self.current_task)
            
            estimate = 1
            if details:
                estimate = int(details.get("estimate", 1))
                if estimate <= 0: estimate = 1
                
                is_completed = (details["status"] == 'Completed')
                self.ui.update_complete_button_status(is_completed=is_completed)
            
            if hasattr(self.ui, 'session_progress_bar'):
                self.ui.session_progress_bar.set_progress(completed_for_task, estimate)
                
        else:
            if hasattr(self.ui, 'session_progress_bar'):
                self.ui.session_progress_bar.set_progress(0, 1)
            
        total_today = self.data_manager.get_total_completed_work_sessions_today()
        fives = total_today // 5
        ones = total_today % 5
        checkmark_string = ("❺ " * fives) + ("🍅 " * ones)
        self.ui.update_daily_checkmarks(checkmark_string.strip())

    def _get_and_record_feedback(self, start_time: datetime, duration: int, status: str, is_interruption: bool = False) -> None:
        """Shows feedback/interruption dialogs and records the session."""
        feedback, interruption_reason = {}, None
        if is_interruption:
            interruption_reason = InterruptionWindow(self.root).get_reason()
        
        if duration > 0:
            completed_count = self.data_manager.get_completed_work_sessions_for_task(self.current_project, self.current_task)
            if completed_count == 0 or (FEEDBACK_INTERVAL > 0 and (completed_count + 1) % FEEDBACK_INTERVAL == 0):
                if self.root.state() == 'iconic':
                    self.root.deiconify()
                feedback = FeedbackWindow(self.root, self.image_dir).get_feedback()
            else:
                last_feedback = self.data_manager.get_last_feedback_for_task(self.current_project, self.current_task)
                if last_feedback: feedback = last_feedback

            session_data = {
                'project_name': self.current_project, 'task_name': self.current_task,
                'session_type': self.current_session_type, 'start_time': start_time,
                'end_time': datetime.now(), 'duration_minutes': duration,
                'status': status, 'interruption_reason': interruption_reason, **feedback
            }
            self.data_manager.record_session(session_data)
            if self.current_session_type == 'Work':
                self.pb_sync.record_session(session_data, kr_ref=self.current_kr_ref)  # async, non-blocking
            self.update_db_status()

    def _handle_session_finish(self, session_type: str, duration: int, status: str) -> None:
        """Handles session completion, including transition to breaks and sound alerts."""
        self.is_running = False
        self.sound_manager.play_end_sound()
        
        if session_type == 'Work':
            self._get_and_record_feedback(self.timer.start_time, duration, status)
            self.update_progress_display()
            
            if RESET_LONG_BREAK_ON_RESTART:
                key = (self.current_project, self.current_task)
                self.local_session_counts[key] = self.local_session_counts.get(key, 0) + 1
                completed_count = self.local_session_counts[key]
            else:
                completed_count = self.data_manager.get_completed_work_sessions_for_task(self.current_project, self.current_task)
            
            self.current_session_type = 'Long Break' if completed_count > 0 and completed_count % LONG_BREAK_INTERVAL == 0 else 'Short Break'
            self.start_session(project_name=self.current_project, task_name=self.current_task)
        else: 
            self.data_manager.record_session({
                'project_name': self.current_project, 'task_name': self.current_task,
                'session_type': session_type, 'start_time': self.timer.start_time,
                'end_time': datetime.now(), 'duration_minutes': duration, 'status': status
            })
            self.update_db_status()
            self._setup_next_work_session()

if __name__ == "__main__":
    window = ctk.CTk()
    app = PomodoroApp(window)
    window.mainloop()