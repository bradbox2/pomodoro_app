# ctk_theme_config.py
"""
CustomTkinter 主题配置管理器
为 FocusFlow 3.0 提供统一的主题系统，支持深色/浅色模式切换
"""

import customtkinter as ctk
from focusflow.config import BG_COLOR, FG_COLOR, ACCENT_COLOR, BUTTON_COLOR, BUTTON_HOVER, CARD_BG_COLOR


class ThemeManager:
    """统一的主题管理单例类"""
    
    _initialized = False
    _current_mode = "dark"
    
    # 主题颜色映射 - 深色模式与 v2.9 保持一致
    THEMES = {
        "dark": {
            "bg": "#242424",           # 主背景 - Gray14 (matches CTk dark mode)
            "fg": "#FFFFFF",           # 文字颜色 - White
            "accent": "#F4A261",       # 强调色 - Warm Orange-Yellow
            "button": "#2A9D8F",       # 按钮颜色 - Teal
            "button_hover": "#21867A", # 按钮悬停 - Darker Teal
            "card_bg": "#1F1F1F",      # 卡片背景 - Dark Gray
            "success": "#52B788",      # 成功状态 - Green
            "danger": "#E76F51",       # 危险/删除 - Burnt Orange
            "break": "#e2979c"         # 休息状态 - Pink
        },
        "light": {
            "bg": "#EBEBEB",           # 主背景 - Light Gray (Standard CTk/System Gray)
            "fg": "#212529",           # 文字颜色 - Dark Gray
            "accent": "#E76F51",       # 强调色 - Burnt Orange
            "button": "#2A9D8F",       # 按钮颜色 - Teal (保持品牌色)
            "button_hover": "#1F7A6E", # 按钮悬停
            "card_bg": "#FFFFFF",      # 卡片背景 - White
            "success": "#52B788",      # 成功状态
            "danger": "#E76F51",       # 危险/删除
            "break": "#D4A5A5"         # 休息状态 - Light Pink
        }
    }
    
    # Observer pattern for theme change notifications
    _observers = []
    
    # --- Color Conversion Utilities ---
    
    @staticmethod
    def hex_to_rgb(hex_color: str) -> tuple:
        """Convert hex color (#RRGGBB) to RGB tuple (R, G, B)."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    @staticmethod
    def ctk_color_to_rgb(ctk_color: str) -> tuple:
        """Convert CustomTkinter color (hex or named like 'gray14') to RGB tuple."""
        if ctk_color.startswith('#'):
            return ThemeManager.hex_to_rgb(ctk_color)
        
        # Named colors - use tkinter to resolve
        import tkinter as tk
        try:
            temp_root = tk.Tk()
            temp_root.withdraw()
            rgb_string = temp_root.winfo_rgb(ctk_color)
            temp_root.destroy()
            # winfo_rgb returns 16-bit (0-65535), convert to 8-bit (0-255)
            return tuple(v // 256 for v in rgb_string)
        except:
            return (0, 0, 0)  # Fallback to black
    
    @classmethod
    def get_color_rgb(cls, key: str) -> tuple:
        """Get color as RGB tuple for Pygame."""
        hex_color = cls.get_color(key)
        return cls.ctk_color_to_rgb(hex_color)
    
    # --- Observer Pattern ---
    
    @classmethod
    def subscribe(cls, callback):
        """Subscribe to theme change notifications."""
        if callback not in cls._observers:
            cls._observers.append(callback)
    
    @classmethod
    def unsubscribe(cls, callback):
        """Unsubscribe from theme change notifications."""
        if callback in cls._observers:
            cls._observers.remove(callback)
    
    @classmethod
    def _notify_observers(cls):
        """Notify all observers of theme change."""
        for callback in cls._observers:
            try:
                callback()
            except Exception as e:
                print(f"⚠️ Theme observer error: {e}")
    
    # --- Validation ---
    
    @classmethod
    def validate_color(cls, color: str) -> bool:
        """Validate if color is compatible with both CTk and Pygame."""
        try:
            cls.ctk_color_to_rgb(color)
            return True
        except:
            return False
    
    @classmethod
    def initialize(cls, mode="dark"):
        """
        初始化主题系统
        
        Args:
            mode: "dark" 或 "light"，默认深色主题
        """
        if cls._initialized:
            return
        
        ctk.set_appearance_mode(mode)
        ctk.set_default_color_theme("blue")  # 使用内置蓝色主题作为基础
        cls._current_mode = mode
        cls._initialized = True
        print(f"✅ Theme initialized: {mode} mode")
    
    @classmethod
    def toggle(cls):
        """
        切换深色/浅色主题
        
        Returns:
            str: 新的主题模式 ("dark" 或 "light")
        """
        new_mode = "light" if cls._current_mode == "dark" else "dark"
        cls.set_mode(new_mode)
        return new_mode
    
    @classmethod
    def set_mode(cls, mode: str):
        """
        Set theme mode and notify observers.
        
        Args:
            mode: "dark" or "light"
        """
        if mode in cls.THEMES:
            cls._current_mode = mode
            ctk.set_appearance_mode(mode)
            cls._notify_observers()
            print(f"🎨 Theme changed to: {mode}")
    
    @classmethod
    def get_color(cls, key):
        """
        获取当前主题的颜色值
        
        Args:
            key: 颜色键名 (bg, fg, accent, button, button_hover, card_bg, success, danger, break)
        
        Returns:
            str: 十六进制颜色值
        """
        return cls.THEMES[cls._current_mode].get(key, "#FFFFFF")
    
    @classmethod
    def get_mode(cls):
        """
        获取当前主题模式
        
        Returns:
            str: "dark" 或 "light"
        """
        return cls._current_mode
    
    @classmethod
    def get_all_colors(cls):
        """
        获取当前主题的所有颜色
        
        Returns:
            dict: 颜色字典
        """
        return cls.THEMES[cls._current_mode].copy()
