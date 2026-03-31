import os
import pandas as pd
from datetime import datetime, timedelta
from pomodoro_data_manager import PomodoroDataManager

# Mock the class logic
def generate_calendar_view_debug(df):
    print("DEBUG: Inside generate_calendar_view")
    if df.empty:
        print("DEBUG: DF is empty inside function")
        return

    # Group by Date
    # df['date'] should already be set? No, caller sets it.
    df['start_time'] = pd.to_datetime(df['start_time'])
    df['date'] = df['start_time'].dt.date
    
    daily_counts = df.groupby('date')['duration_minutes'].count().reset_index(name='pomodoro_count')
    print("DEBUG: Daily counts calculated.")
    
    daily_counts['date'] = pd.to_datetime(daily_counts['date'])
    
    # Check Today (Hardcoded for verification if needed, or dynamic)
    today = datetime.now().date()
    today_dt = pd.to_datetime(today)
    
    print(f"DEBUG: Looking for today: {today_dt}")
    
    row = daily_counts[daily_counts['date'] == today_dt]
    if not row.empty:
        print(f"SUCCESS: Found row for today: {row.iloc[0]['pomodoro_count']} pomodoros")
    else:
        print("FAILURE: No row found for today!")
        print("DEBUG: Available dates:")
        print(daily_counts['date'].tolist())
    
    # Logic for current month
    current_month_start = today.replace(day=1)
    if current_month_start.month == 12:
        current_month_end = current_month_start.replace(year=current_month_start.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        current_month_end = current_month_start.replace(month=current_month_start.month + 1, day=1) - timedelta(days=1)
        
    print(f"DEBUG: Current month end: {current_month_end}")
    
    # Just check if merge works
    # ...

# Setup
base_dir = os.path.dirname(__file__)
data_dir = os.path.join(base_dir, 'data')
mgr = PomodoroDataManager(data_dir, 'pomodoro_data.db')
df = mgr.get_all_sessions_for_analysis()

# Filter like App
df['start_time'] = pd.to_datetime(df['start_time'])
work_sessions = df[df['session_type'] == 'Work']
completed_work = work_sessions[work_sessions['status'] == 'Completed']

print(f"DEBUG: Passed DF size: {len(completed_work)}")
generate_calendar_view_debug(completed_work.copy())

mgr.close()
