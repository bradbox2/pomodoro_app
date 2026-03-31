# test_ctk_basic.py - 测试 CustomTkinter 基础迁移
"""
Quick test to verify CustomTkinter setup before全面迁移
"""

import customtkinter as ctk
from ctk_theme_config import ThemeManager
from config import *

#初始化主题
ThemeManager.initialize("dark")

# 创建测试窗口
window = ctk.CTk()
window.title("FocusFlow 3.0 - CustomTkinter Test")
window.geometry("400x300")

# 测试基本组件
label = ctk.CTkLabel(window, text="CustomTkinter Test", font=(FONT_NAME, 20, "bold"))
label.pack(pady=20)

button = ctk.CTkButton(
    window,
    text="Test Button",
    fg_color=BUTTON_COLOR,
    hover_color=BUTTON_HOVER,
    font=(FONT_NAME, 12)
)
button.pack(pady=10)

entry = ctk.CTkEntry(window, placeholder_text="Test input...")
entry.pack(pady=10)

status_label = ctk.CTkLabel(window, text=f"✅ Theme: {ThemeManager.get_mode()}")
status_label.pack(pady=10)

toggle_btn = ctk.CTkButton(
    window,
    text="Toggle Theme",
    command=lambda: status_label.configure(text=f"✅ Theme: {ThemeManager.toggle()}")
)
toggle_btn.pack(pady=10)

window.mainloop()
