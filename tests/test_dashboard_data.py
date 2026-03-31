import os
import sys
import pandas as pd
from pomodoro_data_manager import PomodoroDataManager

# Initialize data manager
data_dir = os.path.join(os.path.dirname(__file__), 'data')
data_manager = PomodoroDataManager(data_dir, 'pomodoro_data.db')

# Get all sessions for analysis (same method used by Dashboard)
df = data_manager.get_all_sessions_for_analysis()

print(f"Total rows retrieved: {len(df)}")
print(f"\nDataFrame columns: {df.columns.tolist()}")
print(f"\nDataFrame shape: {df.shape}")

if not df.empty:
    print(f"\nFirst 5 rows:")
    print(df[['project_name', 'task_name', 'session_type', 'start_time', 'duration_minutes']].head())
    
    print(f"\nSession types:")
    print(df['session_type'].value_counts())
    
    print(f"\nProjects:")
    print(df['project_name'].value_counts())
    
    # Check if data is being processed correctly
    df['start_time'] = pd.to_datetime(df['start_time'])
    work_df = df[df['session_type'] == 'Work'].copy()
    completed_work_df = work_df[work_df['status'] == 'Completed'].copy()
    
    print(f"\nTotal Work sessions: {len(work_df)}")
    print(f"Completed Work sessions: {len(completed_work_df)}")
else:
    print("\nDataFrame is EMPTY - No data retrieved!")

data_manager.close()
