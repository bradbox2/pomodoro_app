import sqlite3
import os

conn = sqlite3.connect(os.path.join('data', 'pomodoro_data.db'))
c = conn.cursor()

c.execute("""
    SELECT task_name, session_type, duration_minutes, status 
    FROM sessions 
    WHERE start_time LIKE '2026-01-16%' AND session_type='Work'
""")
rows = c.fetchall()

print(f"Work Sessions Today ({len(rows)}):")
for r in rows:
    print(f"Task: {r[0]}, Duration: {r[2]} min, Status: {r[3]}")

conn.close()
