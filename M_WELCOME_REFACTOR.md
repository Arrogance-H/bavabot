# M_WELCOME 随机欢迎功能说明 / Random Welcome Feature Documentation

## 功能概述 / Feature Overview

新版本的 `m_welcome.py` 已经从原来的"M尊享用户专属欢迎"重构为"随机欢迎消息"功能。

The `m_welcome.py` has been refactored from "M-tier exclusive welcome" to a "random welcome message" feature.

### 主要变化 / Key Changes

- ✅ **任何用户都可触发** / Any user can trigger welcome messages
- ✅ **概率触发机制** / Probabilistic trigger mechanism
- ✅ **群组冷却时间** / Group-level cooldown
- ✅ **不依赖数据库** / No database dependency
- ✅ **过滤命令消息** / Filters command messages

---

## 工作原理 / How It Works

### 1. 触发条件 / Trigger Conditions

当群组中任何用户发送消息时，Bot会检查以下条件：

When any user sends a message in the group, the Bot checks:

1. **用户检查** / User Check
   - 必须是真实用户消息（非频道消息）
   - Must be a real user message (not from channel)

2. **消息类型检查** / Message Type Check
   - 跳过以 `/` 开头的命令消息
   - Skips command messages starting with `/`

3. **冷却时间检查** / Cooldown Check
   - 每个群组有独立的冷却时间（默认60分钟）
   - Each group has independent cooldown (default 60 minutes)
   - 防止频繁发送欢迎消息
   - Prevents frequent welcome messages

4. **概率检查** / Probability Check
   - 默认5%的概率发送欢迎消息
   - Default 5% probability to send welcome message
   - 使用随机数判断是否触发
   - Uses random number to determine trigger

### 2. 欢迎消息 / Welcome Message

满足所有条件后，Bot会：

After meeting all conditions, the Bot will:

- 从 `bot/func_helper/yvlu.json` 的 `m_welcome` 列表中随机选择一条欢迎语
- Randomly select a welcome message from `m_welcome` list in `bot/func_helper/yvlu.json`
- 将 `{name}` 占位符替换为发言用户的昵称
- Replace `{name}` placeholder with the speaker's name
- 回复该消息
- Reply to that message

---

## 配置参数 / Configuration Parameters

在 `bot/modules/extra/m_welcome.py` 中可以调整以下参数：

You can adjust the following parameters in `bot/modules/extra/m_welcome.py`:

```python
# 概率设置（0.0-1.0）/ Probability setting (0.0-1.0)
WELCOME_PROBABILITY = 0.05  # 5% 的概率发送欢迎消息

# 冷却时间（分钟）/ Cooldown time (minutes)
WELCOME_COOLDOWN_MINUTES = 60  # 60分钟冷却时间
```

### 调整建议 / Adjustment Recommendations

**增加触发频率 / Increase trigger frequency:**
- 提高 `WELCOME_PROBABILITY`（例如：0.1 = 10%）
- Increase `WELCOME_PROBABILITY` (e.g., 0.1 = 10%)
- 或减少 `WELCOME_COOLDOWN_MINUTES`（例如：30分钟）
- Or decrease `WELCOME_COOLDOWN_MINUTES` (e.g., 30 minutes)

**减少触发频率 / Decrease trigger frequency:**
- 降低 `WELCOME_PROBABILITY`（例如：0.02 = 2%）
- Decrease `WELCOME_PROBABILITY` (e.g., 0.02 = 2%)
- 或增加 `WELCOME_COOLDOWN_MINUTES`（例如：120分钟）
- Or increase `WELCOME_COOLDOWN_MINUTES` (e.g., 120 minutes)

---

## 与旧版本的区别 / Differences from Old Version

### 旧版本（M尊享专属）/ Old Version (M-tier Exclusive)

- ❌ 只有M等级用户发言才触发
- ❌ Only triggered by M-tier users
- ❌ 需要数据库查询和用户等级检查
- ❌ Requires database queries and level checks
- ❌ 每个用户每天只欢迎一次
- ❌ Each user welcomed once per day
- ✅ 使用数据库记录欢迎日期
- ✅ Uses database to track welcome dates

### 新版本（随机欢迎）/ New Version (Random Welcome)

- ✅ 任何用户发言都可能触发
- ✅ Any user can trigger
- ✅ 不需要数据库查询
- ✅ No database queries needed
- ✅ 使用概率和冷却时间控制频率
- ✅ Uses probability and cooldown to control frequency
- ✅ 更简洁的代码和逻辑
- ✅ Cleaner code and logic

---

## 日志说明 / Logging

### 调试日志 / Debug Logs

```
【随机欢迎】- 消息无from_user，跳过（可能是频道消息）
```
**说明**：消息来自频道，正常跳过  
**Info**: Message from channel, normally skipped

```
【随机欢迎】- 群组 -1001234567890 在冷却时间内，距离上次欢迎 30.5 分钟
```
**说明**：群组还在冷却期内，不会发送欢迎消息  
**Info**: Group is in cooldown, won't send welcome message

### 信息日志 / Info Logs

```
【随机欢迎】- 在群组 -1001234567890 向用户 张三 (ID: 123456789) 发送欢迎消息
```
**说明**：成功发送欢迎消息  
**Info**: Successfully sent welcome message

---

## 常见问题 / FAQ

### Q: 为什么很少看到欢迎消息？
### Q: Why do I rarely see welcome messages?

A: 这是正常的！默认配置下：
- 只有5%的消息会触发欢迎
- 每个群组每60分钟最多发送一次

A: This is normal! With default settings:
- Only 5% of messages trigger welcome
- Maximum once per 60 minutes per group

如果想增加频率，可以调整配置参数。

If you want to increase frequency, adjust the configuration parameters.

### Q: 能否为不同群组设置不同的参数？
### Q: Can I set different parameters for different groups?

A: 当前版本使用全局配置。如需要，可以修改代码使用字典存储不同群组的配置。

A: Current version uses global configuration. If needed, you can modify the code to use a dictionary to store different group configurations.

### Q: 如何测试功能是否正常工作？
### Q: How to test if the feature is working?

A: 可以临时修改配置增加触发概率：

A: You can temporarily modify the configuration to increase trigger probability:

```python
WELCOME_PROBABILITY = 1.0  # 100% 触发 / 100% trigger
WELCOME_COOLDOWN_MINUTES = 0  # 无冷却 / No cooldown
```

然后在群组中发送几条消息，应该每次都会收到欢迎消息。测试完成后记得改回原值。

Then send a few messages in the group, you should receive a welcome message each time. Remember to change back after testing.

### Q: 欢迎消息的内容在哪里配置？
### Q: Where is the welcome message content configured?

A: 在 `bot/func_helper/yvlu.json` 文件的 `m_welcome` 数组中。

A: In the `m_welcome` array of `bot/func_helper/yvlu.json` file.

可以添加、删除或修改欢迎消息，使用 `{name}` 作为用户昵称的占位符。

You can add, delete, or modify welcome messages, using `{name}` as a placeholder for the user's nickname.

---

## 升级指南 / Upgrade Guide

如果你从旧版本升级到新版本：

If you're upgrading from the old version:

1. **不需要数据库迁移** / No database migration needed
   - 新版本不使用 `m_welcome_date` 字段
   - New version doesn't use `m_welcome_date` field

2. **配置调整** / Configuration adjustment
   - 根据需要调整 `WELCOME_PROBABILITY` 和 `WELCOME_COOLDOWN_MINUTES`
   - Adjust `WELCOME_PROBABILITY` and `WELCOME_COOLDOWN_MINUTES` as needed

3. **功能验证** / Feature verification
   - 启用DEBUG日志查看触发情况
   - Enable DEBUG logging to see trigger status
   - 在群组中发送消息测试
   - Send messages in group to test

---

## 相关文件 / Related Files

- **代码文件** / Code file: `bot/modules/extra/m_welcome.py`
- **欢迎消息配置** / Welcome messages: `bot/func_helper/yvlu.json`
- **日志配置** / Logging config: `bot/func_helper/logger_config.py`

---

**更新日期 / Last Updated**: 2025-01-XX  
**版本 / Version**: 2.0 (随机欢迎版本 / Random Welcome Version)
