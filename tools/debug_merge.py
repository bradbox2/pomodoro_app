"""
Final debug script to understand the exact merge issue.
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

print("Step 1: Original date column")
print(f"  Type: {type(completed_work_df['date'].iloc[0])}")
print(f"  Sample: {completed_work_df['date'].iloc[0]}")

# Convert to datetime
completed_work_df['date'] = pd.to_datetime(completed_work_df['date'])

print("\nStep 2: After pd.to_datetime")
print(f"  Type: {type(completed_work_df['date'].iloc[0])}")
print(f"  Sample: {completed_work_df['date'].iloc[0]}")

# Group by date
daily_counts = completed_work_df.groupby('date')['duration_minutes'].count().reset_index(name='pomodoro_count')

print("\nStep 3: After groupby")
print(f"  Type: {type(daily_counts['date'].iloc[0])}")
print(f"  Sample: {daily_counts['date'].iloc[0]}")
print(f"  Daily counts shape: {daily_counts.shape}")
print(f"\nDaily counts data:")
print(daily_counts)

# Create date range
today = datetime.now()
current_month_start = today.replace(day=1)
previous_month_start = current_month_start.replace(month=12, year=2025) if current_month_start.month == 1 else current_month_start.replace(month=current_month_start.month - 1)
current_month_end = current_month_start.replace(month=2, day=1, year=2026) - timedelta(days=1) if current_month_start.month == 12 else current_month_start.replace(month=current_month_start.month + 1, day=1) - timedelta(days=1)

all_dates = pd.date_range(start=previous_month_start, end=current_month_end, freq='D')

print(f"\nStep 4: Date range")
print(f"  Type: {type(all_dates[0])}")
print(f"  Sample: {all_dates[0]}")
print(f"  Length: {len(all_dates)}")

# Create DataFrame
date_df = pd.DataFrame({'date': all_dates})

print(f"\nStep 5: date_df")
print(f"  Type: {type(date_df['date'].iloc[0])}")
print(f"  Sample: {date_df['date'].iloc[0]}")

# Try merge
print("\nStep 6: Attempting merge...")
merged = date_df.merge(daily_counts, on='date', how='left')
print(f"  Merged shape: {merged.shape}")
print(f"  Non-null counts: {merged['pomodoro_count'].notna().sum()}")

# Check for matches
print("\nStep 7: Checking for date matches...")
for idx, row in daily_counts.iterrows():
    date_val = row['date']
    matches = date_df[date_df['date'] == date_val]
    print(f"  {date_val}: {len(matches)} matches in date_df")

# Normalize dates to remove time component
print("\nStep 8: Testing with normalized dates...")
daily_counts_normalized = daily_counts.copy()
daily_counts_normalized['date'] = daily_counts_normalized['date'].dt.normalize()

date_df_normalized = date_df.copy()
date_df_normalized['date'] = date_df_normalized['date'].dt.normalize()

merged_normalized = date_df_normalized.merge(daily_counts_normalized, on='date', how='left')
print(f"  Normalized merge - Non-null counts: {merged_normalized['pomodoro_count'].notna().sum()}")

if merged_normalized['pomodoro_count'].notna().sum() > 0:
    print("\n✅ SUCCESS with normalized dates!")
    print(merged_normalized[merged_normalized['pomodoro_count'].notna()][['date', 'pomodoro_count']])

data_manager.close()
