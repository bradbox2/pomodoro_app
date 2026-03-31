import os
import sys
import webbrowser
from datetime import datetime, timedelta
from analysis_manager import AnalysisManager
from pomodoro_data_manager import PomodoroDataManager

# Initialize
base_dir = os.path.dirname(__file__)
data_dir = os.path.join(base_dir, 'data')
data_manager = PomodoroDataManager(data_dir, 'pomodoro_data.db')
am = AnalysisManager(data_manager, base_dir)

# Define range: Last 30 days
end = datetime.now().replace(hour=23, minute=59, second=59)
start = end - timedelta(days=30)

print(f"Generating dashboard for range: {start} to {end}")

# Run generation
try:
    print("\n--- Testing LAST 30 DAYS ---")
    am.generate_and_show_report(start_date=start, end_date=end)
    print("Dashboard 30d generated successfully!")

    print("\n--- Testing ALL TIME (start=None, end=None) ---")
    am.generate_and_show_report(start_date=None, end_date=None)
    print("Dashboard ALL TIME generated successfully!")

except Exception as e:
    print(f"Error generating dashboard: {e}")
    import traceback
    traceback.print_exc()

data_manager.close()
