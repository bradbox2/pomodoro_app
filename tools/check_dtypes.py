import os
import pandas as pd
from pomodoro_data_manager import PomodoroDataManager

# Initialize
base_dir = os.path.dirname(__file__)
data_dir = os.path.join(base_dir, 'data')
mgr = PomodoroDataManager(data_dir, 'pomodoro_data.db')

print("Fetching all sessions...")
df = mgr.get_all_sessions_for_analysis()

print(f"Dataframe shape: {df.shape}")
print(f"Duration dtypes: {df['duration_minutes'].dtype}")

print("\nSample durations:")
print(df['duration_minutes'].head())
print(df['duration_minutes'].tail())

print("\nResult of sum():")
total = df['duration_minutes'].sum()
print(f"Sum type: {type(total)}")
print(f"Sum value: {total}")

mgr.close()
