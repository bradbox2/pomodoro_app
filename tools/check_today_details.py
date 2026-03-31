import sqlite3
import os

conn = sqlite3.connect(os.path.join('data', 'pomodoro_data.db'))
c = conn.cursor()

c.execute("""
    SELECT session_id, project_name, task_name, session_type, start_time, duration_minutes, status 
    FROM sessions 
    WHERE start_time LIKE '2026-01-16%'
""")
rows = c.fetchall()

print(f"Found {len(rows)} sessions today:")
work_completed = 0
for r in rows:
    print(f"  {r[1]} | {r[2]} | Type: {r[3]} | Status: {r[6]} | Duration: {r[5]}")
    if r[3] == 'Work' and r[6] == 'Completed':
        work_completed += 1

print(f"\nTotal Completed Work Sessions: {work_completed}")
conn.close()
