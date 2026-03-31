import sqlite3
import os
import time
from datetime import datetime
from config import DB_NAME, PB_COLLECTIONS
from sync_manager import SyncManager

def sync_history():
    # 1. Connect to local DB
    # We need to find the data folder relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, "data", DB_NAME)
    
    if not os.path.exists(db_path):
        # Try parent directory just in case
        db_path = os.path.join(script_dir, DB_NAME)
        if not os.path.exists(db_path):
            print(f"❌ 找不到本地数据库: {db_path}")
            return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print("✅ 已连接本地数据库，开始同步历史记录...")

    # 2. Sync Projects
    print("\n[1/3] 同步项目...")
    cursor.execute("SELECT project_name FROM projects")
    projects = cursor.fetchall()
    for row in projects:
        name = row[0]
        print(f"  -> {name}")
        SyncManager.sync_data("projects", {"project_name": name}, record_id=name)
        time.sleep(0.1)

    # 3. Sync Tasks
    print("\n[2/3] 同步任务...")
    cursor.execute("SELECT project_name, task_name, estimated_pomodoros, status, sound_preference FROM tasks")
    tasks = cursor.fetchall()
    for row in tasks:
        p_name, t_name, est, status, sound = row
        print(f"  -> {p_name} / {t_name}")
        payload = {
            "project_name": p_name,
            "task_name": t_name,
            "estimated_pomodoros": est,
            "status": status,
            "sound_preference": sound
        }
        SyncManager.sync_data("tasks", payload, record_id=f"{p_name}_{t_name}")
        time.sleep(0.1)

    # 4. Sync Sessions
    print("\n[3/3] 同步番茄钟记录...")
    cursor.execute("SELECT session_id, project_name, task_name, session_type, start_time, end_time, duration_minutes, status, focus_score, end_mood, interruption_reason FROM sessions")
    sessions = cursor.fetchall()
    for row in sessions:
        sid, p_name, t_name, s_type, start, end, dur, status, focus, mood, reason = row
        print(f"  -> Session {sid[:8]}...")
        payload = {
            "project_name": p_name,
            "task_name": t_name,
            "session_type": s_type,
            "start_time": start,
            "end_time": end,
            "duration_minutes": dur,
            "status": status,
            "focus_score": focus,
            "end_mood": mood,
            "interruption_reason": reason
        }
        SyncManager.sync_data("sessions", payload, record_id=sid)
        time.sleep(0.05)

    print("\n🎉 历史记录同步任务已提交到后台线程！")
    print("请正在处理中，请稍后在云端查看结果...")
    time.sleep(10) # Give more time for threads to finish

if __name__ == "__main__":
    sync_history()
