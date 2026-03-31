"""
Debug script to test calendar view generation directly.
"""
import os
import pandas as pd
from datetime import datetime
from pomodoro_data_manager import PomodoroDataManager
from analysis_manager import AnalysisManager

base_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(base_dir, "data")

# Initialize managers
data_manager = PomodoroDataManager(data_dir, "pomodoro_data.db")

# Get all sessions
df = data_manager.get_all_sessions_for_analysis()

print(f"Total sessions: {len(df)}")
print(f"Columns: {df.columns.tolist()}")

# Process data like the calendar view does
df['start_time'] = pd.to_datetime(df['start_time'])
df['date'] = df['start_time'].dt.date

# Filter for completed work sessions
work_df = df[df['session_type'] == 'Work'].copy()
completed_work_df = work_df[work_df['status'] == 'Completed'].copy()

print(f"\nWork sessions: {len(work_df)}")
print(f"Completed work sessions: {len(completed_work_df)}")

if not completed_work_df.empty:
    print(f"\nFirst few completed sessions:")
    print(completed_work_df[['start_time', 'date', 'project_name', 'task_name']].head())
    
    # Test calendar generation
    analysis_manager = AnalysisManager(data_manager, base_dir)
    calendar_html = analysis_manager._generate_calendar_view(completed_work_df)
    
    print(f"\nCalendar HTML length: {len(calendar_html)}")
    print(f"Contains calendar title: {'Pomodoro Activity Calendar' in calendar_html}")
    print(f"Contains tomato emoji: {'🍅' in calendar_html}")
    
    # Save to test file
    with open("test_calendar.html", "w", encoding="utf-8") as f:
        f.write(calendar_html)
    print("\nCalendar HTML saved to test_calendar.html")
else:
    print("\nNo completed work sessions found!")

data_manager.close()
