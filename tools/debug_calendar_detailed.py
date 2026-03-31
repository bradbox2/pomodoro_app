"""
Enhanced debug script to trace the exact data flow.
"""
import os
import pandas as pd
from datetime import datetime, timedelta
from pomodoro_data_manager import PomodoroDataManager

base_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(base_dir, "data")

# Initialize managers
data_manager = PomodoroDataManager(data_dir, "pomodoro_data.db")

# Get all sessions
df = data_manager.get_all_sessions_for_analysis()

# Process data like the calendar view does
df['start_time'] = pd.to_datetime(df['start_time'])
df['date'] = df['start_time'].dt.date

# Filter for completed work sessions
work_df = df[df['session_type'] == 'Work'].copy()
completed_work_df = work_df[work_df['status'] == 'Completed'].copy()

print("=== BEFORE FIX ===")
print(f"Date column type: {type(completed_work_df['date'].iloc[0])}")
print(f"First few dates: {completed_work_df['date'].head().tolist()}")

# NOW APPLY THE FIX
completed_work_df['date'] = pd.to_datetime(completed_work_df['date'])
daily_counts = completed_work_df.groupby('date')['duration_minutes'].count().reset_index(name='pomodoro_count')

print("\n=== AFTER FIX ===")
print(f"Daily counts date type: {type(daily_counts['date'].iloc[0])}")
print(f"Daily counts:\n{daily_counts}")

# Create date range
today = datetime.now()
current_month_start = today.replace(day=1)

if current_month_start.month == 1:
    previous_month_start = current_month_start.replace(year=current_month_start.year - 1, month=12)
else:
    previous_month_start = current_month_start.replace(month=current_month_start.month - 1)

if current_month_start.month == 12:
    current_month_end = current_month_start.replace(year=current_month_start.year + 1, month=1, day=1) - timedelta(days=1)
else:
    current_month_end = current_month_start.replace(month=current_month_start.month + 1, day=1) - timedelta(days=1)

all_dates = pd.date_range(start=previous_month_start, end=current_month_end, freq='D')

print(f"\n=== DATE RANGE ===")
print(f"Date range type: {type(all_dates[0])}")
print(f"Date range: {previous_month_start} to {current_month_end}")
print(f"Total days: {len(all_dates)}")

# Merge
date_df = pd.DataFrame({'date': all_dates})
print(f"\ndate_df date type: {type(date_df['date'].iloc[0])}")

merged = date_df.merge(daily_counts, on='date', how='left')
merged['pomodoro_count'] = merged['pomodoro_count'].fillna(0).astype(int)

print(f"\n=== MERGED DATA ===")
print(f"Merged rows: {len(merged)}")
print(f"Non-zero counts: {(merged['pomodoro_count'] > 0).sum()}")
print(f"\nDays with pomodoros:")
print(merged[merged['pomodoro_count'] > 0][['date', 'pomodoro_count']])

# Test data lookup for January 2026
print(f"\n=== DATA LOOKUP TEST ===")
data_lookup = {}
for _, row in merged.iterrows():
    if row['date'].year == 2026 and row['date'].month == 1:
        data_lookup[row['date'].day] = int(row['pomodoro_count'])

print(f"January 2026 lookup dictionary:")
for day, count in sorted(data_lookup.items()):
    if count > 0:
        print(f"  Day {day}: {count} pomodoros")

data_manager.close()
