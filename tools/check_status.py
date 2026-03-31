import sqlite3
import os
from datetime import datetime
import pandas as pd

db_path = os.path.join('data', 'pomodoro_data.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()

print(f"Current Time: {datetime.now()}")
print("=" * 60)
print("SESSIONS IN DATABASE (Last 10)")
print("=" * 60)

c.execute("""
    SELECT session_id, project_name, task_name, session_type, start_time, duration_minutes, status 
    FROM sessions 
    ORDER BY start_time DESC 
    LIMIT 10
""")
rows = c.fetchall()

if not rows:
    print("No sessions found in database.")
else:
    for r in rows:
        print(f"Project: '{r[1]}', Task: '{r[2]}', Type: {r[3]}, Time: {r[4]}, Duration: {r[5]}, Status: {r[6]}")

print("\n" + "=" * 60)
print("DASHBOARD FILE STATUS")
print("=" * 60)
dashboard_path = 'pomodoro_dashboard.html'
if os.path.exists(dashboard_path):
    mtime = os.path.getmtime(dashboard_path)
    dt = datetime.fromtimestamp(mtime)
    print(f"Dashboard file exists.")
    print(f"Last Modified: {dt}")
    print(f"Size: {os.path.getsize(dashboard_path)} bytes")
else:
    print("Dashboard file does NOT exist.")

conn.close()
