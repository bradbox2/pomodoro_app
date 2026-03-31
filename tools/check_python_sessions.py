import sqlite3
import os

conn = sqlite3.connect(os.path.join('data', 'pomodoro_data.db'))
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM sessions WHERE project_name = 'Python Learning'")
count = c.fetchone()[0]

print(f"Total sessions for 'Python Learning': {count}")

conn.close()
