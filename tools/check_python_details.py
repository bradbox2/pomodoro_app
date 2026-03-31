import sqlite3
import os

conn = sqlite3.connect(os.path.join('data', 'pomodoro_data.db'))
c = conn.cursor()

c.execute("SELECT session_type, status, duration_minutes FROM sessions WHERE project_name = 'Python Learning'")
rows = c.fetchall()

print("Python Learning Sessions:")
for r in rows:
    print(f"Type: {r[0]}, Status: {r[1]}, Dur: {r[2]}")

conn.close()
