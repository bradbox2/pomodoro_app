import os
import sqlite3
import pandas as pd
from datetime import datetime
from pomodoro_data_manager import PomodoroDataManager
from analysis_manager import AnalysisManager

# Setup
TEST_DB = "test_verify.db"
if os.path.exists(TEST_DB): os.remove(TEST_DB)

dm = PomodoroDataManager(".", TEST_DB)
am = AnalysisManager(dm, ".")

# 1. Test Task with Stats
print("--- Testing Task Stats ---")
dm.add_or_update_task("Proj1", "TaskA", 5)
dm.add_or_update_task("Proj1", "TaskB", 3)

# Add sessions
today = datetime.now()
session_data = {
    'project_name': "Proj1", 'task_name': "TaskA",
    'session_type': 'Work', 'start_time': today, 'end_time': today,
    'duration_minutes': 25, 'status': 'Completed'
}
dm.record_session(session_data)
dm.record_session(session_data) # 2 sessions for TaskA
dm.record_session({**session_data, 'task_name': 'TaskB', 'status': 'Interrupted'}) # 0 completed for TaskB

tasks = dm.get_tasks_with_stats("Proj1")
print(f"Tasks: {tasks}")

found_a = next((t for t in tasks if t['name'] == 'TaskA'), None)
found_b = next((t for t in tasks if t['name'] == 'TaskB'), None)

if found_a and found_a['count'] == 2:
    print("PASS: TaskA count is 2")
else:
    print(f"FAIL: TaskA count is {found_a['count'] if found_a else 'None'}")

if found_b and found_b['count'] == 0:
    print("PASS: TaskB count is 0")
else:
    print(f"FAIL: TaskB count is {found_b['count'] if found_b else 'None'}")


# 2. Test Dashboard Generation
print("\n--- Testing Analysis Report ---")
# Generate HTML
am.generate_and_show_report()

report_path = os.path.join(".", "pomodoro_dashboard.html")
if os.path.exists(report_path):
    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
        # Check Summary Tab
        if "Total Focus Time by Project & Task" in content:
            print("PASS: Summary chart updated to show Tasks")
        else:
            print("FAIL: Summary chart title mismatch")

        # Check Time Analysis (Calendar View & Weekly)
        if "Calendar View" in content:
            print("PASS: Calendar View found")
        else:
            print("FAIL: Calendar View NOT found")
            
        if "Total Focus Time by Week" in content:
            print("PASS: Weekly chart found in Time Analysis")
        else:
            print("FAIL: Weekly chart NOT found")

        # Check Removed Items
        if "Long Term Trends" not in content.replace("Long Term Trends", ""): # Check for Tab button
            # Note: "Long Term Trends" string might exist in old code, we need to check the TAB Button text
            # But simpler: check if the tab ID div is gone or the button text is gone from the tab list
            if 'id="LongTerm"' not in content:
                print("PASS: Long Term Trends tab removed")
            else:
                print("FAIL: Long Term Trends tab div still present")
        
        if "Total Focus Time by Month" not in content:
            print("PASS: Monthly bar chart removed")
        else:
             # It might be part of the Calendar view title if I used that, but I used "Calendar View"
            print("FAIL: 'Total Focus Time by Month' string still found (should be removed)")

else:
    print("FAIL: Report file not generated")

# Cleanup
dm.close()
if os.path.exists(TEST_DB): os.remove(TEST_DB)
