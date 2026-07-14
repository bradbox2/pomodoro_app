import os
import sys
from focusflow.analysis_manager import AnalysisManager
from focusflow.pomodoro_data_manager import PomodoroDataManager

# Initialize
base_dir = os.path.dirname(__file__)
data_dir = os.path.join(base_dir, 'data')
data_manager = PomodoroDataManager(data_dir, 'pomodoro_data.db')
am = AnalysisManager(data_manager, base_dir)

print("\n--- Testing ALL TIME (start=None, end=None) ---")
am.generate_and_show_report(start_date=None, end_date=None)
print("Done!")

data_manager.close()
