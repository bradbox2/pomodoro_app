import requests
import sys
import re
from config import PB_URL, PB_EMAIL, PB_PASSWORD, PB_COLLECTIONS

def init_pocketbase():
    # Normalize URL: remove trailing slashes and /api suffix for base URL logic
    base_url = PB_URL.rstrip('/')
    if base_url.endswith('/api'):
        base_url = base_url[:-4]
    
    print(f"正在连接到 PocketBase: {base_url} ...")
    
    # 1. 登录为超级用户 (Superuser Auth - PB v0.23+)
    # 注意：v0.23+ 版本中 Admin 已并入 _superusers 集合
    auth_url = f"{base_url}/api/collections/_superusers/auth-with-password"
    try:
        res = requests.post(auth_url, json={
            "identity": PB_EMAIL,
            "password": PB_PASSWORD
        }, timeout=15)
        # 如果 _superusers 失败，尝试旧版本的 admins 接口
        if res.status_code == 404:
            auth_url = f"{base_url}/api/admins/auth-with-password"
            res = requests.post(auth_url, json={
                "identity": PB_EMAIL,
                "password": PB_PASSWORD
            }, timeout=15)
        
        res.raise_for_status()
        token = res.json()["token"]
        print("✅ 身份验证成功")
    except Exception as e:
        print(f"❌ 认证失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"响应详情: {e.response.text}")
        print("请确保 config.py 中的 PB_EMAIL 和 PB_PASSWORD 是 PocketBase 的管理员账号。")
        return

    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. 定义集合方案 (Schemas)
    schemas = [
        {
            "name": PB_COLLECTIONS["projects"],
            "type": "base",
            "schema": [
                {"name": "project_name", "type": "text", "required": True, "unique": True}
            ]
        },
        {
            "name": PB_COLLECTIONS["tasks"],
            "type": "base",
            "schema": [
                {"name": "local_id", "type": "text", "required": True},
                {"name": "project_name", "type": "text"},
                {"name": "task_name", "type": "text"},
                {"name": "estimated_pomodoros", "type": "number"},
                {"name": "status", "type": "text"},
                {"name": "sound_preference", "type": "text"}
            ]
        },
        {
            "name": PB_COLLECTIONS["sessions"],
            "type": "base",
            "schema": [
                {"name": "local_id", "type": "text", "required": True},
                {"name": "project_name", "type": "text"},
                {"name": "task_name", "type": "text"},
                {"name": "session_type", "type": "text"},
                {"name": "start_time", "type": "date"},
                {"name": "end_time", "type": "date"},
                {"name": "duration_minutes", "type": "number"},
                {"name": "status", "type": "text"},
                {"name": "focus_score", "type": "number"},
                {"name": "end_mood", "type": "text"},
                {"name": "interruption_reason", "type": "text"}
            ]
        }
    ]

    # 3. 执行创建操作
    for collection_data in schemas:
        coll_name = collection_data["name"]
        print(f"检查集合 [{coll_name}] ...")
        
        # 检查是否已存在
        check_url = f"{base_url}/api/collections/{coll_name}"
        check_res = requests.get(check_url, headers=headers)
        if check_res.status_code == 200:
            print(f"  - 集合已存在，跳过。")
            continue
            
        # 创建集合
        create_url = f"{base_url}/api/collections"
        create_res = requests.post(
            create_url, 
            json=collection_data, 
            headers=headers
        )
        
        if create_res.status_code in [200, 204, 201]:
            print(f"  - ✅ 成功创建集合: {coll_name}")
        else:
            print(f"  - ❌ 创建失败: {create_res.text}")

    print("\n🎉 所有云端同步表初始化完成！")

if __name__ == "__main__":
    init_pocketbase()
