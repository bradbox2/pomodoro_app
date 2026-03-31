
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont

root = tk.Tk()
root.withdraw() # Hide

# Configure styles/fonts as in the app
FONT_NAME = "Segoe UI"
title_font = tkfont.Font(family=FONT_NAME, size=26, weight="bold")
std_font = tkfont.Font(family=FONT_NAME, size=10)
btn_font = tkfont.Font(family=FONT_NAME, size=13, weight="bold")

# Measure Title
title_text = "FocusFlow 2.9"
title_w = title_font.measure(title_text)
print(f"Title '{title_text}' width: {title_w}px")

# Measure CoolButton text
btn_text = "Analysis" # The wider text
btn_text_w = btn_font.measure(btn_text)
print(f"Button Text '{btn_text}' width: {btn_text_w}px") 
# Note CoolButton is fixed width 120 in code, so checking if text fits isn't the issue, 
# but checking if 2 buttons (120*2) + padding fits is the key.
# 2 buttons: 120 + 120 + 8(left) + 8(right) + 8(left) + 8(right) = 240 + 32 = 272px.
# Window inner width (300 - 20) = 280px. Fits.

# Measure Combobox
# ttk Combobox width is in characters '0'.
style = ttk.Style()
style.theme_use('clam')
style.configure(".", font=(FONT_NAME, 10))

# Create a dummy combobox to measure requested width
combo = ttk.Combobox(root, width=26, font=std_font)
req_w = combo.winfo_reqwidth()
print(f"Combobox(width=26) requested width: {req_w}px")

combo_small = ttk.Combobox(root, width=18, font=std_font)
req_w_small = combo_small.winfo_reqwidth()
print(f"Combobox(width=18) requested width: {req_w_small}px")

root.destroy()
