# 测试消息回复功能说明 / Test Message Reply Feature

## 功能描述 / Feature Description

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

```python
@bot.on_message(filters.chat(group) & filters.group)
async def test_reply_handler(_, msg):
    # 只处理真实用户的文本消息
    if not msg.from_user:
        return
    
    # 检查消息内容是否为 "test"
    if msg.text and msg.text.strip().lower() == "test":
        LOGGER.info(f"【测试回复】- 用户 {msg.from_user.first_name} (ID: {msg.from_user.id}) 发送了测试消息")
        await msg.reply("测试成功")
```

### 过滤器 / Filters

- `filters.chat(group)` - 仅在授权群组中工作
- `filters.group` - 仅在群组聊天中工作
- 消息必须来自真实用户（非频道消息）
- 消息文本必须为 "test"（不区分大小写）

Filters:
- `filters.chat(group)` - Only works in authorized groups
- `filters.group` - Only works in group chats
- Messages must be from real users (not channel messages)
- Message text must be "test" (case-insensitive)

## 日志 / Logging

当用户发送测试消息时，会在日志中看到：

When a user sends a test message, you will see in the logs:

```
【测试回复】- 用户 张三 (ID: 123456789) 发送了测试消息
```

## 注意事项 / Notes

⚠️ **重要**：此功能需要关闭bot的隐私模式才能正常工作。

⚠️ **Important**: This feature requires the bot's privacy mode to be disabled to work properly.

参见 / See: [BOT_PRIVACY_MODE_SETUP.md](BOT_PRIVACY_MODE_SETUP.md)

## 版本历史 / Version History

- **2025**: 初始实现 / Initial implementation
  - 添加测试消息回复功能
  - 当用户发送 "test" 时回复 "测试成功"

---

**更新日期 / Last Updated**: 2025
