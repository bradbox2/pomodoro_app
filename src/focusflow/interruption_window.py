# interruption_window.py
import tkinter as tk
from tkinter import ttk, Toplevel
from focusflow.config import BG_COLOR
from focusflow.app_config_manager import AppConfigManager

class InterruptionWindow(Toplevel):
    """A pop-up window for selecting the reason for a session interruption."""
    def __init__(self, parent):
        super().__init__(parent)
        self.transient(parent)
        self.title("Interruption Reason")
        self.config(bg=BG_COLOR)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        self.reason = "Unknown"  # Default reason if closed

        self._create_widgets()
        self.grab_set()
        self.wait_window(self)

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(expand=True, fill="both")
        
        ttk.Label(main_frame, text="Why was the session interrupted?", 
                 font=('Helvetica', 10, 'bold')).pack(pady=(0, 10))

        reasons = AppConfigManager().get_interruption_reasons()

        if not reasons:
            ttk.Label(main_frame, text="暂无可用的中断原因。请在设置中添加。").pack(pady=10)

        for category, reason_list in reasons.items():
            cat_frame = ttk.LabelFrame(main_frame, text=category, padding="10")
            cat_frame.pack(fill="x", pady=5)

            if not reason_list:
                ttk.Label(cat_frame, text="此分类暂无中断原因。").pack(fill="x", pady=2)
                continue
            
            # Display buttons vertically for better visibility
            for reason_data in reason_list:
                # Handle both dict and string format
                if isinstance(reason_data, dict):
                    reason_text = reason_data.get('name', 'Unknown')
                else:
                    reason_text = str(reason_data)
                
                button = ttk.Button(cat_frame, text=reason_text, 
                                   command=lambda r=reason_text: self._on_reason_selected(r))
                button.pack(fill="x", pady=2)  # Vertical layout with padding

    def _on_reason_selected(self, reason: str):
        """Records the reason and closes the window."""
        self.reason = reason
        self.destroy()

    def _on_close(self):
        """Called when the window is closed via the 'X' button."""
        self.destroy()

    def get_reason(self):
        """Returns the selected interruption reason."""
        return self.reason
