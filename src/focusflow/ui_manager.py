# ui_manager.py - FocusFlow 3.0
import os
import platform
import random
import tkinter as tk
import pygame
import customtkinter as ctk
from tkinter import StringVar, Menu  # Keep StringVar and Menu from tkinter
from focusflow.config import *
from focusflow.ctk_theme_config import ThemeManager
from datetime import datetime, timedelta
import math

from focusflow.visual_effects import BlackHoleEffect, ZenFocusEffect
from focusflow.game_progress_bar import GameFocusBar


def calculate_home_size(requested_width, requested_height, screen_width, screen_height):
    """Fit the home window to its content while leaving OS chrome/taskbar room."""
    return (
        min(int(requested_width), int(screen_width * 0.9)),
        min(int(requested_height), int(screen_height * 0.9)),
    )


def parse_focus_estimate(raw: str) -> int:
    """Parse the local-first estimate contract shared with GoalSifter."""
    try:
        estimate = int(raw.strip())
    except (AttributeError, ValueError):
        raise ValueError("Focus item estimate must be between 1 and 99") from None
    if not 1 <= estimate <= 99:
        raise ValueError("Focus item estimate must be between 1 and 99")
    return estimate

# --- Pygame Widget (Refactored) ---
class PygameTimerWidget(tk.Frame):
    """只负责视觉效果 (Delegates rendering to Effect Classes)"""
    def __init__(self, parent, width=260, height=200, bg_color=BG_COLOR, **kwargs):
        super().__init__(parent, width=width, height=height, bg=bg_color, borderwidth=0, relief='flat', **kwargs)
        self.width = width
        self.height = height
        self.bg_color = bg_color 
        self.time_text = "00:00"
        
        # 1. 嵌入 Frame
        self.embed_frame = tk.Frame(self, width=width, height=height, bg=bg_color, borderwidth=0, relief='flat')
        self.embed_frame.pack(fill="both", expand=True)
        self.update_idletasks()
        try:
            window_id = self.embed_frame.winfo_id()
            os.environ['SDL_WINDOWID'] = str(window_id)
        except Exception as e: print(f"Embedding setup failed: {e}")

        # Subscribe to theme changes
        from focusflow.ctk_theme_config import ThemeManager
        ThemeManager.subscribe(self._on_theme_changed)

        # 2. Init Pygame
        try:
            if not pygame.get_init():
                pygame.init() 
                pygame.font.init()
            self.screen = pygame.display.set_mode((width, height))
        except Exception as e:
            print(f"Pygame display init failed: {e}")
            return
            
        # 3. Init Effect based on current theme
        self.clock = pygame.time.Clock()
        self.effect = None
        self._init_effect()
            
        self.mode = "Work"
        self.running = True
        self.render_loop()

    def _init_effect(self):
        """Initialize or switch effect based on global theme"""
        from focusflow.ctk_theme_config import ThemeManager
        current_mode = ThemeManager.get_mode()
        current_bg = ThemeManager.get_color("bg")
        
        if current_mode == "light":
            self.effect = ZenFocusEffect(self.width, self.height, current_bg)
        else:
            self.effect = BlackHoleEffect(self.width, self.height, current_bg)
            
        print(f"✨ Visual Effect initialized: {type(self.effect).__name__}")

    def update_text(self, text):
        self.time_text = text
    
    def update_display(self):
        """Force refresh"""
        pass

    def set_background_color(self, color):
        """Dynamically update background color"""
        self.bg_color = color
        self.configure(bg=color)
        self.embed_frame.configure(bg=color)
        
        # Also update the effect's knowledge of BG
        if self.effect:
            self.effect.set_bg_color(color)
    
    def _on_theme_changed(self):
        """Called when theme toggles"""
        from focusflow.ctk_theme_config import ThemeManager
        new_bg = ThemeManager.get_color("bg")
        self.set_background_color(new_bg)
        
        # Switch Strategy: Re-init effect entirely to swap classes if needed
        self._init_effect()
        
    def set_mode(self, mode):
        self.mode = mode

    def render_loop(self):
        if not self.running: return

        # Update Logic
        if self.effect and self.mode == "Work":
            self.effect.update()
        
        # Draw Logic
        if self.effect:
            try:
                if self.mode == "Work":
                    self.effect.draw(self.screen, self.time_text)
                else:
                    self.effect.draw_minimal(self.screen, self.time_text)
            except Exception as e:
                print(f"Render error: {e}")
        else:
            self.screen.fill((0,0,0))
            
        pygame.display.flip()
        self.after(20, self.render_loop)

# --- Date Selection Dialog ---
class DateRangeDialog(ctk.CTkToplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.title("Analysis Period")
        self.geometry("320x350")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self.mode_var = StringVar(value="30d")
        
        # UI Setup
        self._create_widgets()
        
        # Center the window
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        pad_opts = {'padx': 20, 'pady': 5}
        
        lbl = ctk.CTkLabel(self, text="Select Data Range", font=(FONT_NAME, 14, "bold"))
        lbl.pack(pady=15)
        
        # Radio Buttons - CustomTkinter style
        self.r_30 = ctk.CTkRadioButton(self, text="Last 30 Days (Default)", 
                                       variable=self.mode_var, value="30d", 
                                       command=self._toggle_custom)
        self.r_30.pack(anchor="w", **pad_opts)
        
        self.r_month = ctk.CTkRadioButton(self, text="This Month", 
                                           variable=self.mode_var, value="month", 
                                           command=self._toggle_custom)
        self.r_month.pack(anchor="w", **pad_opts)

        self.r_all = ctk.CTkRadioButton(self, text="All Time", 
                                         variable=self.mode_var, value="all", 
                                         command=self._toggle_custom)
        self.r_all.pack(anchor="w", **pad_opts)

        self.r_custom = ctk.CTkRadioButton(self, text="Custom Range (YYYY-MM-DD)", 
                                            variable=self.mode_var, value="custom", 
                                            command=self._toggle_custom)
        self.r_custom.pack(anchor="w", **pad_opts)
        
        # Custom Date Inputs
        self.custom_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.custom_frame.pack(fill="x", padx=40, pady=10)
        
        ctk.CTkLabel(self.custom_frame, text="Start:").grid(row=0, column=0, padx=5)
        self.start_entry = ctk.CTkEntry(self.custom_frame, width=100)
        self.start_entry.grid(row=0, column=1, padx=5)
        self.start_entry.insert(0, (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"))
        
        ctk.CTkLabel(self.custom_frame, text="End:").grid(row=0, column=2, padx=5)
        self.end_entry = ctk.CTkEntry(self.custom_frame, width=100)
        self.end_entry.grid(row=0, column=3, padx=5)
        self.end_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        self._toggle_custom() # Init state

        # Generate Button
        btn = ctk.CTkButton(self, text="Generate Report", width=150, height=40, 
                            command=self._on_confirm, 
                            fg_color=ACCENT_COLOR, hover_color=BUTTON_HOVER)
        btn.pack(side="bottom", pady=20)

    def _toggle_custom(self):
        if self.mode_var.get() == "custom":
            self.start_entry.configure(state="normal")
            self.end_entry.configure(state="normal")
        else:
            self.start_entry.configure(state="disabled")
            self.end_entry.configure(state="disabled")

    def _on_confirm(self):
        mode = self.mode_var.get()
        start = None
        end = datetime.now()
        
        try:
            if mode == "30d":
                start = end - timedelta(days=30)
            elif mode == "month":
                start = end.replace(day=1)
            elif mode == "all":
                start = None
                end = None
            elif mode == "custom":
                s_str = self.start_entry.get().strip()
                e_str = self.end_entry.get().strip()
                start = datetime.strptime(s_str, "%Y-%m-%d")
                end = datetime.strptime(e_str, "%Y-%m-%d")
                # Include the full end day
                end = end.replace(hour=23, minute=59, second=59)

            self.destroy()
            self.callback(start, end)
            
        except ValueError:
            from tkinter import messagebox
            messagebox.showerror("Invalid Date", "Please use YYYY-MM-DD format.")

# --- UI Manager ---
class UIManager:
    def __init__(self, root: ctk.CTk, action_command, secondary_action_command, analysis_command,
                 quick_start_command, load_backup_command, merge_db_command,
                 sound_switch_callback,
                 delete_project_callback,
                 delete_task_callback,
                 home_callback,
                 theme_toggle_callback,
                 focus_item_select_callback,
                 goalsifter_refresh_callback,
                 goalsifter_sync_callback,
                 goalsifter_bind_callback,
                 goalsifter_create_callback,
                 goalsifter_settings_callback,
                 goalsifter_complete_callback,
                 local_manage_callback,
                 image_dir, all_projects: list, sound_manager=None):
        self.root = root
        self.action_command = action_command
        self.secondary_action_command = secondary_action_command
        self.analysis_command = analysis_command
        self.quick_start_command = quick_start_command
        self.load_backup_command = load_backup_command
        self.merge_db_command = merge_db_command
        self.sound_switch_callback = sound_switch_callback
        self.delete_project_callback = delete_project_callback
        self.delete_task_callback = delete_task_callback
        self.home_callback = home_callback
        self.theme_toggle_callback = theme_toggle_callback
        self.focus_item_select_callback = focus_item_select_callback
        self.goalsifter_refresh_callback = goalsifter_refresh_callback
        self.goalsifter_sync_callback = goalsifter_sync_callback
        self.goalsifter_bind_callback = goalsifter_bind_callback
        self.goalsifter_create_callback = goalsifter_create_callback
        self.goalsifter_settings_callback = goalsifter_settings_callback
        self.goalsifter_complete_callback = goalsifter_complete_callback
        self.local_manage_callback = local_manage_callback
        self.image_dir = image_dir
        self.all_projects = all_projects
        self.sound_manager = sound_manager  # Store reference
        
        self.sound_manager = sound_manager  # Store reference
        
        # Subscribe to Theme Changes
        ThemeManager.subscribe(self._on_theme_change)
        
        self._setup_window()
        self._setup_frames()
        self._create_widgets()
        self._bind_events()
        
        # Initial Theme Apply (to ensure correct initial state)
        self._on_theme_change()
        
        self.show_setup_view()

    def _setup_window(self):
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self.root.geometry(HOME_WINDOW_GEOMETRY)
        self.root.resizable(True, True)
        # CustomTkinter handles styling automatically via theme

    def _on_theme_change(self):
        """Handle dynamic theme updates for widgets that need manual refreshment"""
        mode = ThemeManager.get_mode()
        
        # 1. Update ComboBox Colors
        # Need to manually set dropdown colors because ctk doesn't auto-update these deeply
        dropdown_fg = ThemeManager.get_color("card_bg")
        text_color = ThemeManager.get_color("fg")
        input_bg = ThemeManager.get_color("bg") # Use main BG for input field contrast against Card BG
        
        # Project Combobox
        if hasattr(self, 'project_combobox'):
            self.project_combobox.configure(
                fg_color=input_bg,
                dropdown_fg_color=dropdown_fg,
                text_color=text_color,
                dropdown_text_color=text_color
            )
            
        # Task Combobox
        if hasattr(self, 'task_combobox'):
            self.task_combobox.configure(
                fg_color=input_bg,
                dropdown_fg_color=dropdown_fg,
                text_color=text_color,
                dropdown_text_color=text_color
            )
            
        # 2. Update Transparent Buttons / Icons for Contrast
        # In Light mode, white icons on transparent bg (over light window) are invisible.
        # So we force dark text/icons in Light mode, and white in Dark mode.
        icon_color = "#212529" if mode == "light" else "#FFFFFF"
        
        if hasattr(self, 'theme_btn'):
            self.theme_btn.configure(text_color=icon_color)
            
        # 3. Update Input Card Background (Fix for "Black Box" in Light Mode)
        if hasattr(self, 'input_card'):
            self.input_card.configure(
                fg_color=ThemeManager.get_color("card_bg"),
                border_color=ThemeManager.get_color("accent")
            )
            
        # 4. Update Game Progress Bar (Canvas needs manual redraw)
        if hasattr(self, 'session_progress_bar'):
            self.session_progress_bar.update_view()
            
        # Update Status Bar Buttons (Backup/Merge)
        # They are transparent, so they need contrast against the background
        status_btn_color = "#666666" if mode == "light" else "#888888"
        # Since these are created in _create_widgets and not stored as self.xxx, 
        # we might need to store them or iterate children if we want to update them.
        # For significantly better code, let's just make them attributes if we need to update them,
        # OR just set a neutral gray that works on both (like #666666 or #888888 usually works ok).
        # But per user request "Light Mode Icon Contrast", let's be safe.
        # We will iterate specific frames if needed, or rely on the fact that #888888 is visible on #EBEBEB.
        # User specifically mentioned "Theme Toggle Icon" (切换功能的ICON).


    def _setup_frames(self):
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self.main_container = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_container.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.timer_view_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.setup_view_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.controls_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.controls_frame.grid(row=1, column=0, pady=(15, 0))
        self.daily_checkmarks_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.daily_checkmarks_frame.grid(row=2, column=0, pady=(2,0))
        self.status_bar_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.status_bar_frame.grid(row=3, column=0, pady=(2,0), sticky="ew")
        self.quick_start_frame = ctk.CTkFrame(self.setup_view_frame, fg_color="transparent")
        self.quick_start_frame.grid(row=6, column=0, columnspan=3, pady=(10,0))

    def _create_card_frame(self, parent):
        """Create a card-style container with CustomTkinter styling"""
        card = ctk.CTkFrame(parent, fg_color=ThemeManager.get_color("card_bg"), 
                           corner_radius=10, border_width=2, 
                           border_color=ThemeManager.get_color("accent"))
        # Inner content area
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)
        return card, inner

    def _create_widgets(self):
        # --- Timer View ---
        self.timer_label = ctk.CTkLabel(self.timer_view_frame, 
                                        font=(FONT_NAME, 26, "bold"))
        # Reduced top padding for tighter look
        self.timer_label.grid(row=0, column=0, pady=(PADDING_MEDIUM, PADDING_SMALL))
        
        
        # Pygame widget container - transparent to blend seamlessly with UI
        pygame_container = ctk.CTkFrame(self.timer_view_frame, 
                                       fg_color="transparent",
                                       corner_radius=0,
                                       border_width=0)
        pygame_container.grid(row=1, column=0, pady=PADDING_MEDIUM)
        
        self.pygame_widget = PygameTimerWidget(pygame_container, width=170, height=170,
                                              bg_color=ThemeManager.get_color("bg"))
        self.pygame_widget.pack(padx=0, pady=0)
        
        # Replaced Text Label with GameFocusBar
        self.session_progress_bar = GameFocusBar(self.timer_view_frame, width=220, height=20, target_val=1)
        # Increased bottom padding to separate from sound controls
        self.session_progress_bar.grid(row=2, column=0, pady=(4, PADDING_MEDIUM))
        
        # === Sound Control Bar ===
        audio_frame = ctk.CTkFrame(self.timer_view_frame, fg_color="transparent")
        audio_frame.grid(row=3, column=0, pady=(0, PADDING_MEDIUM))
        
        # ToolTip Class
        class ToolTip:
            def __init__(self, widget, text):
                self.widget = widget
                self.text = text
                self.tooltip_window = None
                self.widget.bind("<Enter>", self.show_tooltip)
                self.widget.bind("<Leave>", self.hide_tooltip)
            
            def show_tooltip(self, event=None):
                if self.tooltip_window: return
                x, y, _, _ = self.widget.bbox("insert")
                x += self.widget.winfo_rootx() + 25
                y += self.widget.winfo_rooty() + 25
                
                self.tooltip_window = tk.Toplevel(self.widget)
                self.tooltip_window.wm_overrideredirect(True)
                self.tooltip_window.wm_geometry(f"+{x}+{y}")
                
                label = tk.Label(self.tooltip_window, text=self.text, background="#ffffe0", relief="solid", borderwidth=1, font=("Arial", 9, "normal"))
                label.pack()
                
            def hide_tooltip(self, event=None):
                if self.tooltip_window:
                    self.tooltip_window.destroy()
                    self.tooltip_window = None

        # Icon-only buttons to save space
        def make_sound_btn(icon, mode, tooltip_text):
            btn = ctk.CTkButton(audio_frame, text=icon, 
                               font=(FONT_NAME, 14), 
                               width=45, height=28,
                               fg_color=BUTTON_COLOR, 
                               hover_color=BUTTON_HOVER,
                               command=lambda: self.sound_switch_callback(mode))
            ToolTip(btn, tooltip_text)
            return btn
        
        make_sound_btn("⏰", "dida", "Tick Sound").pack(side="left", padx=2)
        make_sound_btn("🎵", "music", "Music Playlist").pack(side="left", padx=2)
        
        # Mute is now a toggle pause/resume button
        self.mute_button = ctk.CTkButton(audio_frame, text="⏸️", 
                                        font=(FONT_NAME, 14), 
                                        width=45, height=28,
                                        fg_color=BUTTON_COLOR, 
                                        hover_color=BUTTON_HOVER,
                                        command=self.toggle_mute)
        self.mute_button.pack(side="left", padx=2)
        ToolTip(self.mute_button, "Pause/Resume")
        self.is_muted = False  # Track mute state
        
        # Home Button
        home_btn = ctk.CTkButton(audio_frame, text="🏠", 
                     font=(FONT_NAME, 14), 
                     width=45, height=28,
                     fg_color=BUTTON_COLOR, 
                     hover_color=BUTTON_HOVER,
                     command=self.home_callback)
        home_btn.pack(side="left", padx=10)
        ToolTip(home_btn, "Return Home (Task Switch)")

        # --- Setup View ---
        # Title
        ctk.CTkLabel(self.setup_view_frame, text=f"{APP_NAME} {APP_VERSION}", 
                    text_color=ThemeManager.get_color("danger"), 
                    font=("Segoe UI", 26, "bold")).grid(row=0, column=0, columnspan=3, pady=PADDING_LARGE)
        
        # Theme Toggle Button (Placed relatively to not mess up grid)
        self.theme_btn = ctk.CTkButton(self.setup_view_frame, text="🌗", 
                                      width=30, height=30,
                                      fg_color="transparent", 
                                      hover_color=BUTTON_HOVER,
                                      font=(FONT_NAME, 16),
                                      command=self._on_theme_toggle)
        self.theme_btn.place(relx=0.9, rely=0.0) # Top-right corner of the frame
        
        # Project/Task Input Card
        self.input_card, input_inner = self._create_card_frame(self.setup_view_frame)
        self.input_card.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, PADDING_MEDIUM))
        self.task_source_tabs = ctk.CTkTabview(input_inner, height=330)
        self.task_source_tabs.pack(fill="both", expand=True)
        editor_tab = self.task_source_tabs.add("本地任务")
        goalsifter_tab = self.task_source_tabs.add("GoalSifter 任务")
        self.local_focus_list = ctk.CTkScrollableFrame(editor_tab, fg_color="transparent", height=165)
        self.local_focus_list.grid(row=4, column=0, columnspan=3, sticky="nsew", pady=(PADDING_MEDIUM, 0))
        local_actions = ctk.CTkFrame(editor_tab, fg_color="transparent")
        local_actions.grid(row=5, column=0, columnspan=3, sticky="w", pady=(PADDING_SMALL, 0))
        ctk.CTkButton(local_actions, text="绑定已有 DW", width=100, height=26,
                      command=self.goalsifter_bind_callback).pack(side="left", padx=(0, 5))
        ctk.CTkButton(local_actions, text="创建并绑定 DW", width=110, height=26,
                      command=self.goalsifter_create_callback).pack(side="left")
        ctk.CTkButton(local_actions, text="管理本地任务", width=100, height=26,
                      command=self.local_manage_callback).pack(side="left", padx=(5, 0))
        self.goalsifter_focus_list = ctk.CTkScrollableFrame(goalsifter_tab, fg_color="transparent")
        self.goalsifter_focus_list.pack(fill="both", expand=True, padx=2, pady=2)
        self.goalsifter_status_label = ctk.CTkLabel(
            self.goalsifter_focus_list, text="仅显示活跃 DW。连接失败不会影响本地任务。",
            font=(FONT_NAME, 11), justify="left",
        )
        self.goalsifter_status_label.pack(anchor="w", pady=(2, 8))
        ctk.CTkButton(
            self.goalsifter_focus_list, text="刷新 GoalSifter 任务", height=28,
            command=self.goalsifter_refresh_callback,
        ).pack(anchor="w", pady=(0, 8))
        ctk.CTkButton(
            self.goalsifter_focus_list, text="手动同步 Outbox", height=28,
            command=self.goalsifter_sync_callback,
        ).pack(anchor="w", pady=(0, 8))
        ctk.CTkButton(
            self.goalsifter_focus_list, text="⚙ 连接设置", height=28,
            command=self.goalsifter_settings_callback,
        ).pack(anchor="w", pady=(0, 8))
        
        # Project section
        ctk.CTkLabel(editor_tab, text="本地分类（可选）:",
                    font=(FONT_NAME, 11, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, PADDING_SMALL))
        self.project_var = StringVar()
        self.project_combobox = ctk.CTkComboBox(editor_tab, variable=self.project_var,
                                               values=self.all_projects, width=260,
                                               dropdown_fg_color=ThemeManager.get_color("card_bg"),
                                               button_color=ACCENT_COLOR,
                                               button_hover_color=BUTTON_HOVER)
        self.project_combobox.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, PADDING_MEDIUM))
        
        # Task section
        ctk.CTkLabel(editor_tab, text="任务:",
                    font=(FONT_NAME, 11, "bold")).grid(row=2, column=0, sticky="w", pady=(0, PADDING_SMALL))
        self.task_var = StringVar()
        self.task_combobox = ctk.CTkComboBox(editor_tab, variable=self.task_var, width=180,
                                            dropdown_fg_color=ThemeManager.get_color("card_bg"),
                                            button_color=ACCENT_COLOR,
                                            button_hover_color=BUTTON_HOVER)
        self.task_combobox.grid(row=3, column=0, sticky="w", padx=(0, PADDING_SMALL))
        
        # Estimate input
        ctk.CTkLabel(editor_tab, text="Est:",
                    font=(FONT_NAME, 11, "bold")).grid(row=2, column=1, sticky="w", pady=(0, PADDING_SMALL))
        self.estimate_var = StringVar(value="1")
        self.estimate_entry = ctk.CTkEntry(editor_tab, textvariable=self.estimate_var,
                                          width=50, justify="center")
        self.estimate_entry.grid(row=3, column=1, sticky="w")
        
        # Sound choice  
        self.sound_choice = StringVar(value="dida")
        sound_frame = ctk.CTkFrame(self.setup_view_frame, fg_color="transparent")
        ctk.CTkRadioButton(sound_frame, text="Ticking", variable=self.sound_choice, value="dida", 
                          font=(FONT_NAME, 10)).pack(side="left", padx=PADDING_SMALL)
        ctk.CTkRadioButton(sound_frame, text="Music", variable=self.sound_choice, value="music", 
                          font=(FONT_NAME, 10)).pack(side="left", padx=PADDING_SMALL)
        sound_frame.grid(row=2, column=0, columnspan=3, pady=PADDING_MEDIUM)
        
        # --- Controls ---
        self.action_button = ctk.CTkButton(self.controls_frame, text="Start", 
                                          command=self.action_command, width=120, height=45,
                                          fg_color=ThemeManager.get_color("danger"), 
                                          hover_color="#c0392b",
                                          font=(FONT_NAME, 14, "bold"),
                                          corner_radius=8)
        self.action_button.grid(row=0, column=0, padx=8)
        
        self.secondary_button = ctk.CTkButton(self.controls_frame, text="Analysis", 
                                             command=self.analysis_command, width=120, height=45, 
                                             fg_color=ThemeManager.get_color("danger"), 
                                             hover_color="#c0392b",
                                             font=(FONT_NAME, 14, "bold"),
                                             corner_radius=8)
        self.secondary_button.grid(row=0, column=1, padx=8)
        
        self.daily_checkmark_label = ctk.CTkLabel(self.daily_checkmarks_frame, 
                                                  font=(FONT_NAME, 12, "bold"), 
                                                  text_color=ThemeManager.get_color("danger"))
        self.daily_checkmark_label.pack()
        
        # --- Status Bar ---
        btn_frame = ctk.CTkFrame(self.status_bar_frame, fg_color="transparent")
        btn_frame.pack(anchor="w")
        ctk.CTkButton(btn_frame, text="Backup", command=self.load_backup_command,
                     font=(FONT_NAME, 9), width=60, height=24,
                     fg_color="transparent", text_color="#888888",
                     hover_color=BUTTON_HOVER).pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text="Merge", command=self.merge_db_command,
                     font=(FONT_NAME, 9), width=60, height=24,
                     fg_color="transparent", text_color="#888888",
                     hover_color=BUTTON_HOVER).pack(side="left", padx=2)
        self.db_status_label = ctk.CTkLabel(self.status_bar_frame, text="", 
                                           font=(FONT_NAME, 9), 
                                           text_color="#888888")
        self.db_status_label.pack(anchor="w")

    def update_quick_start_buttons(self, recent_tasks):
        for widget in self.quick_start_frame.winfo_children(): widget.destroy()
        if not recent_tasks: return
        ctk.CTkLabel(self.quick_start_frame, text="Quick Start:", 
                    font=(FONT_NAME, 11, "bold")).pack(anchor="w", pady=(PADDING_SMALL, PADDING_SMALL))
        f = ctk.CTkFrame(self.quick_start_frame, fg_color="transparent")
        f.pack()
        for t in recent_tasks:
            ctk.CTkButton(f, text=t['task'][:9]+"...", 
                         command=lambda p=t['project'], t=t['task']: self.quick_start_command(p, t),
                         font=(FONT_NAME, 11), width=85, height=28,
                         fg_color=BUTTON_COLOR, hover_color=BUTTON_HOVER).pack(side="left", padx=3)

    def toggle_mute(self):
        """Toggle pause/resume of current sound"""
        if self.is_muted:
            # Resume - restore sound
            self.mute_button.configure(text="⏸️")
            self.is_muted = False
            # Call sound_manager's resume method
            if self.sound_manager:
                self.sound_manager.resume_sound()
        else:
            # Pause - stop sound temporarily
            self.mute_button.configure(text="▶️")
            self.is_muted = True
            # Call sound_manager's pause method
            if self.sound_manager:
                self.sound_manager.pause_sound()
    
    def show_setup_view(self):
        self.timer_view_frame.grid_remove()
        self.setup_view_frame.grid(row=0, column=0, sticky="n")
        self.status_bar_frame.grid(row=3, column=0, sticky="ew")
        self.root.resizable(True, True)
        self.root.attributes('-topmost', False)
        self.root.after_idle(self._fit_home_window)

    def _fit_home_window(self):
        self.root.update_idletasks()
        width, height = calculate_home_size(
            self.root.winfo_reqwidth(), self.root.winfo_reqheight(),
            self.root.winfo_screenwidth(), self.root.winfo_screenheight(),
        )
        self.root.geometry(f"{width}x{height}")

    def show_timer_view(self):
        self.setup_view_frame.grid_remove()
        self.timer_view_frame.grid(row=0, column=0, sticky="n")
        self.status_bar_frame.grid_remove()
        self.root.geometry(TIMER_WINDOW_GEOMETRY)
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)

    def _bind_events(self):
        # CustomTkinter ComboBox uses 'command' parameter, but we can also bind to selection
        # Use configure to set command callback for proper event handling
        self.project_combobox.configure(command=lambda choice: self.root.event_generate("<<ProjectSelected>>"))
        self.task_combobox.configure(command=lambda choice: self.root.event_generate("<<TaskSelected>>"))

        # --- Context Menus ---
        self._attach_context_menu(self.project_combobox, "Delete Project", self.delete_project_callback, self.get_project_name)
        self._attach_context_menu(self.task_combobox, "Delete Task", self.delete_task_callback, self.get_task_name)

    def _attach_context_menu(self, widget, label_text, command, get_value_func):
        """Attaches a right-click menu to a widget."""
        menu = Menu(self.root, tearoff=0, bg=BG_COLOR, fg=FG_COLOR, activebackground=BUTTON_COLOR, activeforeground="white")
        
        def show_menu(event):
            # Only show if there is actually a value selected/entered
            if get_value_func():
                menu.delete(0, "end")
                menu.add_command(label=f"{label_text} '{get_value_func()}'", command=command)
                menu.tk_popup(event.x_root, event.y_root)
        
        widget.bind("<Button-3>", show_menu) # Windows Right-Click

    def toggle_action_button(self, is_running): 
        self.action_button.configure(text="Abort" if is_running else "Start")
    
    def toggle_secondary_button(self, is_running):
        new_text = "Complete" if is_running else "Analysis"
        new_command = self.secondary_action_command if is_running else self.analysis_command
        self.secondary_button.configure(text=new_text, command=new_command)
        
        # Ensure Analysis button is always enabled when in setup mode
        if not is_running:
            self.secondary_button.configure(state="normal")
    
    def update_complete_button_status(self, is_completed): 
        self.secondary_button.configure(state="disabled" if is_completed else "normal")
    
    def update_db_status(self, ts):
        self.db_status_label.configure(text=f"Updated: {ts}")

    def get_project_name(self): return self.project_var.get().strip()
    def get_task_name(self): return self.task_var.get().strip()
    def get_estimate(self): return parse_focus_estimate(self.estimate_var.get())
    def get_sound_choice(self): return self.sound_choice.get()
    def set_project_list(self, projects): self.project_combobox.configure(values=projects)
    def set_task_list(self, tasks): self.task_combobox.configure(values=tasks)
    def set_estimate(self, value): self.estimate_var.set(str(value))
    def set_sound_choice(self, choice): self.sound_choice.set(choice)
    def select_editor_tab(self): self.task_source_tabs.set("本地任务")

    def refresh_local_focus_items(self, items):
        for widget in self.local_focus_list.winfo_children():
            widget.destroy()
        if not items:
            ctk.CTkLabel(self.local_focus_list, text="还没有本地任务。填写上方任务后按开始，即可离线计时。").pack(pady=10)
            return
        for item in items:
            binding = "已绑定 DW" if item["state"] == "bound" else "草稿"
            text = (
                f'{item["task_name"]}\n{item["project_name"]}  ·  '
                f'{item["completed_count"]}/{item["estimate"]}  ·  {binding}'
            )
            ctk.CTkButton(
                self.local_focus_list, text=text, anchor="w", height=48,
                command=lambda value=item: self.focus_item_select_callback(value),
            ).pack(fill="x", pady=3)

    def refresh_goalsifter_focus_items(self, items, status_text=""):
        for widget in self.goalsifter_focus_list.winfo_children():
            widget.destroy()
        ctk.CTkLabel(
            self.goalsifter_focus_list,
            text=status_text or "仅显示活跃 DW；任务编辑与完成请回 GoalSifter。",
            font=(FONT_NAME, 11), justify="left",
        ).pack(anchor="w", pady=(2, 8))
        ctk.CTkButton(
            self.goalsifter_focus_list, text="刷新 GoalSifter 任务", height=28,
            command=self.goalsifter_refresh_callback,
        ).pack(anchor="w", pady=(0, 8))
        ctk.CTkButton(
            self.goalsifter_focus_list, text="手动同步 Outbox", height=28,
            command=self.goalsifter_sync_callback,
        ).pack(anchor="w", pady=(0, 8))
        ctk.CTkButton(
            self.goalsifter_focus_list, text="⚙ 连接设置", height=28,
            command=self.goalsifter_settings_callback,
        ).pack(anchor="w", pady=(0, 8))
        if not items:
            ctk.CTkLabel(self.goalsifter_focus_list, text="没有可选的活跃 DW。", font=(FONT_NAME, 11)).pack(pady=12)
            return
        for item in items:
            context = item.get("context_label") or "未关联 KR"
            text = f'{item["task_name"]}\nKR：{context}  ·  {item["completed_count"]}/{item["estimate"]}  ·  已绑定 DW'
            row = ctk.CTkFrame(self.goalsifter_focus_list, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkButton(
                row, text=text, anchor="w", height=52,
                command=lambda value=item: self.focus_item_select_callback(value),
            ).pack(side="left", fill="x", expand=True)
            ctk.CTkButton(
                row, text="完成", width=60, height=52,
                command=lambda value=item: self.goalsifter_complete_callback(value),
            ).pack(side="right", padx=(5, 0))
    
    def update_timer_display(self, time_str):
        if hasattr(self, 'pygame_widget'):
            self.pygame_widget.update_text(time_str)

    def update_header(self, text, color): 
        self.timer_label.configure(text=text, text_color=color)
    
    def update_progress(self, text): 
        # Deprecated: progress_label removed.
        # Use session_progress_bar.set_progress instead.
        pass
    
    def update_daily_checkmarks(self, marks): 
        self.daily_checkmark_label.configure(text=marks)
    
    def set_timer_mode(self, mode):
        """Passes the session mode to the Pygame widget to control particles"""
        if hasattr(self, 'pygame_widget'):
            self.pygame_widget.set_mode(mode)

    def _on_theme_toggle(self):
        """Wraps the callback to also update the button icon potentially"""
        if self.theme_toggle_callback:
            self.theme_toggle_callback()
            # Optional: toggle icon if you wanted sun/moon specific icons
            # current_mode = ThemeManager.get_mode()
            # self.theme_btn.configure(text="☀️" if current_mode == "light" else "🌙")
