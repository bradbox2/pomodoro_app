import sqlite3
import os

conn = sqlite3.connect(os.path.join('data', 'pomodoro_data.db'))
c = conn.cursor()

c.execute("SELECT start_time, status FROM sessions WHERE project_name = 'Python Learning'")
rows = c.fetchall()

print("Python Learning Raw Data:")
for r in rows:
    print(f"Time: '{r[0]}', Status: '{r[1]}'")

conn.close()
