import sqlite3
import os
from datetime import datetime, timedelta

db_path = os.path.join("data", "pomodoro_data.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check total sessions
cursor.execute("SELECT COUNT(*) FROM sessions")
total = cursor.fetchone()[0]
print(f"Total sessions: {total}")

# Check completed work sessions
cursor.execute("SELECT COUNT(*) FROM sessions WHERE session_type='Work' AND status='Completed'")
completed = cursor.fetchone()[0]
print(f"Completed work sessions: {completed}")

# Check dates with data
cursor.execute("""
    SELECT DATE(start_time) as date, COUNT(*) as count 
    FROM sessions 
    WHERE session_type='Work' AND status='Completed'
    GROUP BY DATE(start_time)
    ORDER BY date DESC
    LIMIT 10
""")
print("\nLast 10 days with completed pomodoros:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} pomodoros")

# Check today
today = datetime.now().strftime('%Y-%m-%d')
cursor.execute("""
    SELECT COUNT(*) FROM sessions 
    WHERE session_type='Work' AND status='Completed' 
    AND DATE(start_time) = ?
""", (today,))
today_count = cursor.fetchone()[0]
print(f"\nToday ({today}): {today_count} completed pomodoros")

conn.close()
