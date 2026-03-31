import sqlite3
import pandas as pd
import os

DB_PATH = os.path.join("data", "pomodoro_data.db")
OUTPUT_CSV = "interruptions_dump.csv"

def dump_db():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT start_time, session_type, status, interruption_reason FROM sessions WHERE status='Interrupted' ORDER BY start_time DESC", conn)
    conn.close()
    
    print(f"Dumping {len(df)} records to {OUTPUT_CSV}")
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    
    # Also print distinct reasons
    print("\nDistinct Interruption Reasons:")
    print(df['interruption_reason'].value_counts())

if __name__ == "__main__":
    dump_db()
