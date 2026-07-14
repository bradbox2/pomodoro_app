# main.py - FocusFlow 3.0
import os
import sys
import shutil
import random
import filecmp
import logging
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import customtkinter as ctk
from tkinter import messagebox, filedialog, simpledialog, StringVar, BooleanVar  # Keep these for dialogs
from datetime import datetime
import re
from typing import Optional

from focusflow.config import *
from focusflow.ctk_theme_config import ThemeManager
from focusflow.app_paths import AppPaths
from focusflow.app_config_manager import AppConfigManager
from focusflow.pomodoro_timer import PomodoroTimer
from focusflow.pomodoro_data_manager import PomodoroDataManager
from focusflow.sound_manager import SoundManager
from focusflow.ui_manager import UIManager, DateRangeDialog
from focusflow.analysis_manager import AnalysisManager
from focusflow.feedback_window import FeedbackWindow
from focusflow.interruption_window import InterruptionWindow
from focusflow.goalsifter_client import GoalSifterClient, GoalSifterRemoteError
from focusflow.goalsifter_settings import GoalSifterSettings

APP_LOGGER = logging.getLogger("focusflow.app")
BACKUP_LOGGER = logging.getLogger("focusflow.backup")

def get_base_path():
    """Project root holding bundled assets (images/, sound/) and legacy data.

    Works both from a source checkout (this module lives at
    <root>/src/focusflow/main.py, so the root is two parents up) and from a
    PyInstaller one-folder build (assets sit next to the executable).
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return str(Path(__file__).resolve().parents[2])

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
        self.root.report_callback_exception = self._report_callback_exception
        
        # --- Paths ---
        self.base_dir = get_base_path()
        self.paths = AppPaths.from_environment(Path(self.base_dir))
        self.paths.ensure_ready()
        self._configure_loggers()
        self.config_manager = AppConfigManager(self.paths.config_path)
        self.preferences = self.config_manager.get_preferences()

        # --- Initialize Theme System ---
        ThemeManager.initialize(self.preferences["theme_mode"])

        self.data_dir = str(self.paths.data_dir)
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
        self.goalsifter_settings = GoalSifterSettings.load(self.paths)
        self.goalsifter_client = GoalSifterClient(self.goalsifter_settings)
        self.goalsifter_tunnel = None
        self._goalsifter_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="focusflow-gs")
        self._goalsifter_sync_in_flight = False
        self._goalsifter_retry_delay = 1
        self._goalsifter_retry_job = None
        
        # 1. SoundManager (含事件系统)
        self.sound_manager = SoundManager(self.sound_dir) 
        
        self.analysis_manager = AnalysisManager(self.data_manager, self.paths.exports_dir, self.paths.config_path)
        self.timer = PomodoroTimer(
            self.preferences["work_minutes"],
            self.preferences["short_break_minutes"],
            self.preferences["long_break_minutes"],
            self.update_timer_display,
            self.on_timer_finish,
        )
        
        # --- UI ---
        all_projects = self.data_manager.get_local_project_names()
        self.ui = UIManager(
            self.root,
            self.handle_action_button,
            self.mark_current_task_complete,
            self.show_analysis_dialog,
            self.quick_start_session,
            self.load_backup,
            self.merge_databases,
            self.switch_sound_mode,
            self.delete_project_handler,
            self.delete_task_handler,
            self.handle_home_button,
            self.toggle_theme,  # New callback
            self.open_settings_dialog,
            self.select_local_focus_item,
            self.refresh_goalsifter_tasks,
            self.sync_goalsifter_outbox,
            self.bind_current_focus_item,
            self.create_and_bind_current_focus_item,
            self.open_goalsifter_settings,
            self.complete_goalsifter_focus_item,
            self.show_local_task_manager,
            self.image_dir,
            all_projects,
            self.sound_manager  # Pass sound_manager reference
        )
        self.ui.apply_display_preferences(self.preferences)
        
        # --- State ---
        self.is_running = False
        self.current_session_type = 'Work'
        self.current_project = ""
        self.current_task = ""
        self.current_task_estimate = 1
        self.current_focus_source = "local"
        self.current_goalsifter_task_id = None
        self._goalsifter_refresh_in_flight = False
        self._goalsifter_focus_refresh_job = None

        # --- Init ---
        self.setup_window_properties()
        self.reset_state_and_ui()
        # Optionally connect to GoalSifter on startup (never blocks local timing).
        self.root.after(900, self._maybe_auto_connect_goalsifter)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.bind("<<ProjectSelected>>", self.on_project_selected)
        self.root.bind("<<TaskSelected>>", self.on_task_selected)
        self.root.bind("<FocusIn>", self._on_goalsifter_window_focus)
        self.root.bind("<Visibility>", self._on_goalsifter_window_focus)
        self._schedule_goalsifter_periodic_refresh()

        # === 【新增】启动事件监听循环 ===
        self.check_pygame_events()

        # --- Runtime Session Tracking ---
        # Stores session counts for the current runtime: {(project_name, task_name): count}
        self.local_session_counts = {}

    @staticmethod
    def _report_callback_exception(exc_type, exc_value, exc_traceback) -> None:
        """Keep one bad Tk callback from terminating the whole desktop app."""
        APP_LOGGER.error(
            "Unhandled FocusFlow callback exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

    def _configure_loggers(self) -> None:
        """Keep application errors and database backup diagnostics separate."""
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        for logger, filename in ((APP_LOGGER, "app.log"), (BACKUP_LOGGER, "backup.log")):
            logger.setLevel(logging.INFO)
            logger.propagate = False
            if not any(getattr(handler, "_focusflow_file", False) for handler in logger.handlers):
                handler = logging.FileHandler(self.paths.logs_dir / filename, encoding="utf-8")
                handler.setFormatter(formatter)
                handler._focusflow_file = True
                logger.addHandler(handler)

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
        
        try:
            if not os.path.exists(db_path):
                BACKUP_LOGGER.warning(f"Database not found at {db_path}. Skipping backup.")
                return

            # Check if backup is needed (compare with bak1)
            if os.path.exists(bak1_path) and filecmp.cmp(db_path, bak1_path, shallow=False):
                BACKUP_LOGGER.info("Database unchanged since last backup. Skipping backup.")
                return

            # Proceed with rolling backup
            if os.path.exists(bak2_path):
                try:
                    os.remove(bak2_path)
                except OSError as e:
                    BACKUP_LOGGER.error(f"Failed to remove old backup {bak2_path}: {e}")
            
            if os.path.exists(bak1_path):
                try:
                    os.rename(bak1_path, bak2_path)
                except OSError as e:
                     BACKUP_LOGGER.error(f"Failed to rotate backup {bak1_path} to {bak2_path}: {e}")

            shutil.copy2(db_path, bak1_path)
            BACKUP_LOGGER.info(f"Backup successful: {bak1_path} created.")
            
        except Exception as e:
            error_msg = f"Critical error during database backup: {e}"
            print(error_msg)
            BACKUP_LOGGER.error(error_msg)

    def setup_window_properties(self) -> None:
        """Sets window properties like 'Always on Top' based on configuration."""
        self.root.attributes('-topmost', self.preferences["always_on_top"])

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
                    'interruption_reason': "Task Switching",
                    'device_id': self.goalsifter_settings.device_id,
                }
                self.data_manager.record_session(session_data)

            # Disable particles
            self.ui.set_timer_mode('None')
        
        # Always return to setup
        self.reset_state_and_ui()

    def toggle_theme(self) -> None:
        """Toggles between Light and Dark visual modes."""
        mode = ThemeManager.toggle()
        if hasattr(self, "config_manager"):
            self.preferences = self.config_manager.update_preferences({"theme_mode": mode})

    def open_settings_dialog(self) -> None:
        """Open the user-facing settings window."""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("FocusFlow 设置")
        dialog.geometry("620x650")
        dialog.minsize(560, 580)
        dialog.transient(self.root)

        tabs = ctk.CTkTabview(dialog)
        tabs.pack(fill="both", expand=True, padx=18, pady=(18, 8))
        general_tab = tabs.add("常规")
        interruption_tab = tabs.add("中断选项")
        feedback_tab = tabs.add("Session Feedback")
        body = ctk.CTkScrollableFrame(general_tab, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=2, pady=2)
        preferences = self.preferences
        fields = {}

        def add_section(title: str, description: str):
            card = ctk.CTkFrame(body, corner_radius=10)
            card.pack(fill="x", pady=(0, 12))
            ctk.CTkLabel(card, text=title, font=(FONT_NAME, 16, "bold")).pack(anchor="w", padx=14, pady=(12, 2))
            ctk.CTkLabel(card, text=description, justify="left", anchor="w").pack(fill="x", padx=14, pady=(0, 10))
            return card

        def add_number(card, row, label, key):
            line = ctk.CTkFrame(card, fg_color="transparent")
            line.pack(fill="x", padx=14, pady=4)
            ctk.CTkLabel(line, text=label, anchor="w").pack(side="left", fill="x", expand=True)
            variable = StringVar(value=str(preferences[key]))
            fields[key] = variable
            ctk.CTkEntry(line, textvariable=variable, width=100).pack(side="right")

        timer_card = add_section("计时", "调整下一次工作和休息周期；当前正在进行的计时不会被重置。")
        add_number(timer_card, 0, "工作时长（分钟）", "work_minutes")
        add_number(timer_card, 1, "短休息时长（分钟）", "short_break_minutes")
        add_number(timer_card, 2, "长休息时长（分钟）", "long_break_minutes")
        add_number(timer_card, 3, "几次工作后进入长休息", "long_break_interval")
        add_number(timer_card, 4, "每隔几次请求反馈（0 为关闭）", "feedback_interval")
        reset_var = BooleanVar(value=preferences["reset_long_break_on_restart"])
        fields["reset_long_break_on_restart"] = reset_var
        ctk.CTkCheckBox(timer_card, text="应用重启后重置长休息计数", variable=reset_var).pack(anchor="w", padx=14, pady=(6, 12))

        window_card = add_section("窗口", "控制 FocusFlow 窗口在桌面上的行为。")
        topmost_var = BooleanVar(value=preferences["always_on_top"])
        fields["always_on_top"] = topmost_var
        ctk.CTkCheckBox(window_card, text="窗口总在最前", variable=topmost_var).pack(anchor="w", padx=14, pady=4)
        transparency_var = StringVar(value=f"{int(preferences['focused_transparency'] * 100)}%")
        fields["focused_transparency"] = transparency_var
        transparency_line = ctk.CTkFrame(window_card, fg_color="transparent")
        transparency_line.pack(fill="x", padx=14, pady=(4, 12))
        ctk.CTkLabel(transparency_line, text="计时期间窗口透明度").pack(side="left", fill="x", expand=True)
        ctk.CTkOptionMenu(transparency_line, variable=transparency_var,
                          values=[f"{value}%" for value in range(50, 101, 5)], width=100).pack(side="right")

        display_card = add_section("显示", "主题、动画和字体大小会立即应用。")
        theme_var = StringVar(value=preferences["theme_mode"])
        fields["theme_mode"] = theme_var
        theme_line = ctk.CTkFrame(display_card, fg_color="transparent")
        theme_line.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(theme_line, text="主题").pack(side="left", fill="x", expand=True)
        ctk.CTkOptionMenu(theme_line, variable=theme_var, values=["dark", "light"], width=100).pack(side="right")
        animation_var = BooleanVar(value=preferences["enable_animations"])
        fields["enable_animations"] = animation_var
        ctk.CTkCheckBox(display_card, text="启用计时动画", variable=animation_var).pack(anchor="w", padx=14, pady=4)
        scale_var = StringVar(value=f"{int(preferences['font_size_scale'] * 100)}%")
        fields["font_size_scale"] = scale_var
        scale_line = ctk.CTkFrame(display_card, fg_color="transparent")
        scale_line.pack(fill="x", padx=14, pady=(4, 12))
        ctk.CTkLabel(scale_line, text="字体缩放").pack(side="left", fill="x", expand=True)
        ctk.CTkOptionMenu(scale_line, variable=scale_var,
                          values=[f"{value}%" for value in range(80, 151, 10)], width=100).pack(side="right")

        ctk.CTkLabel(interruption_tab, text="管理中断分类和原因；这里的操作会立即保存。",
                     anchor="w").pack(fill="x", padx=12, pady=(10, 8))
        interruption_body = ctk.CTkFrame(interruption_tab, fg_color="transparent")
        interruption_body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        interruption_body.grid_columnconfigure(0, weight=1)
        interruption_body.grid_columnconfigure(1, weight=2)
        interruption_body.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(interruption_body, text="分类", font=(FONT_NAME, 14, "bold")).grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ctk.CTkLabel(interruption_body, text="原因", font=(FONT_NAME, 14, "bold")).grid(row=0, column=1, sticky="w", padx=6, pady=4)
        category_list = ctk.CTkScrollableFrame(interruption_body, height=300)
        category_list.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        reason_list = ctk.CTkScrollableFrame(interruption_body, height=300)
        reason_list.grid(row=1, column=1, sticky="nsew", padx=(6, 0))
        category_actions = ctk.CTkFrame(interruption_body, fg_color="transparent")
        category_actions.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        reason_actions = ctk.CTkFrame(interruption_body, fg_color="transparent")
        reason_actions.grid(row=2, column=1, sticky="ew", pady=(8, 0))
        selected_category = {"name": None}

        def set_interruption_status(message: str):
            status.configure(text=message)

        def refresh_reasons():
            for widget in reason_list.winfo_children():
                widget.destroy()
            category = selected_category["name"]
            reasons = self.config_manager.get_interruption_reasons().get(category, []) if category else []
            if not reasons:
                ctk.CTkLabel(reason_list, text="此分类暂无中断原因。\n可以点击“新增原因”。").pack(pady=20)
                return
            for reason in reasons:
                row = ctk.CTkFrame(reason_list, fg_color="transparent")
                row.pack(fill="x", pady=2)
                ctk.CTkLabel(row, text=reason.get("name", ""), anchor="w").pack(side="left", fill="x", expand=True, padx=4)
                ctk.CTkButton(row, text="改名", width=48,
                              command=lambda item=reason: rename_reason(item)).pack(side="right", padx=2)
                ctk.CTkButton(row, text="删", width=36,
                              command=lambda item=reason: delete_reason(item)).pack(side="right", padx=2)

        def select_category(category: str):
            selected_category["name"] = category
            refresh_categories()
            refresh_reasons()

        def refresh_categories(select: str | None = None):
            categories = list(self.config_manager.get_interruption_reasons())
            if select in categories:
                selected_category["name"] = select
            elif selected_category["name"] not in categories:
                selected_category["name"] = categories[0] if categories else None
            for widget in category_list.winfo_children():
                widget.destroy()
            if not categories:
                ctk.CTkLabel(category_list, text="暂无分类。\n可以点击“新增分类”。").pack(pady=20)
            for category in categories:
                ctk.CTkButton(category_list, text=category, anchor="w",
                              fg_color=BUTTON_COLOR if category == selected_category["name"] else "transparent",
                              command=lambda value=category: select_category(value)).pack(fill="x", pady=2)

        def add_category():
            name = simpledialog.askstring("新增分类", "分类名称：", parent=dialog)
            if name is None:
                return
            try:
                self.config_manager.add_interruption_category(name)
                refresh_categories(name.strip())
                refresh_reasons()
            except ValueError as error:
                set_interruption_status(f"操作失败：{error}")

        def rename_category():
            old_name = selected_category["name"]
            if not old_name:
                set_interruption_status("请先选择一个分类。")
                return
            name = simpledialog.askstring("重命名分类", "新的分类名称：", initialvalue=old_name, parent=dialog)
            if name is None:
                return
            try:
                new_name = self.config_manager.rename_interruption_category(old_name, name)
                refresh_categories(new_name)
                refresh_reasons()
            except ValueError as error:
                set_interruption_status(f"操作失败：{error}")

        def delete_category():
            category = selected_category["name"]
            if not category:
                set_interruption_status("请先选择一个分类。")
                return
            if not messagebox.askyesno("删除分类", f"删除分类“{category}”及其中的原因？\n历史记录不会受到影响。", parent=dialog):
                return
            try:
                self.config_manager.delete_interruption_category(category)
                selected_category["name"] = None
                refresh_categories()
                refresh_reasons()
            except ValueError as error:
                set_interruption_status(f"操作失败：{error}")

        def add_reason():
            category = selected_category["name"]
            if not category:
                set_interruption_status("请先选择一个分类。")
                return
            name = simpledialog.askstring("新增中断原因", "原因名称：", parent=dialog)
            if name is None:
                return
            try:
                self.config_manager.add_interruption_reason(category, name)
                refresh_reasons()
            except ValueError as error:
                set_interruption_status(f"操作失败：{error}")

        def rename_reason(reason):
            category = selected_category["name"]
            name = simpledialog.askstring("重命名中断原因", "新的原因名称：", initialvalue=reason.get("name", ""), parent=dialog)
            if name is None:
                return
            try:
                self.config_manager.rename_interruption_reason(category, reason["id"], name)
                refresh_reasons()
            except ValueError as error:
                set_interruption_status(f"操作失败：{error}")

        def delete_reason(reason):
            category = selected_category["name"]
            if not messagebox.askyesno("删除中断原因", f"删除“{reason.get('name', '')}”？\n历史记录不会受到影响。", parent=dialog):
                return
            try:
                self.config_manager.delete_interruption_reason(category, reason["id"])
                refresh_reasons()
            except ValueError as error:
                set_interruption_status(f"操作失败：{error}")

        ctk.CTkButton(category_actions, text="新增分类", command=add_category).pack(side="left", padx=2)
        ctk.CTkButton(category_actions, text="重命名", command=rename_category).pack(side="left", padx=2)
        ctk.CTkButton(category_actions, text="删除", command=delete_category).pack(side="left", padx=2)
        ctk.CTkButton(reason_actions, text="新增原因", command=add_reason).pack(side="left", padx=2)
        refresh_categories()
        refresh_reasons()

        ctk.CTkLabel(feedback_tab, text="管理会话结束时显示的情绪选项及其评分；操作会立即保存。",
                     anchor="w").pack(fill="x", padx=12, pady=(10, 8))
        feedback_body = ctk.CTkFrame(feedback_tab, fg_color="transparent")
        feedback_body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        feedback_body.grid_columnconfigure(0, weight=3)
        feedback_body.grid_columnconfigure(1, weight=1)
        feedback_body.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(feedback_body, text="情绪选项", font=(FONT_NAME, 14, "bold")).grid(
            row=0, column=0, sticky="w", padx=6, pady=4
        )
        ctk.CTkLabel(feedback_body, text="评分（1–10）", font=(FONT_NAME, 14, "bold")).grid(
            row=0, column=1, sticky="w", padx=6, pady=4
        )
        feedback_list = ctk.CTkScrollableFrame(feedback_body, height=300)
        feedback_list.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=0)
        feedback_actions = ctk.CTkFrame(feedback_body, fg_color="transparent")
        feedback_actions.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        def refresh_feedback():
            for widget in feedback_list.winfo_children():
                widget.destroy()
            moods = self.config_manager.get_feedback_moods()
            if not moods:
                ctk.CTkLabel(feedback_list, text="暂无情绪选项。\n至少需要保留一项。\n").pack(pady=20)
                return
            for mood in moods:
                row = ctk.CTkFrame(feedback_list, fg_color="transparent")
                row.pack(fill="x", pady=2)
                ctk.CTkLabel(row, text=mood.get("name", ""), anchor="w").pack(
                    side="left", fill="x", expand=True, padx=4
                )
                ctk.CTkLabel(row, text=str(mood.get("score", 5)), width=70).pack(side="left")
                ctk.CTkButton(row, text="修改", width=48,
                              command=lambda item=mood: edit_feedback(item)).pack(side="right", padx=2)
                ctk.CTkButton(row, text="删", width=36,
                              command=lambda item=mood: delete_feedback(item)).pack(side="right", padx=2)

        def add_feedback():
            name = simpledialog.askstring("新增反馈情绪", "情绪名称：", parent=dialog)
            if name is None:
                return
            score = simpledialog.askinteger("新增反馈情绪", "评分（1–10）：", minvalue=1, maxvalue=10, parent=dialog)
            if score is None:
                return
            try:
                self.config_manager.add_feedback_mood(name, score)
                refresh_feedback()
                set_interruption_status("反馈情绪已新增并保存。")
            except ValueError as error:
                set_interruption_status(f"操作失败：{error}")

        def edit_feedback(mood):
            name = simpledialog.askstring("修改反馈情绪", "情绪名称：",
                                          initialvalue=mood.get("name", ""), parent=dialog)
            if name is None:
                return
            score = simpledialog.askinteger("修改反馈情绪", "评分（1–10）：",
                                            initialvalue=mood.get("score", 5), minvalue=1, maxvalue=10,
                                            parent=dialog)
            if score is None:
                return
            try:
                self.config_manager.update_feedback_mood(mood["id"], name, score)
                refresh_feedback()
                set_interruption_status("反馈情绪已修改并保存。")
            except ValueError as error:
                set_interruption_status(f"操作失败：{error}")

        def delete_feedback(mood):
            if not messagebox.askyesno("删除反馈情绪", f"删除“{mood.get('name', '')}”？\n历史记录不会受到影响。",
                                       parent=dialog):
                return
            try:
                self.config_manager.delete_feedback_mood(mood["id"])
                refresh_feedback()
                set_interruption_status("反馈情绪已删除并保存。")
            except ValueError as error:
                set_interruption_status(f"操作失败：{error}")

        ctk.CTkButton(feedback_actions, text="新增情绪", command=add_feedback).pack(side="left", padx=2)
        refresh_feedback()

        status = ctk.CTkLabel(dialog, text="", text_color=ThemeManager.get_color("danger"), anchor="w")
        status.pack(fill="x", padx=18, pady=(0, 4))
        buttons = ctk.CTkFrame(dialog, fg_color="transparent")
        buttons.pack(fill="x", padx=18, pady=(0, 16))

        def save():
            try:
                updates = {
                    "work_minutes": int(fields["work_minutes"].get()),
                    "short_break_minutes": int(fields["short_break_minutes"].get()),
                    "long_break_minutes": int(fields["long_break_minutes"].get()),
                    "long_break_interval": int(fields["long_break_interval"].get()),
                    "feedback_interval": int(fields["feedback_interval"].get()),
                    "reset_long_break_on_restart": bool(fields["reset_long_break_on_restart"].get()),
                    "always_on_top": bool(fields["always_on_top"].get()),
                    "focused_transparency": int(fields["focused_transparency"].get().rstrip("%")) / 100,
                    "theme_mode": fields["theme_mode"].get(),
                    "enable_animations": bool(fields["enable_animations"].get()),
                    "font_size_scale": int(fields["font_size_scale"].get().rstrip("%")) / 100,
                }
                self.apply_preferences(updates)
                dialog.destroy()
            except (TypeError, ValueError, OSError) as error:
                status.configure(text=f"保存失败：{error}")

        ctk.CTkButton(buttons, text="取消", width=90, command=dialog.destroy).pack(side="right")
        ctk.CTkButton(buttons, text="保存", width=90, command=save).pack(side="right", padx=(0, 8))
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)

    def apply_preferences(self, updates: dict) -> dict:
        """Persist user preferences and apply changes without resetting a session."""
        preferences = self.config_manager.update_preferences(updates)
        self.preferences = preferences
        ThemeManager.set_mode(preferences["theme_mode"])
        self.root.attributes("-topmost", preferences["always_on_top"])
        if self.is_running:
            self.root.attributes("-alpha", preferences["focused_transparency"])
        else:
            self.root.attributes("-alpha", 1.0)
        self.timer.settings.update({
            "Work": preferences["work_minutes"],
            "Short Break": preferences["short_break_minutes"],
            "Long Break": preferences["long_break_minutes"],
        })
        self.ui.apply_display_preferences(preferences)
        return preferences

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
            if self.current_focus_source == "goalsifter":
                self._complete_current_goalsifter_task()
            else:
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
        self.ui.set_sound_choice('dida')
        tasks_data = self.data_manager.get_tasks_with_stats(project_name, include_completed=False)
        formatted_tasks = [f"{t['name']} ({t['count']})" for t in tasks_data]
        self.ui.set_task_list(formatted_tasks)

    def on_task_selected(self, event=None) -> None:
        """Callback when a task is selected; refreshes task details and progress."""
        project_name = self.ui.get_project_name()
        raw_task_name = self.ui.get_task_name()

        task_name = self._get_clean_task_name(raw_task_name)
        if project_name and task_name:
            details = self.data_manager.get_task_details(project_name, task_name)
            if details:
                self.ui.set_estimate(details["estimate"])
                completed_count = self.data_manager.get_completed_work_sessions_for_task(project_name, task_name)
                self.ui.update_progress(f"({completed_count} / {details['estimate']})")
                if details.get("sound"):
                    self.ui.set_sound_choice(details["sound"])

    def select_local_focus_item(self, item: dict) -> None:
        """Make a card the current task; starting remains an explicit action."""
        self.ui.project_var.set(item["project_name"])
        self.ui.task_var.set(item["task_name"])
        self.ui.set_estimate(item["estimate"])
        details = self.data_manager.get_task_details(item["project_name"], item["task_name"])
        if details and details.get("sound"):
            self.ui.set_sound_choice(details["sound"])
        self.ui.update_progress(f'({item["completed_count"]} / {item["estimate"]})')
        self.current_project = item["project_name"]
        self.current_task = item["task_name"]
        self.current_task_estimate = item["estimate"]
        self.current_focus_source = item.get("source", "local")
        self.current_goalsifter_task_id = (
            item.get("goalsifter_task_id") if self.current_focus_source == "goalsifter" else None
        )

    def complete_goalsifter_focus_item(self, item: dict) -> None:
        """Select a remote DW card and ask for explicit completion."""
        self.select_local_focus_item(item)
        self.mark_current_task_complete()

    def _complete_current_goalsifter_task(self) -> None:
        task_id = self.current_goalsifter_task_id
        if not task_id:
            messagebox.showerror("完成失败", "当前 GoalSifter DW 缺少 task_id。")
            return
        if self.is_running:
            self.abort_session(is_completing=True)
        try:
            self.goalsifter_client.complete_dw_task(task_id)
        except GoalSifterRemoteError as error:
            messagebox.showerror("完成失败", f"GoalSifter 拒绝完成该 DW：{error}")
            return
        self.refresh_goalsifter_tasks()
        self.reset_state_and_ui()

    def _on_goalsifter_window_focus(self, _event=None) -> None:
        """Refresh remote DW state when the app returns to the foreground."""
        if _event is not None and getattr(_event, "widget", self.root) is not self.root:
            return
        if not self.goalsifter_settings.is_configured:
            return
        if self._goalsifter_focus_refresh_job is not None:
            try:
                self.root.after_cancel(self._goalsifter_focus_refresh_job)
            except Exception:
                pass
        self._goalsifter_focus_refresh_job = self.root.after(
            250, self._run_debounced_goalsifter_focus_refresh
        )

    def _run_debounced_goalsifter_focus_refresh(self) -> None:
        self._goalsifter_focus_refresh_job = None
        self.refresh_goalsifter_tasks()

    def _schedule_goalsifter_periodic_refresh(self) -> None:
        self.root.after(30000, self._run_goalsifter_periodic_refresh)

    def _run_goalsifter_periodic_refresh(self) -> None:
        if self.goalsifter_settings.is_configured:
            self.refresh_goalsifter_tasks()
        self._schedule_goalsifter_periodic_refresh()

    def _maybe_auto_connect_goalsifter(self) -> None:
        """Refresh tasks after local startup without starting Outbox network work."""
        if self.goalsifter_settings.is_configured:
            if self.goalsifter_settings.auto_connect:
                self.refresh_goalsifter_tasks()

    def _submit_goalsifter_operation(self, operation, on_success, on_failure) -> None:
        """Run one remote operation off the Tk thread and marshal its result back."""
        def run() -> None:
            try:
                if self.goalsifter_tunnel is None or self.goalsifter_tunnel.poll() is not None:
                    self.goalsifter_tunnel = self.goalsifter_client.start_tunnel()
                for _ in range(20):
                    if self.goalsifter_client.is_tunnel_ready():
                        result = operation()
                        self.root.after(0, lambda result=result: on_success(result))
                        return
                    if self.goalsifter_tunnel.poll() is not None:
                        break
                    time.sleep(0.25)
                raise GoalSifterRemoteError(0, "GoalSifter 隧道连接超时")
            except Exception as error:
                self.root.after(0, lambda error=error: on_failure(error))

        try:
            self._goalsifter_executor.submit(run)
        except Exception as error:
            on_failure(error)

    def open_goalsifter_settings(self) -> None:
        """Edit and persist the GoalSifter connection without hand-editing JSON."""
        s = self.goalsifter_settings
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("GoalSifter 连接设置")
        dialog.geometry("440x380")
        dialog.transient(self.root)
        try:
            dialog.grab_set()
        except Exception:
            pass

        head = {"padx": 16, "pady": (10, 0)}
        ctk.CTkLabel(dialog, text="SSH Host 别名（在 ~/.ssh/config 中定义）",
                     anchor="w").pack(fill="x", **head)
        alias_var = StringVar(value=s.ssh_host_alias)
        ctk.CTkEntry(dialog, textvariable=alias_var).pack(fill="x", padx=16)

        ctk.CTkLabel(dialog, text="Bearer Token", anchor="w").pack(fill="x", **head)
        token_var = StringVar(value=s.bearer_token)
        token_entry = ctk.CTkEntry(dialog, textvariable=token_var, show="*")
        token_entry.pack(fill="x", padx=16)
        show_var = BooleanVar(value=False)
        ctk.CTkCheckBox(
            dialog, text="显示 Token", variable=show_var,
            command=lambda: token_entry.configure(show="" if show_var.get() else "*"),
        ).pack(anchor="w", padx=16, pady=(4, 0))

        ctk.CTkLabel(dialog, text="本地端口", anchor="w").pack(fill="x", **head)
        port_var = StringVar(value=str(s.local_port))
        ctk.CTkEntry(dialog, textvariable=port_var, width=120).pack(anchor="w", padx=16)

        auto_var = BooleanVar(value=s.auto_connect)
        ctk.CTkCheckBox(dialog, text="启动时自动连接并刷新 GoalSifter 任务",
                        variable=auto_var).pack(anchor="w", padx=16, pady=(12, 0))

        status = ctk.CTkLabel(dialog, text="", anchor="w", justify="left",
                              font=(FONT_NAME, 11), wraplength=400)
        status.pack(fill="x", padx=16, pady=(8, 0))

        def _apply() -> bool:
            try:
                port = int(port_var.get().strip())
                if not (1 <= port <= 65535):
                    raise ValueError
            except ValueError:
                status.configure(text="端口必须是 1–65535 之间的整数。")
                return False
            s.update_connection(
                self.paths,
                ssh_host_alias=alias_var.get(),
                bearer_token=token_var.get(),
                local_port=port,
                auto_connect=auto_var.get(),
            )
            # A changed alias/port invalidates any live tunnel; drop it so the
            # next connect re-establishes with the new settings.
            if self.goalsifter_tunnel is not None:
                try:
                    self.goalsifter_tunnel.terminate()
                except Exception:
                    pass
                self.goalsifter_tunnel = None
            return True

        def _save() -> None:
            if _apply():
                dialog.destroy()

        def _save_and_test() -> None:
            if _apply():
                dialog.destroy()
                self.refresh_goalsifter_tasks()

        buttons = ctk.CTkFrame(dialog, fg_color="transparent")
        buttons.pack(fill="x", padx=16, pady=16, side="bottom")
        ctk.CTkButton(buttons, text="保存", width=90, command=_save).pack(side="right")
        ctk.CTkButton(buttons, text="保存并测试连接", width=150,
                      command=_save_and_test).pack(side="right", padx=(0, 8))

    def _await_goalsifter_ready(self, on_ready, on_timeout, attempts: int = 20) -> None:
        """Poll the tunnel port on the Tk loop (non-blocking) until it accepts connections.

        Fires on_ready() as soon as the forwarded port is listening; on_timeout(msg) if the
        ssh process died early or the port never came up within ~5s. Replaces the old blind
        350ms wait that raced SSH establishment and surfaced WinError 10061.
        """
        if self.goalsifter_client.is_tunnel_ready():
            on_ready()
            return
        if self.goalsifter_tunnel is not None and self.goalsifter_tunnel.poll() is not None:
            on_timeout(self.goalsifter_client.tunnel_failure_message(self.goalsifter_tunnel) or
                       "SSH 隧道进程已退出，请在「连接设置」重试。")
            return
        if attempts <= 0:
            on_timeout("GoalSifter 隧道连接超时；SSH 可能仍在建立或配置有误，请稍后重试。")
            return
        self.root.after(250, lambda: self._await_goalsifter_ready(on_ready, on_timeout, attempts - 1))

    def refresh_goalsifter_tasks(self) -> None:
        """Fetch active DWs only after an explicit user refresh request."""
        if getattr(self, '_goalsifter_refresh_in_flight', False):
            return
        if not self.goalsifter_settings.is_configured:
            self.ui.refresh_goalsifter_focus_items(
                [], "GoalSifter 尚未配置 SSH alias 与 Bearer token。"
            )
            return
        self._goalsifter_refresh_in_flight = True

        def on_error(error: Exception) -> None:
            self._goalsifter_refresh_in_flight = False
            self.ui.refresh_goalsifter_focus_items([], f"GoalSifter 不可用：{error}")

        try:
            cached_items = self.data_manager.get_goalsifter_focus_items()
        except Exception as error:
            self._goalsifter_refresh_in_flight = False
            self.ui.refresh_goalsifter_focus_items([], f"GoalSifter 不可用：{error}")
            return
        self.ui.refresh_goalsifter_focus_items(cached_items, "正在连接 GoalSifter…")
        self._submit_goalsifter_operation(
            self.goalsifter_client.get_active_dw_tasks,
            self._load_goalsifter_tasks,
            on_error,
        )

    def _load_goalsifter_tasks(self, tasks=None) -> None:
        try:
            if tasks is None:
                tasks = self.goalsifter_client.get_active_dw_tasks()
            self.data_manager.reconcile_goalsifter_focus_items({task.task_id for task in tasks})
            for task in tasks:
                self.data_manager.upsert_goalsifter_focus_item(task.__dict__)
            self.ui.refresh_goalsifter_focus_items(
                self.data_manager.get_goalsifter_focus_items(), "已加载活跃 DW。"
            )
            self.update_db_status()
            self._goalsifter_refresh_in_flight = False
        except Exception as error:
            self._goalsifter_refresh_in_flight = False
            self.ui.refresh_goalsifter_focus_items([], f"GoalSifter 不可用：{error}")

    def sync_goalsifter_outbox(self) -> None:
        """Upload queued immutable events with durable retry semantics."""
        if getattr(self, '_goalsifter_sync_in_flight', False):
            return
        if not self.goalsifter_settings.is_configured:
            self.ui.refresh_goalsifter_focus_items([], "GoalSifter 尚未配置 SSH alias 与 Bearer token。")
            return
        if not self.data_manager.get_pending_focusflow_events():
            return
        self._goalsifter_sync_in_flight = True

        def on_failure(error: Exception) -> None:
            self._goalsifter_sync_in_flight = False
            self.ui.refresh_goalsifter_focus_items([], f"无法同步 Outbox：{error}")
            self._schedule_goalsifter_retry()

        self.ui.refresh_goalsifter_focus_items(
            self.data_manager.get_goalsifter_focus_items(), "正在连接 GoalSifter 并同步 Outbox…"
        )
        pending_events = self.data_manager.get_pending_focusflow_events()
        self._submit_goalsifter_operation(
            lambda: self._sync_pending_goalsifter_events(pending_events),
            self._finish_goalsifter_outbox_sync,
            on_failure,
        )

    def _finish_goalsifter_outbox_sync(self, result: dict) -> None:
        """Apply worker-produced Outbox results on the Tk/database thread."""
        synced_events = result.get("synced", [])
        for event in synced_events:
            self.data_manager.mark_focusflow_event_synced(event["event_id"])

        failure = result.get("failure")
        if failure is not None:
            event = result["failed_event"]
            error = failure["error"]
            if failure["conflict"]:
                self.data_manager.mark_focusflow_event_conflict(event["event_id"], str(error))
                self._goalsifter_sync_in_flight = False
                self.ui.refresh_goalsifter_focus_items(
                    self.data_manager.get_goalsifter_focus_items(),
                    f"已同步 {len(synced_events)} 条；发现事件冲突，已暂停该事件：{error}",
                )
                return
            self.data_manager.record_focusflow_event_error(event["event_id"], str(error))
            self._goalsifter_sync_in_flight = False
            self.ui.refresh_goalsifter_focus_items(
                self.data_manager.get_goalsifter_focus_items(),
                f"已同步 {len(synced_events)} 条；其余保留待同步：{error}",
            )
            self._schedule_goalsifter_retry()
            return

        self._goalsifter_sync_in_flight = False
        self._goalsifter_retry_delay = 1
        self.ui.refresh_goalsifter_focus_items(
            self.data_manager.get_goalsifter_focus_items(),
            f"已同步 {len(synced_events)} 条 Outbox 事件。",
        )

    def _schedule_goalsifter_retry(self) -> None:
        """Retry transient delivery failures without blocking the Tk event loop."""
        if getattr(self, '_goalsifter_retry_job', None) is not None:
            return
        delay = getattr(self, '_goalsifter_retry_delay', 1)
        self._goalsifter_retry_delay = min(delay * 2, 60)
        self._goalsifter_retry_job = self.root.after(
            delay * 1000, self._run_goalsifter_retry
        )

    def _run_goalsifter_retry(self) -> None:
        self._goalsifter_retry_job = None
        self.sync_goalsifter_outbox()

    def bind_current_focus_item(self) -> None:
        """Explicitly bind the selected local item to a known remote DW id."""
        if not self.current_project or not self.current_task:
            messagebox.showinfo("选择本地任务", "请先在“本地任务”中单击一个任务卡。")
            return
        if self.current_focus_source != "local":
            messagebox.showinfo("仅限本地任务", "远端 DW 已绑定；请在 GoalSifter 中管理它。")
            return
        if self.current_task_estimate > 4:
            messagebox.showwarning("需要拆分", "本地预估超过 4 个番茄。请拆成多个 DW 后分别绑定。")
            return
        task_id = simpledialog.askstring("绑定已有 DW", "输入 GoalSifter DW 的 task_id：", parent=self.root)
        if not task_id:
            return
        item = self.data_manager.ensure_focus_item(self.current_project, self.current_task)
        self.data_manager.bind_focus_item(item['local_id'], task_id.strip(), self.goalsifter_settings.device_id)
        self.reset_state_and_ui()
        messagebox.showinfo("已绑定", "本地任务已绑定；已完成的历史番茄已进入 Outbox，需由你手动同步。")

    def create_and_bind_current_focus_item(self) -> None:
        """Create a DW through the locked API, then explicitly bind the local item."""
        if not self.current_project or not self.current_task:
            messagebox.showinfo("选择本地任务", "请先在“本地任务”中单击一个任务卡。")
            return
        if self.current_focus_source != "local":
            messagebox.showinfo("仅限本地任务", "远端 DW 已绑定；请在 GoalSifter 中管理它。")
            return
        if self.current_task_estimate > 4:
            messagebox.showwarning("需要拆分", "本地预估超过 4 个番茄。请拆成多个 DW 后分别绑定。")
            return
        if not self.goalsifter_settings.is_configured:
            messagebox.showwarning("GoalSifter 未配置", "请先配置 SSH alias 与 Bearer token。")
            return
        project_name = self.current_project
        task_name = self.current_task
        estimate = self.current_task_estimate
        device_id = self.goalsifter_settings.device_id

        def create_remote_task():
            return self.goalsifter_client.create_dw_task(task_name, estimate)

        def on_created(result: dict) -> None:
            try:
                item = self.data_manager.ensure_focus_item(project_name, task_name)
                self.data_manager.bind_focus_item(
                    item['local_id'], result['task_id'], device_id
                )
                self.reset_state_and_ui()
                messagebox.showinfo("已创建并绑定", "新 DW 已创建；历史番茄需要由你手动同步。")
            except Exception as error:
                messagebox.showerror("绑定失败", f"本地绑定失败：{error}")

        def on_failed(error: Exception) -> None:
            if isinstance(error, GoalSifterRemoteError) and error.status_code == 422:
                messagebox.showwarning("需要澄清", "GoalSifter 拒绝创建该任务，请回 TTC/GoalSifter 完成澄清后再绑定。")
            else:
                messagebox.showerror("创建失败", f"GoalSifter 不可用：{error}")

        self._submit_goalsifter_operation(create_remote_task, on_created, on_failed)

    def _sync_pending_goalsifter_events(self, pending_events: list[dict]) -> dict:
        """Send Outbox events in the worker and return only serializable results."""
        synced = []
        for event in pending_events:
            try:
                result = self.goalsifter_client.post_pomo_event(event)
                if result.get('event_id') != event['event_id'] or 'duplicate' not in result:
                    raise GoalSifterRemoteError(502, "GoalSifter returned an invalid event acknowledgement")
                synced.append(event)
            except GoalSifterRemoteError as error:
                return {
                    "synced": synced,
                    "failed_event": event,
                    "failure": {"error": error, "conflict": error.status_code == 409},
                }
        return {"synced": synced, "failure": None}

    def show_local_task_manager(self) -> None:
        """Manage local projects and their tasks without touching GoalSifter KR data."""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("管理本地任务")
        dialog.geometry("760x560")
        dialog.transient(self.root)
        toolbar = ctk.CTkFrame(dialog)
        toolbar.pack(fill="x", padx=12, pady=(12, 6))
        project_var = ctk.StringVar()
        project_picker = ctk.CTkComboBox(toolbar, variable=project_var, width=260)
        project_picker.pack(side="left", padx=6, pady=8)
        task_body = ctk.CTkScrollableFrame(dialog)
        task_body.pack(fill="both", expand=True, padx=12, pady=(6, 12))

        def refresh_tasks(_choice=None):
            for widget in task_body.winfo_children():
                widget.destroy()
            project = project_var.get().strip()
            ctk.CTkLabel(task_body, text=project or "请选择本地 Project", font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(0, 8))
            if not project:
                return
            active = [item for item in self.data_manager.get_local_focus_items() if item['project_name'] == project]
            archived = [item for item in self.data_manager.get_archived_local_focus_items() if item['project_name'] == project]
            ctk.CTkLabel(task_body, text="活跃任务", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 4))
            for item in active:
                row = ctk.CTkFrame(task_body)
                row.pack(fill="x", pady=3)
                ctk.CTkLabel(row, text=f'{item["task_name"]}  ·  {item["completed_count"]}/{item["estimate"]}', justify="left").pack(side="left", fill="x", expand=True, padx=8, pady=6)
                ctk.CTkButton(row, text="归档", width=70, command=lambda value=item: archive(value)).pack(side="right", padx=6)
            ctk.CTkLabel(task_body, text="已归档", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(16, 4))
            for item in archived:
                row = ctk.CTkFrame(task_body)
                row.pack(fill="x", pady=3)
                ctk.CTkLabel(row, text=f'{item["task_name"]}  ·  预估 {item["estimate"]}', justify="left").pack(side="left", fill="x", expand=True, padx=8, pady=6)
                ctk.CTkButton(row, text="恢复", width=70, command=lambda value=item: restore(value)).pack(side="right", padx=6)

        def refresh_projects(select=None):
            values = [row['project_name'] for row in self.data_manager.get_local_project_summaries()]
            project_picker.configure(values=values)
            chosen = select if select in values else (values[0] if values else "")
            project_var.set(chosen)
            refresh_tasks()

        def rename_project():
            source = project_var.get().strip()
            target = simpledialog.askstring("重命名 Project", "新的本地分类名称：", initialvalue=source, parent=dialog)
            if not target or target.strip() == source:
                return
            try:
                self.data_manager.rename_local_project(source, target.strip())
                self.reset_state_and_ui()
                refresh_projects(target.strip())
            except ValueError as error:
                messagebox.showwarning("无法重命名", str(error), parent=dialog)

        def merge_project():
            selected = project_var.get().strip()
            raw_sources = simpledialog.askstring(
                "合并 Project", "要合并的来源分类（多个名称用英文逗号分隔）：",
                initialvalue=selected, parent=dialog,
            )
            if not raw_sources:
                return
            sources = [name.strip() for name in raw_sources.split(',') if name.strip()]
            target = simpledialog.askstring("合并 Project", "合并到哪个本地分类（可输入新名称）：", parent=dialog)
            if not target:
                return
            try:
                self.data_manager.merge_local_projects(sources, target.strip())
                self.reset_state_and_ui()
                refresh_projects(target.strip())
            except (ValueError, sqlite3.IntegrityError) as error:
                messagebox.showwarning("存在冲突", str(error), parent=dialog)

        def delete_empty_project():
            project = project_var.get().strip()
            if not project or not messagebox.askyesno("删除空 Project", f"删除空分类“{project}”？", parent=dialog):
                return
            try:
                self.data_manager.delete_empty_local_project(project)
                self.reset_state_and_ui()
                refresh_projects()
            except ValueError as error:
                messagebox.showwarning("无法删除", str(error), parent=dialog)

        def archive(item):
            self.data_manager.archive_local_focus_item(item['project_name'], item['task_name'])
            self.reset_state_and_ui()
            refresh_tasks()

        def restore(item):
            self.data_manager.restore_local_focus_item(item['project_name'], item['task_name'])
            self.reset_state_and_ui()
            refresh_tasks()

        project_picker.configure(command=refresh_tasks)
        ctk.CTkButton(toolbar, text="重命名", width=80, command=rename_project).pack(side="left", padx=3)
        ctk.CTkButton(toolbar, text="合并到…", width=80, command=merge_project).pack(side="left", padx=3)
        ctk.CTkButton(toolbar, text="删除空分类", width=95, command=delete_empty_project).pack(side="left", padx=3)
        refresh_projects()

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
                self._shutdown_goalsifter_worker()
                self.data_manager.close()
                self.root.destroy()
        else:
            self._shutdown_goalsifter_worker()
            self.data_manager.close()
            self.root.destroy()

    def _shutdown_goalsifter_worker(self) -> None:
        executor = getattr(self, "_goalsifter_executor", None)
        if executor is not None:
            executor.shutdown(wait=False, cancel_futures=True)

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

        selected_details = None
        selected_estimate = None
        if self.current_session_type == 'Work':
            selected_details = self.data_manager.get_task_details(project_name, task_name)
            try:
                selected_estimate = selected_details['estimate'] if selected_details else self.ui.get_estimate()
            except ValueError:
                messagebox.showwarning("Estimate Required", "Please use an estimate between 1 and 4. Split larger tasks first.")
                return
        
        self.is_running = True
        self.ui.toggle_action_button(is_running=True)
        self.ui.toggle_secondary_button(is_running=True)
        self.ui.show_timer_view()
        
        from focusflow.ctk_theme_config import ThemeManager
        pygame_bg = ThemeManager.get_color("bg")
        if hasattr(self.ui, 'pygame_widget'):
            self.ui.pygame_widget.set_background_color(pygame_bg)
            self.ui.pygame_widget.update_display()
        
        if self.current_session_type == 'Work':
            self.root.attributes('-alpha', self.preferences["focused_transparency"])
            self.current_project, self.current_task = project_name, task_name
            self.current_task_estimate = selected_estimate
            
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
        self.ui.toggle_action_button(is_running=False)
        self.ui.toggle_secondary_button(is_running=False)
        self.root.attributes('-alpha', 1.0)

        local_projects = self.data_manager.get_local_project_names()
        local_focus_items = self.data_manager.get_local_focus_items()
        self.ui.refresh_local_focus_items(local_focus_items)
        self.ui.task_source_tabs.set("本地任务")
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
        self.current_goalsifter_task_id = None
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
        self.ui.update_timer_display(f"{self.preferences['work_minutes']:02d}:00")

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
            feedback_interval = self.preferences["feedback_interval"]
            if completed_count == 0 or (feedback_interval > 0 and (completed_count + 1) % feedback_interval == 0):
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
                'status': status, 'interruption_reason': interruption_reason,
                'device_id': self.goalsifter_settings.device_id, **feedback
            }
            self.data_manager.record_session(session_data)
            self.update_db_status()

    def _handle_session_finish(self, session_type: str, duration: int, status: str) -> None:
        """Handles session completion, including transition to breaks and sound alerts."""
        self.is_running = False
        self.sound_manager.play_end_sound()
        
        if session_type == 'Work':
            self._get_and_record_feedback(self.timer.start_time, duration, status)
            self.root.after(0, self._sync_goalsifter_after_work)
            self.update_progress_display()
            
            if self.preferences["reset_long_break_on_restart"]:
                key = (self.current_project, self.current_task)
                self.local_session_counts[key] = self.local_session_counts.get(key, 0) + 1
                completed_count = self.local_session_counts[key]
            else:
                completed_count = self.data_manager.get_completed_work_sessions_for_task(self.current_project, self.current_task)
            
            interval = self.preferences["long_break_interval"]
            self.current_session_type = 'Long Break' if completed_count > 0 and completed_count % interval == 0 else 'Short Break'
            self.start_session(project_name=self.current_project, task_name=self.current_task)
        else: 
            self.data_manager.record_session({
                'project_name': self.current_project, 'task_name': self.current_task,
                'session_type': session_type, 'start_time': self.timer.start_time,
                'end_time': datetime.now(), 'duration_minutes': duration, 'status': status,
                'device_id': self.goalsifter_settings.device_id,
            })
            self.update_db_status()
            self._setup_next_work_session()

    def _sync_goalsifter_after_work(self) -> None:
        """Start a retryable remote sync after completing a bound DW session."""
        if self.current_focus_source == "goalsifter":
            self.sync_goalsifter_outbox()

def main() -> None:
    """Entry point: create the root window and run the application."""
    window = ctk.CTk()
    PomodoroApp(window)
    window.mainloop()


if __name__ == "__main__":
    main()
