# M尊享用户同步功能 / M-Tier User Sync Feature

## 功能概述 / Feature Overview

**中文：**
此功能允许管理员将数据库中的M尊享用户（`lv='m'`）的Telegram ID同步到配置文件（`config.json`）的`m_users`列表中。

**English:**
This feature allows administrators to sync M-tier users (`lv='m'`) from the database to the `m_users` list in the configuration file (`config.json`).

---

## 问题背景 / Background

**中文：**
- 在config面板中手动添加M用户时可能会失败或导致原有用户ID丢失
- 数据库中有M尊享用户（lv='m'），但config.json中的m_users列表可能不同步
- 需要一个简单的方法来确保两者保持一致

**English:**
- Manually adding M users in the config panel might fail or cause existing user IDs to be lost
- M-tier users exist in the database (lv='m'), but the m_users list in config.json may be out of sync
- A simple method is needed to ensure both stay in sync

---

## 使用方法 / How to Use

### 1. 进入配置面板 / Access Config Panel

**中文：**
1. 发送 `/config` 命令
2. 点击 "👥 管理M尊享用户" 按钮

**English:**
1. Send `/config` command
2. Click the "👥 管理M尊享用户" button

### 2. 使用同步命令 / Use Sync Command

**中文：**
在弹出的输入框中输入：
```
sync
```

**English:**
In the popup input box, enter:
```
sync
```

### 3. 完成同步 / Complete Sync

**中文：**
系统将：
1. 查询数据库中所有 `lv='m'` 的用户
2. 提取他们的Telegram ID
3. **过滤掉在 `m_welcome_exclude` 排除列表中的用户** 🚫
4. 合并到 `config.m_users` 列表（保留原有ID）
5. 更新全局 `m_users` 变量
6. 保存到 `config.json` 文件
7. 显示同步的用户数量和跳过的用户数量

**English:**
The system will:
1. Query all users with `lv='m'` from the database
2. Extract their Telegram IDs
3. **Filter out users in the `m_welcome_exclude` exclusion list** 🚫
4. Merge them into the `config.m_users` list (preserving existing IDs)
5. Update the global `m_users` variable
6. Save to `config.json` file
7. Display the count of synced users and skipped users

---

## 可用命令 / Available Commands

在M用户管理面板中，现在支持以下命令：

| 命令 / Command | 说明 / Description |
|---|---|
| `add 123456789` | 添加用户到M尊享列表 / Add user to M-tier list |
| `del 123456789` | 从M尊享列表删除用户 / Remove user from M-tier list |
| `list` | 查看当前M尊享用户列表 / View current M-tier user list |
| `sync` | **新增** 从数据库同步M用户 / **NEW** Sync M users from database |

---

## 技术细节 / Technical Details

### 实现逻辑 / Implementation Logic

```python
# 1. 查询数据库中所有M级用户
m_level_users = get_all_emby(Emby.lv == 'm')

# 2. 提取TG ID
synced_ids = [user.tg for user in m_level_users if user.tg]

# 3. 过滤掉在排除列表中的用户
synced_ids_filtered = [uid for uid in synced_ids if uid not in config.m_welcome_exclude]

# 4. 合并到配置（去重）
config.m_users = list(set(config.m_users + synced_ids_filtered))

# 5. 同步全局变量
m_users.clear()
m_users.extend(config.m_users)

# 6. 保存配置
save_config()
```

**注意 / Note:**
- 🚫 在 `m_welcome_exclude`（欢迎排除列表）中的用户将不会被同步到 `m_users`
- 这确保了管理员明确排除的用户不会在同步操作中被意外添加回来
- 如果有被跳过的用户，系统会显示跳过的数量

- 🚫 Users in `m_welcome_exclude` will not be synced to `m_users`
- This ensures that explicitly excluded users are not accidentally added back during sync
- If users are skipped, the system will display the count

### 数据流 / Data Flow

```
数据库 (Database)          配置文件 (Config File)        全局变量 (Global Var)
┌─────────────────┐       ┌──────────────────┐         ┌─────────────────┐
│ Emby表          │       │ config.json      │         │ m_users (list)  │
│ ├─ tg: 123     │       │ {                │         │                 │
│ ├─ lv: 'm'  ──→ sync ──→│   "m_users": [   │──sync──→│ [123, 456, 789] │
│ ├─ tg: 456     │       │     123,         │         │                 │
│ └─ tg: 789     │       │     456,         │         │                 │
│                 │       │     789          │         │                 │
└─────────────────┘       │   ]              │         └─────────────────┘
                          │ }                │
                          └──────────────────┘
```

---

## 优势 / Advantages

**中文：**
- ✅ **防止数据丢失** - 合并而不是覆盖现有ID
- ✅ **一键同步** - 无需手动逐个添加
- ✅ **保持一致性** - 确保数据库和配置文件同步
- ✅ **简单易用** - 只需输入 `sync` 命令
- ✅ **安全可靠** - 保留原有数据，只添加新数据
- ✅ **尊重排除列表** - 自动跳过在排除列表中的用户 🚫

**English:**
- ✅ **Prevents data loss** - Merges instead of overwriting existing IDs
- ✅ **One-click sync** - No need to add manually one by one
- ✅ **Maintains consistency** - Ensures database and config file are in sync
- ✅ **Easy to use** - Just enter the `sync` command
- ✅ **Safe and reliable** - Preserves existing data, only adds new data
- ✅ **Respects exclusion list** - Automatically skips users in exclusion list 🚫

---

## 故障排查 / Troubleshooting

### Q1: 同步后为什么有些用户ID消失了？
**A:** 不会发生！同步使用合并策略（`set(config.m_users + synced_ids)`），会保留所有原有ID。

### Q1: Why did some user IDs disappear after sync?
**A:** This won't happen! The sync uses a merge strategy (`set(config.m_users + synced_ids)`), which preserves all existing IDs.

---

### Q2: 数据库中没有M用户怎么办？
**A:** 系统会显示 "⚠️ 数据库中未找到M尊享用户"，并保持当前列表不变。

### Q2: What if there are no M users in the database?
**A:** The system will display "⚠️ 数据库中未找到M尊享用户" and keep the current list unchanged.

---

### Q3: 同步会影响bot运行吗？
**A:** 不会。同步是异步操作，不会阻塞bot的其他功能。更新后会立即生效。

### Q3: Will syncing affect bot operation?
**A:** No. Syncing is an asynchronous operation and won't block other bot functions. Changes take effect immediately.

---

### Q4: 多次同步会重复添加用户吗？
**A:** 不会。使用 `set()` 去重，确保每个用户ID只出现一次。

### Q4: Will syncing multiple times add duplicate users?
**A:** No. Uses `set()` for deduplication, ensuring each user ID appears only once.

---

### Q5: 如果用户在排除列表中，同步时会怎样？
**A:** 在 `m_welcome_exclude` 排除列表中的用户将被自动跳过，不会添加到 `m_users`。系统会显示跳过的用户数量。例如：
```
✅ 已从数据库同步 3 个M尊享用户
⚠️ 跳过 2 个在排除列表中的用户
```

### Q5: What happens if a user is in the exclusion list during sync?
**A:** Users in the `m_welcome_exclude` exclusion list will be automatically skipped and not added to `m_users`. The system will display the count of skipped users. For example:
```
✅ Synced 3 M-tier users from database
⚠️ Skipped 2 users in exclusion list
```

---

## 文件修改 / Files Modified

- `bot/modules/panel/config_panel.py`
  - 添加 `sync` 命令处理逻辑
  - 导入 `get_all_emby` 和 `Emby` 从 `bot.sql_helper.sql_emby`
  - 更新用户界面说明

---

## 版本历史 / Version History

- **2025-01-08**: 初始版本，添加 `sync` 命令 / Initial version, added `sync` command

---

## 相关文档 / Related Documentation

- [M_WELCOME_OPTIMIZATION.md](./M_WELCOME_OPTIMIZATION.md) - M尊享欢迎功能优化
- [M_WELCOME_EXCLUDE_FEATURE.md](./M_WELCOME_EXCLUDE_FEATURE.md) - M尊享欢迎排除列表功能
- [config_example.json](./config_example.json) - 配置文件示例

---

## 总结 / Summary

**中文：**
此功能解决了config面板中M用户管理的同步问题，提供了一个简单、安全、可靠的方法来确保数据库中的M尊享用户与配置文件保持一致。

**English:**
This feature solves the M user management sync issue in the config panel, providing a simple, safe, and reliable method to ensure M-tier users in the database stay in sync with the configuration file.
