# 测试消息回复功能说明 / Test Message Reply Feature

> **⚠️ 重要更新 / Important Update**
>
> **此功能已整合到 M尊享欢迎功能中** / **This feature has been integrated into the M-tier welcome feature**
> 
> 请参考 [M_WELCOME_OPTIMIZATION.md](./M_WELCOME_OPTIMIZATION.md) 了解详情。
> 
> Please refer to [M_WELCOME_OPTIMIZATION.md](./M_WELCOME_OPTIMIZATION.md) for details.

## 功能描述 / Feature Description

测试消息回复功能允许任何用户在群组中发送 "test" 来测试Bot的消息处理能力。

Test message reply feature allows any user to send "test" in the group to test the Bot's message processing capability.

**现在此功能已经整合到 `m_welcome.py` 中，不再需要单独的文件。**

**This feature is now integrated into `m_welcome.py`, no separate file needed.**

Bot可以访问群组中的消息，当用户在群组中发送 "test" 时，bot会自动回复 "测试成功"。

The bot can access messages in group chats. When a user sends "test" in the group, the bot will automatically reply with "测试成功" (test successful).

## 使用方法 / Usage

1. 确保bot已添加到授权群组（群组ID在 `config.json` 的 `group` 列表中）
2. 确保bot的隐私模式已关闭（参见 [BOT_PRIVACY_MODE_SETUP.md](BOT_PRIVACY_MODE_SETUP.md)）
3. 在群组中发送消息 "test"（不区分大小写）
4. Bot会立即回复 "测试成功"

Steps:
1. Ensure the bot is added to an authorized group (group ID is in the `group` list in `config.json`)
2. Ensure bot privacy mode is disabled (see [BOT_PRIVACY_MODE_SETUP.md](BOT_PRIVACY_MODE_SETUP.md))
3. Send message "test" in the group (case-insensitive)
4. Bot will immediately reply with "测试成功"

## 实现细节 / Implementation Details

### 文件 / Files

- `bot/modules/extra/test_reply.py` - 测试消息回复功能的实现
- `bot/modules/extra/__init__.py` - 导入测试回复处理器

### 代码逻辑 / Code Logic

**（现在位于 `m_welcome.py`）/ (Now located in `m_welcome.py`)**

```python
@bot.on_message(filters.chat(group) & filters.group & filters.text, group=1)
async def welcome_m_user(_, msg):
    # 只处理真实用户的文本消息
    if not msg.from_user:
        return
    
    # 测试模式：检查消息内容是否为 "test"
    if msg.text and msg.text.strip().lower() == "test":
        LOGGER.info(f"【M尊享欢迎】- 测试模式：用户 {msg.from_user.first_name} (ID: {msg.from_user.id}) 发送了测试消息")
        user_name = msg.from_user.first_name
        welcome_msg = random.choice(Yulv.load_yulv().m_welcome)
        welcome_msg = welcome_msg.replace("{name}", user_name)
        await msg.reply(welcome_msg)
        return
    
    # 其他M尊享欢迎逻辑...
```

### 优化改进 / Optimizations

与原实现相比的改进 / Improvements over original implementation:

1. ✅ **整合到一个文件** - 减少代码重复 / **Integrated into one file** - Reduces code duplication
2. ✅ **使用 `filters.text`** - 只处理文本消息 / **Uses `filters.text`** - Only processes text messages  
3. ✅ **早期返回** - 测试模式不查询数据库 / **Early return** - Test mode doesn't query database
4. ✅ **handler group** - 避免与其他handler冲突 / **handler group** - Avoids conflicts with other handlers
5. ✅ **更好的日志** - 明确标识测试模式 / **Better logging** - Clearly identifies test mode

### 过滤器 / Filters

**（已优化）/ (Optimized)**

- `filters.chat(group)` - 仅在授权群组中工作 / Only works in authorized groups
- `filters.group` - 仅在群组聊天中工作 / Only works in group chats
- `filters.text` - **新增：仅处理文本消息** / **New: Only processes text messages**
- 消息必须来自真实用户（非频道消息）/ Messages must be from real users (not channel messages)
- 消息文本必须为 "test"（不区分大小写）/ Message text must be "test" (case-insensitive)
- `group=1` - **新增：使用handler group确保执行顺序** / **New: Uses handler group to ensure execution order**

Filters:
- `filters.chat(group)` - Only works in authorized groups
- `filters.group` - Only works in group chats
- `filters.text` - **New: Only processes text messages**
- Messages must be from real users (not channel messages)
- Message text must be "test" (case-insensitive)
- `group=1` - **New: Uses handler group to ensure execution order**

## 日志 / Logging

当用户发送测试消息时，会在日志中看到：

When a user sends a test message, you will see in the logs:

```
【M尊享欢迎】- 测试模式：用户 张三 (ID: 123456789) 发送了测试消息
```

**注意日志标签已从 `【测试回复】` 更改为 `【M尊享欢迎】`**

**Note: Log tag changed from `【测试回复】` to `【M尊享欢迎】`**

## 注意事项 / Notes

⚠️ **重要**：此功能需要关闭bot的隐私模式才能正常工作。

⚠️ **Important**: This feature requires the bot's privacy mode to be disabled to work properly.

参见 / See: [BOT_PRIVACY_MODE_SETUP.md](BOT_PRIVACY_MODE_SETUP.md)

## 迁移说明 / Migration Notes

如果你之前使用了独立的 `test_reply.py`：

If you were previously using the standalone `test_reply.py`:

1. ✅ 功能完全兼容，无需修改 / Functionality fully compatible, no changes needed
2. ✅ 测试方式保持不变 / Test method remains the same  
3. ✅ 日志标签略有变化 / Log tag slightly changed
4. ✅ 回复消息从"测试成功"变为随机欢迎消息 / Reply changed from "测试成功" to random welcome message
5. ✅ 性能更优（使用 `filters.text`）/ Better performance (uses `filters.text`)

## 版本历史 / Version History

- **2025-01**: 功能整合 / Feature integration
  - ✅ 整合到 `m_welcome.py` / Integrated into `m_welcome.py`
  - ✅ 添加 `filters.text` 优化性能 / Added `filters.text` for optimization
  - ✅ 使用 handler group / Uses handler group
  - ✅ 回复随机欢迎消息 / Replies with random welcome message

- **2025**: 初始实现 / Initial implementation
  - 添加测试消息回复功能
  - 当用户发送 "test" 时回复 "测试成功"

---

**更新日期 / Last Updated**: 2025-01

**参考 / See Also**: [M_WELCOME_OPTIMIZATION.md](./M_WELCOME_OPTIMIZATION.md) - 完整的优化说明
