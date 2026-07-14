# GoalSifter 服务端同步更新备份交接记录

**记录日期**: 2026-07-13  
**记录用途**: 交给本地 AI agent 执行源码与数据库备份  
**重要边界**: 本次只更新了 WSL 中的 GoalSifter v3 源码工作树，未执行生产部署或 VPS 数据库迁移。

## 源码位置

```text
\\wsl.localhost\Ubuntu\home\jerry\workspace\openclaw-bot\bots\goalsifter_v3
```

相关源码文件：

- `skills/goalsifter_core/focusflow_api.py`
- `skills/goalsifter_core/api_server.py`
- `skills/goalsifter_core/db_init.py`
- `tests/test_focusflow_contract.py`
- `docs/devlog/2026-07-13-focusflow-offline-multidevice-sync.md`

## 建议备份步骤

### 1. 记录当前工作树状态

```bash
cd /home/jerry/workspace/openclaw-bot/bots/goalsifter_v3
date -Iseconds > /tmp/focusflow-server-backup-date.txt
git status --short > /tmp/focusflow-server-backup-status.txt
git diff -- skills/goalsifter_core/focusflow_api.py \
  skills/goalsifter_core/api_server.py \
  skills/goalsifter_core/db_init.py \
  tests/test_focusflow_contract.py \
  > /tmp/focusflow-server-sync-update.patch
```

### 2. 复制源码差异和开发记录

将以下文件复制到本地备份目录，不要使用 `git clean`、`git reset --hard` 或覆盖整个工作树：

```text
/tmp/focusflow-server-sync-update.patch
skills/goalsifter_core/focusflow_api.py
skills/goalsifter_core/api_server.py
skills/goalsifter_core/db_init.py
tests/test_focusflow_contract.py
docs/devlog/2026-07-13-focusflow-offline-multidevice-sync.md
```

建议备份目录命名：

```text
FocusFlow_Server_Backup_20260713_OfflineMultideviceSync/
```

### 3. 备份 GoalSifter 数据库

先从配置或 `skills/goalsifter_core/db_connect.py` 确认实际 SQLite 路径，再执行 SQLite 在线备份。不要直接复制正在写入的数据库文件：

```bash
sqlite3 /实际数据库路径/goalsifter.db ".backup '/备份目录/goalsifter-20260713-predeploy.db'"
sha256sum /备份目录/goalsifter-20260713-predeploy.db \
  > /备份目录/goalsifter-20260713-predeploy.db.sha256
```

备份完成后核对以下表存在：

```sql
SELECT name FROM sqlite_master
WHERE type = 'table'
  AND name IN ('focusflow_events', 'focusflow_event_conflicts', 'task_events');
```

### 4. 验证源码备份可恢复

在临时副本中应用 patch，不要在原工作树验证：

```bash
git clone --no-hardlinks /home/jerry/workspace/openclaw-bot/bots/goalsifter_v3 \
  /tmp/goalsifter-v3-backup-check
cd /tmp/goalsifter-v3-backup-check
git apply /tmp/focusflow-server-sync-update.patch
python -m pytest -q tests/test_focusflow_contract.py tests/test_t9_focusflow_webhook.py
```

## 备份完成回执

由执行备份的 AI agent 填写：

```text
备份目录：
源码 patch SHA-256：
数据库备份文件：
数据库备份 SHA-256：
验证命令及结果：
是否执行生产部署：否 / 是（需填写批准人和时间）
```

## 恢复注意事项

- 不要恢复整个 GoalSifter v3 工作树；该仓库当前存在其他未提交改动。
- 优先恢复目标文件或应用 `/tmp/focusflow-server-sync-update.patch`，并人工检查冲突。
- 生产部署前先备份数据库，再执行服务端迁移；迁移会新增 `payload_hash` 和 `focusflow_event_conflicts`。
- 服务端升级后必须重启 API 进程，并重新执行 FocusFlow 契约测试或等价冒烟测试。
