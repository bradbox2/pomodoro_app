"""
Test if the calendar is being generated in the actual dashboard flow.
"""
import os
from focusflow.pomodoro_data_manager import PomodoroDataManager
from focusflow.analysis_manager import AnalysisManager

base_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(base_dir, "data")

# Initialize managers
data_manager = PomodoroDataManager(data_dir, "pomodoro_data.db")
analysis_manager = AnalysisManager(data_manager, base_dir)

# Get the data like the dashboard does
df = data_manager.get_all_sessions_for_analysis()

print(f"Total sessions: {len(df)}")

if not df.empty:
    import pandas as pd
    df['start_time'] = pd.to_datetime(df['start_time'])
    df['day_of_week'] = df['start_time'].dt.day_name()
    df['hour'] = df['start_time'].dt.hour
    df['date'] = df['start_time'].dt.date
    
    work_df = df[df['session_type'] == 'Work'].copy()
    completed_work_df = work_df[work_df['status'] == 'Completed'].copy()
    
    print(f"Completed work sessions: {len(completed_work_df)}")
    
    # Test the summary chart generation
    summary_html = analysis_manager._create_summary_chart(completed_work_df)
    
    print(f"\nSummary HTML length: {len(summary_html)}")
    print(f"Contains calendar title: {'Pomodoro Activity Calendar' in summary_html}")
    print(f"Contains tomato emoji: {'🍅' in summary_html}")
    
    # Save for inspection
    with open("test_summary.html", "w", encoding="utf-8") as f:
        f.write(summary_html)
    print("\nSummary HTML saved to test_summary.html")

data_manager.close()
