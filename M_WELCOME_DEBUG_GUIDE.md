# M尊享欢迎功能调试指南 / M-Tier Welcome Debug Guide

## 问题描述 / Problem Description

如果M尊享用户发言后没有收到欢迎消息，且日志中没有任何相关记录，现在可以通过新增的调试日志来排查问题。

If M-tier users don't receive welcome messages after speaking, and there are no related logs, you can now troubleshoot using the new debug logging.

## 新增的调试日志 / New Debug Logging

现在 `m_welcome.py` 在以下情况会输出调试日志：

The `m_welcome.py` module now outputs debug logs in the following cases:

### 1. 消息无from_user / Message has no from_user
```
【M尊享欢迎】- 消息无from_user，跳过（可能是频道消息）
```
**原因**：消息来自频道而非用户  
**解决**：这是正常情况，不需要处理

**Cause**: Message is from a channel, not a user  
**Solution**: This is normal, no action needed

### 2. 收到用户消息 / User message received
```
【M尊享欢迎】- 收到用户 张三 (ID: 123456789) 的消息
```
**说明**：Bot成功接收到用户消息，隐私模式已正确关闭

**Info**: Bot successfully received user message, privacy mode is correctly disabled

### 3. 用户不在数据库中 / User not in database
```
【M尊享欢迎】- 用户 张三 (ID: 123456789) 不在数据库中
```
**原因**：用户还没有注册Emby账户  
**解决**：用户需要先通过Bot注册Emby账户

**Cause**: User hasn't registered an Emby account yet  
**Solution**: User needs to register an Emby account through the Bot

### 4. 用户等级不是M / User level is not M
```
【M尊享欢迎】- 用户 张三 (ID: 123456789) 等级为 a，不是M尊享
```
**原因**：用户的等级不是 'm'（可能是 'a', 'b', 'c' 等）  
**解决**：使用 `/prom` 命令将用户升级为M尊享

**Cause**: User's level is not 'm' (might be 'a', 'b', 'c', etc.)  
**Solution**: Use `/prom` command to upgrade user to M-tier

### 5. 今天已经欢迎过 / Already welcomed today
```
【M尊享欢迎】- 用户 张三 (ID: 123456789) 今天已经欢迎过了
```
**原因**：每个M尊享用户每天只会被欢迎一次  
**解决**：这是正常行为，明天会重新欢迎

**Cause**: Each M-tier user is welcomed only once per day  
**Solution**: This is normal behavior, they will be welcomed again tomorrow

### 6. 成功欢迎 / Successfully welcomed
```
【M尊享欢迎】- 欢迎M尊享用户 张三 (ID: 123456789)
```
**说明**：成功发送欢迎消息

**Info**: Welcome message sent successfully

### 7. 测试模式触发 / Test mode triggered
```
【M尊享欢迎】- 测试模式：用户 张三 (ID: 123456789) 发送了测试消息
【M尊享欢迎】- 欢迎M尊享用户 张三 (ID: 123456789)
```
**说明**：任何用户发送"test"消息时触发测试模式，会跳过所有检查（数据库存在、每日欢迎限制和等级检查），立即发送欢迎消息

**Info**: When any user sends "test" message, test mode is triggered, bypassing all checks (database existence, daily welcome limit and level check), sending welcome message immediately

## 测试功能 / Test Feature

为了方便测试M尊享欢迎功能是否正常工作，现在**任何用户**都可以通过发送 **"test"** 消息来触发欢迎消息，无需在数据库中，也无需特定等级。

To test if the M-tier welcome feature is working, **any user** can now send **"test"** message to trigger the welcome message, without needing to be in the database or having a specific level.

**使用方法 / Usage:**
1. 在群组中发送消息 "test" / Send message "test" in the group
2. Bot将立即回复欢迎消息 / Bot will immediately reply with welcome message
3. 此测试不会更新数据库中的欢迎日期 / This test will not update the welcome date in database
4. 不需要在数据库中或特定等级 / No need to be in database or have specific level

## 如何启用调试日志 / How to Enable Debug Logging

### 方法1：修改日志配置 / Method 1: Modify log configuration

编辑 `bot/func_helper/logger_config.py`，将 `level` 从 `"INFO"` 改为 `"DEBUG"`：

Edit `bot/func_helper/logger_config.py`, change `level` from `"INFO"` to `"DEBUG"`:

```python
log_config = {
    "sink": log_filename,
    "format": log_format,
    "level": "DEBUG",  # 改为 DEBUG / Change to DEBUG
    "rotation": "00:00",
    "retention": "30 days"
}
```

### 方法2：临时启用（推荐）/ Method 2: Temporary enable (Recommended)

在运行Bot之前设置环境变量：

Set environment variable before running the Bot:

```bash
export LOGURU_LEVEL=DEBUG
python main.py
```

## 故障排查流程 / Troubleshooting Process

### 步骤 1：检查是否收到消息 / Step 1: Check if messages are received

启用DEBUG日志后，让M尊享用户在群组中发言。

Enable DEBUG logging, then have an M-tier user speak in the group.

**如果看不到任何日志 / If you don't see any logs:**
- ✗ Bot可能处于隐私模式 / Bot might be in privacy mode
- ✓ 按照 [BOT_PRIVACY_MODE_SETUP.md](./BOT_PRIVACY_MODE_SETUP.md) 关闭隐私模式 / Follow BOT_PRIVACY_MODE_SETUP.md to disable privacy mode
- ✗ Bot可能不在授权群组中 / Bot might not be in authorized group
- ✓ 检查 `config.json` 中的 `group` 列表 / Check `group` list in config.json

**如果看到"收到用户消息" / If you see "user message received":**
- ✓ Bot正常接收消息，继续下一步 / Bot is receiving messages normally, proceed to next step

### 步骤 2：检查用户状态 / Step 2: Check user status

根据看到的调试日志判断：

Based on the debug log you see:

- **"用户不在数据库中" / "User not in database"**  
  → 用户需要先注册Emby账户 / User needs to register Emby account first

- **"等级为 X，不是M尊享" / "Level is X, not M-tier"**  
  → 使用 `/prom <user_id>` 升级用户 / Use `/prom <user_id>` to upgrade user

- **"今天已经欢迎过了" / "Already welcomed today"**  
  → 正常，等待明天 / Normal, wait until tomorrow

- **"欢迎M尊享用户" / "Welcoming M-tier user"**  
  → 功能正常工作！ / Feature is working!

## 常见问题 / FAQ

### Q: 为什么有些用户看到日志，有些看不到？
### Q: Why do I see logs for some users but not others?

A: 如果完全看不到某个用户的日志，说明Bot没有接收到该用户的消息。这通常是因为：
1. Bot处于隐私模式（最常见）
2. 该群组不在授权列表中
3. Bot没有正确启动

A: If you don't see any logs for a user, the Bot is not receiving their messages. This is usually because:
1. Bot is in privacy mode (most common)
2. The group is not in the authorized list
3. Bot is not running correctly

### Q: 日志显示"等级为 null"或其他值
### Q: Log shows "level is null" or other values

A: 这说明用户在数据库中但等级不是 'm'。使用管理命令 `/prom` 将用户升级为M尊享。

A: This means the user is in the database but their level is not 'm'. Use the admin command `/prom` to upgrade the user to M-tier.

### Q: 每次重启Bot后用户都被欢迎
### Q: Users are welcomed every time the Bot restarts

A: 检查数据库的 `m_welcome_date` 字段是否正确保存。如果每次都是 NULL，可能是数据库写入权限问题。

A: Check if the `m_welcome_date` field in the database is being saved correctly. If it's always NULL, there might be a database write permission issue.

## 相关文档 / Related Documentation

- [BOT_PRIVACY_MODE_SETUP.md](./BOT_PRIVACY_MODE_SETUP.md) - Bot隐私模式设置
- [M_WELCOME_FIX_SUMMARY.md](./M_WELCOME_FIX_SUMMARY.md) - M尊享欢迎功能修复说明

---

**更新日期 / Last Updated**: 2025-01-09
