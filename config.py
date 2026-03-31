# config.py
APP_NAME = "FocusFlow"
APP_VERSION = "3.1.1"

# --- UI Color Constants (Dark Ocean Theme) ---
BG_COLOR = "#242424"   # Gray14 (Matches CustomTkinter Dark Mode)
FG_COLOR = "#FFFFFF"   # White text
ACCENT_COLOR = "#F4A261" # Warm Orange-Yellow accent (optimized from #E9C46A)
CARD_BG_COLOR = "#1F1F1F" # Dark Gray for card backgrounds
BUTTON_COLOR = "#2A9D8F" # Teal button
BUTTON_HOVER = "#21867A" # Darker Teal hover (improved contrast)
PINK = "#e2979c"       # Keep for breaks
RED = "#e76f51"        # Burnt Orange (Warmer Red)
GREEN = "#2A9D8F"      # Teal (Matches button)
SUCCESS_COLOR = "#52B788" # Green for completion states
YELLOW = BG_COLOR      # Deprecated, mapped to BG for backward compat

# --- Font Constants ---
FONT_NAME = "Segoe UI"

# --- Timer Constants (in minutes) ---
WORK_MIN = 25
SHORT_BREAK_MIN = 5
LONG_BREAK_MIN = 15

# --- Long Break Configuration ---
LONG_BREAK_INTERVAL = 4            # Number of work sessions before a long break
RESET_LONG_BREAK_ON_RESTART = True # If True, count starts from 0 on app restart. If False, continues from historical data.

# --- Database Filename ---
DB_NAME = "pomodoro_data.db"

# --- Window Behavior ---
WINDOW_GEOMETRY = "300x510"  # Optimized from 360x580 for better content display
ALWAYS_ON_TOP = True
FOCUSED_TRANSPARENCY = 0.8

# --- Spacing Constants ---
PADDING_SMALL = 5
PADDING_MEDIUM = 10
PADDING_LARGE = 15
PADDING_XLARGE = 20

# --- Feedback Behavior ---
# Ask for user feedback on the first session, and then every N sessions.
# Set to 1 to ask for feedback every time.
FEEDBACK_INTERVAL = 3

# --- Planning Mode Configuration (v3.0) ---
PLANNING_WINDOW_GEOMETRY = "800x600"  # Planning Mode 窗口默认尺寸
DEFAULT_THEME_MODE = "dark"            # 默认主题模式 ("dark" 或 "light")
ENABLE_THEME_SWITCHING = True          # 是否启用主题切换功能
ENABLE_ANIMATIONS = True               # 是否启用UI动画效果
HIGH_CONTRAST_MODE = False             # 高对比度模式（可访问性）
FONT_SIZE_SCALE = 1.0                  # 字体缩放系数（1.0 = 100%）

import os as _os
try:
    from dotenv import load_dotenv as _load
    _load(_os.path.join(_os.path.dirname(__file__), ".env"))
except ImportError:
    pass

# --- PocketBase Cloud Sync Configuration ---
PB_SYNC_ENABLED = True
PB_URL      = _os.environ.get("PB_URL", "")
PB_EMAIL    = _os.environ.get("PB_EMAIL", "")
PB_PASSWORD = _os.environ.get("PB_PASSWORD", "")
PB_COLLECTIONS = {
    "projects": "ff_projects",
    "tasks": "ff_tasks",
    "sessions": "ff_sessions"
}
