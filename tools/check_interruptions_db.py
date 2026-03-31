import sqlite3
import os
import pandas as pd

DB_PATH = os.path.join("data", "pomodoro_data.db")

def check_interruptions():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        
        # 1. Count interrupted sessions
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sessions WHERE status = 'Interrupted'")
        total_interrupted = cursor.fetchone()[0]
        print(f"Total Interrupted Sessions: {total_interrupted}")

        if total_interrupted == 0:
            print("No interrupted sessions found.")
            conn.close()
            return

        # 2. Dump details
        query = "SELECT session_id, project_name, task_name, start_time, duration_minutes, interruption_reason FROM sessions WHERE status = 'Interrupted'"
        df = pd.read_sql_query(query, conn)
        
        print("\n--- Raw Interruption Data ---")
        print(df.to_string())
        
        # 3. Check for NULL/Empty reasons
        null_reasons = df[df['interruption_reason'].isnull()]
        empty_reasons = df[df['interruption_reason'] == ""]
        print(f"\nNULL reasons: {len(null_reasons)}")
        print(f"Empty string reasons: {len(empty_reasons)}")

        conn.close()
        
    except Exception as e:
        print(f"Error reading database: {e}")

if __name__ == "__main__":
    check_interruptions()
