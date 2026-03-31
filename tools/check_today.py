import sqlite3
import os

conn = sqlite3.connect(os.path.join('data', 'pomodoro_data.db'))
c = conn.cursor()

print("=" * 60)
print("SESSIONS ON 2026-01-16 (Today)")
print("=" * 60)

c.execute("""
    SELECT session_id, project_name, task_name, session_type, start_time, duration_minutes, status 
    FROM sessions 
    WHERE start_time LIKE '2026-01-16%'
    ORDER BY start_time DESC
""")
rows = c.fetchall()

if not rows:
    print("NO sessions found for today (2026-01-16).")
else:
    print(f"Found {len(rows)} sessions today:")
    for r in rows:
        print(f"  {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]}min | {r[6]}")

conn.close()
