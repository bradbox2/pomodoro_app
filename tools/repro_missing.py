import os
import pandas as pd
from pomodoro_data_manager import PomodoroDataManager

# Initialize
base_dir = os.path.dirname(__file__)
data_dir = os.path.join(base_dir, 'data')
mgr = PomodoroDataManager(data_dir, 'pomodoro_data.db')

df = mgr.get_all_sessions_for_analysis()
df['start_time'] = pd.to_datetime(df['start_time'])

# NO filtering (All Time)
# ...

# Filter Completed Work
completed_work = df[(df['session_type'] == 'Work') & (df['status'] == 'Completed')]

print(f"Total Completed Work: {len(completed_work)}")
print("Projects present:")
print(completed_work['project_name'].unique())

python_rows = completed_work[completed_work['project_name'] == 'Python Learning']
print(f"Python Learning rows: {len(python_rows)}")

mgr.close()
