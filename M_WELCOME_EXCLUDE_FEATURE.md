# M尊享欢迎排除列表功能 / M-Tier Welcome Exclusion List Feature

## 功能概述 / Feature Overview

**中文：**
此功能允许管理员创建一个排除列表，在该列表中的M尊享用户将不会收到自动欢迎消息。这对于某些不希望被打扰的用户或特殊情况下很有用。

**English:**
This feature allows administrators to create an exclusion list where M-tier users in this list will not receive automatic welcome messages. This is useful for users who don't want to be disturbed or in special circumstances.

---

## 技术实现 / Technical Implementation

### 1. 配置文件 / Configuration File

在 `config.json` 中添加了新字段 `m_welcome_exclude`：

```json
{
  "m_users": [123456789, 987654321],
  "m_welcome_exclude": [111222333],
  ...
}
```

### 2. 数据流 / Data Flow

```
配置文件 (Config File)        全局变量 (Global Var)       欢迎处理 (Welcome Handler)
┌──────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│ config.json      │         │ m_welcome_exclude│        │ m_welcome.py    │
│ {                │         │ (list)          │         │                 │
│   "m_welcome_    │──load──→│ [111222333]     │──check─→│ if user_id in  │
│    exclude": [   │         │                 │         │   exclude_list:│
│     111222333    │         │                 │         │   return       │
│   ]              │         │                 │         │                 │
│ }                │         └─────────────────┘         └─────────────────┘
└──────────────────┘
```

### 3. 代码变更 / Code Changes

#### 3.1 Schema定义 (bot/schemas/schemas.py)

添加了 `m_welcome_exclude` 字段和验证器：

```python
# M尊享欢迎排除列表 (Telegram user IDs) - 在此列表中的用户不会收到欢迎消息
m_welcome_exclude: List[int] = Field(default_factory=list)

@field_validator('m_welcome_exclude', mode='before')
@classmethod
def validate_m_welcome_exclude(cls, v):
    """将 None 转换为空列表，以支持旧配置文件"""
    if v is None:
        return []
    return v
```

#### 3.2 全局变量 (bot/__init__.py)

暴露 `m_welcome_exclude` 变量：

```python
m_welcome_exclude = config.m_welcome_exclude
```

#### 3.3 欢迎处理逻辑 (bot/modules/extra/m_welcome.py)

添加排除列表检查：

```python
# 检查用户是否在排除列表中
if user_id in m_welcome_exclude:
    LOGGER.debug(f"【M尊享欢迎】- 用户 {msg.from_user.first_name} (ID: {user_id}) 在排除列表中，跳过欢迎")
    return
```

#### 3.4 管理界面 (bot/modules/panel/config_panel.py)

添加了 `manage_m_welcome_exclude` 函数，支持以下操作：
- 添加用户到排除列表：`add 123456789`
- 从排除列表移除用户：`del 123456789`
- 查看排除列表：`list`

#### 3.5 配置面板按钮 (bot/func_helper/fix_bottons.py)

在配置面板中添加了 "🚫 M欢迎排除列表" 按钮。

---

## 使用说明 / Usage Instructions

### 通过配置面板管理 / Manage via Config Panel

1. **打开配置面板 / Open Config Panel**
   - 管理员发送 `/config` 命令
   - 点击 "🚫 M欢迎排除列表" 按钮

2. **添加用户到排除列表 / Add User to Exclusion List**
   - 输入：`add 123456789`
   - Bot会确认添加成功

3. **从排除列表移除用户 / Remove User from Exclusion List**
   - 输入：`del 123456789`
   - Bot会确认移除成功

4. **查看排除列表 / View Exclusion List**
   - 输入：`list`
   - Bot会显示当前所有被排除的用户ID

### 通过配置文件管理 / Manage via Config File

也可以直接编辑 `config.json` 文件：

```json
{
  "m_welcome_exclude": [123456789, 987654321],
  ...
}
```

编辑后需要重启bot使更改生效。

---

## 工作流程 / Workflow

### 正常流程 / Normal Flow

1. M尊享用户在群组中发送文本消息
2. Bot检查用户是否在 `m_users` 列表中 ✅
3. Bot检查用户是否在 `m_welcome_exclude` 列表中 ❌
4. Bot查询数据库，检查今天是否已欢迎过
5. 发送欢迎消息并更新数据库

### 排除流程 / Exclusion Flow

1. M尊享用户在群组中发送文本消息
2. Bot检查用户是否在 `m_users` 列表中 ✅
3. Bot检查用户是否在 `m_welcome_exclude` 列表中 ✅
4. **跳过欢迎，记录日志并返回** 🚫

---

## 日志输出 / Log Output

当用户在排除列表中时，会记录DEBUG级别的日志：

```
【M尊享欢迎】- 用户 张三 (ID: 123456789) 在排除列表中，跳过欢迎
```

---

## 性能影响 / Performance Impact

**优势 / Advantages:**
- ✅ 早期返回 - 在数据库查询之前就检查排除列表
- ✅ O(1) 列表查找 - 使用Python的 `in` 操作符
- ✅ 减少不必要的数据库查询 - 被排除的用户不会触发数据库操作
- ✅ 减少不必要的消息发送 - 降低API调用次数

**影响 / Impact:**
- 对于被排除的用户，完全避免了数据库查询和消息发送
- 对于未被排除的用户，只增加了一次O(1)的列表检查，影响可忽略不计

---

## 兼容性 / Compatibility

### 向后兼容 / Backward Compatibility

✅ **完全向后兼容** - 如果配置文件中没有 `m_welcome_exclude` 字段，会自动初始化为空列表。

### 升级步骤 / Upgrade Steps

1. 更新代码到最新版本
2. 重启bot
3. （可选）在配置面板中添加需要排除的用户

**注意：** 不需要手动修改配置文件，系统会自动处理。

---

## 故障排查 / Troubleshooting

### Q: 用户已添加到排除列表，但仍然收到欢迎消息？

A: 检查以下几点：
1. ✅ 确认用户ID是否正确添加到排除列表
2. ✅ 确认是否已重启bot（如果是手动编辑配置文件）
3. ✅ 查看日志，确认是否有相关的DEBUG信息
4. ✅ 使用配置面板的 `list` 命令确认当前排除列表

### Q: 如何获取用户ID？

A: 有以下几种方法：
1. 用户可以通过给bot发送 `/myinfo` 命令查看自己的ID
2. 管理员可以通过转发用户消息给bot查看ID
3. 可以使用其他Telegram bot获取用户ID

### Q: 排除列表有数量限制吗？

A: 没有硬性限制，但建议保持在合理数量以获得最佳性能。

---

## 相关文档 / Related Documentation

- [M_WELCOME_OPTIMIZATION.md](./M_WELCOME_OPTIMIZATION.md) - M欢迎功能优化说明
- [M_USER_SYNC_FEATURE.md](./M_USER_SYNC_FEATURE.md) - M用户同步功能
- [M_WELCOME_DEBUG_GUIDE.md](./M_WELCOME_DEBUG_GUIDE.md) - 调试指南

---

**最后更新 / Last Updated**: 2025-01

**版本 / Version**: 1.0

**注意 / Note**: 此功能是M尊享欢迎系统的可选增强功能，不影响核心欢迎功能的正常运行。
