# feedback_window.py
import os
import tkinter as tk
from tkinter import ttk, Toplevel, PhotoImage
from config import BG_COLOR, FG_COLOR

class FeedbackWindow(Toplevel):
    """A pop-up window to gather user feedback after a session."""
    def __init__(self, parent, image_dir):
        super().__init__(parent)
        self.transient(parent)
        self.title("Session Feedback")
        self.config(bg=BG_COLOR)
        
        # Bring to front but don't block
        self.lift()
        self.focus_force()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        self.feedback_data = {
            "focus_score": 5,
            "end_mood": "Neutral"
        }

        # Load the image
        try:
            image_path = os.path.join(image_dir, "submit.gif") 
            self.header_image = PhotoImage(file=image_path)
        except tk.TclError as e:
            print(f"Warning: Could not load image at {image_path}. Error: {e}")
            self.header_image = None

        self._create_widgets()
        
        # Block until window is closed
        self.grab_set()
        self.wait_window(self)

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(expand=True, fill="both")

        # Display the image at the top
        if self.header_image:
            image_label = ttk.Label(main_frame, image=self.header_image)
            image_label.pack(pady=(0, 15))

        # End Mood - Using a more robust Grid layout for buttons
        ttk.Label(main_frame, text="How do you feel now?").pack(anchor="w", pady=(5,5))
        mood_frame = ttk.Frame(main_frame)
        mood_frame.pack(pady=5)
        
        # Load moods from config
        from app_config_manager import AppConfigManager
        config_manager = AppConfigManager()
        moods = config_manager.get_feedback_moods()
        
        s = ttk.Style()
        s.configure('small.TButton', font=('Helvetica', 8), padding=(5, 5))
        
        # Arrange buttons in a 2-column grid to ensure they always fit
        for i, mood_data in enumerate(moods):
            # Parse mood_data from config (expecting dict set: {'name': 'Excited', 'score': 9})
            # Backward compatibility check just in case
            if isinstance(mood_data, dict):
                mood_name = mood_data.get('name', 'Unknown')
                mood_score = mood_data.get('score', 5)
            else:
                mood_name = str(mood_data)
                mood_score = 5

            button = ttk.Button(mood_frame, text=mood_name, style='small.TButton', 
                                command=lambda n=mood_name, s=mood_score: self._on_mood_selected(n, s))
            row = i // 3  # Change to 3 columns for better layout
            col = i % 3
            button.grid(row=row, column=col, padx=3, pady=3, sticky="ew")

    def _on_mood_selected(self, mood_name: str, score: int):
        self.feedback_data["end_mood"] = mood_name
        self.feedback_data["focus_score"] = score
        self.destroy()

    def _on_close(self):
        # If closed without selecting, we keep defaults or partial data
        self.destroy()

    def get_feedback(self):
        """Returns the collected feedback data."""
        return self.feedback_data
