# myinfo命令获取信息原理说明

## 概述
`myinfo` 命令是bavabot中用于查看用户个人信息的核心命令。本文档详细解释了该命令的工作原理和数据流程。

## 命令触发流程

### 1. 命令入口 (start.py)
```python
@bot.on_message(filters.command('myinfo', prefixes) & user_in_group_on_filter)
async def my_info(_, msg):
    await msg.delete()
    if msg.sender_chat:
        return
    text, keyboard = await cr_kk_ikb(uid=msg.from_user.id, first=msg.from_user.first_name)
    await sendMessage(msg, text, timer=60)
```

**关键步骤：**
- 使用过滤器确保用户在群组中并有权限使用命令
- 删除用户发送的原始命令消息（保持聊天整洁）
- 调用 `cr_kk_ikb` 函数获取用户信息和键盘按钮
- 发送格式化的用户信息，60秒后自动删除

### 2. 信息构建层 (fix_bottons.py)
```python
async def cr_kk_ikb(uid, first):
    text = ''
    text1 = ''
    keyboard = []
    data = await members_info(uid)
    # ... 信息格式化和键盘按钮构建
```

**功能职责：**
- 调用 `members_info` 获取原始用户数据
- 构建用户友好的显示文本
- 生成管理员操作按钮（如果有权限）
- 获取用户在Emby服务器上的额外信息（播放记录等）

### 3. 数据获取层 (utils.py)
```python
async def members_info(tg=None, name=None):
    if tg is None:
        tg = name
    data = sql_get_emby(tg)
    # ... 数据处理和格式化
```

**数据处理逻辑：**
- 从数据库获取用户基础信息
- 根据用户状态转换显示标签
- 计算到期时间和权限状态
- 返回格式化的用户信息元组

### 4. 数据库访问层 (sql_emby.py)
```python
def sql_get_emby(tg):
    # 根据Telegram用户ID查询数据库
    # 返回Emby表记录对象
```

## 数据库表结构

### Emby表字段说明
- `tg`: Telegram用户ID（主键）
- `embyid`: Emby服务器用户ID
- `name`: Emby账户名称
- `pwd/pwd2`: 密码信息
- `lv`: 用户等级 ('a'=白名单, 'b'=正常, 'c'=已禁用, 'd'=未注册)
- `cr`: 创建时间
- `ex`: 到期时间
- `us/iv`: 用户积分信息
- `ch`: 变更时间

## 显示信息说明

### 基础信息显示
```
**· 🍉 TG&名称** | [用户名](tg://user?id=用户ID)
**· 🍒 识别のID** | `用户ID`
**· 🍓 当前状态** | 正常/已禁用/白名单等
**· 🍥 持有积分** | 积分数量
**· 💠 账号名称** | Emby账户名
**· 🚨 到期时间** | 到期日期或永久
```

### 扩展信息（如果有播放记录）
```
**· 🔋 上次活动** | 最近播放时间
**· 📅 过去30天** | 播放时长统计
```

## 权限控制

### 用户权限检查
1. **群组成员验证**: `user_in_group_on_filter` 确保用户在指定群组中
2. **命令前缀**: 支持多种命令前缀 ('/', '!', '.', '，', '。')
3. **发送者检查**: 过滤频道消息，只处理个人用户消息

### 管理员功能
如果查看者是管理员，会显示额外的管理按钮：
- 禁用/解除禁用账户
- 删除账户
- 踢出并封禁
- 媒体库权限控制

## 性能优化

### 缓存机制
- 使用 `cacheout.Cache` 对频繁查询进行缓存
- 减少数据库访问频率

### 异步处理
- 所有数据库操作和API调用都是异步的
- 提高并发处理能力

## 错误处理

### 数据不存在处理
```python
if data is None:
    text += f'数据库中没有此ID。ta 还没有私聊过我'
```

### Emby服务器连接异常
```python
try:
    success, rep = await emby.user(emby_id=embyid)
    # ... 处理Emby数据
except (TypeError, IndexError, ValueError):
    text1 = f"**· 📅 过去30天未有记录**"
```

## 安全考虑

1. **消息自动删除**: 用户信息显示60秒后自动删除，保护隐私
2. **权限分级**: 不同权限用户看到的信息和操作按钮不同
3. **输入验证**: 对用户ID和输入参数进行验证

## 总结

`myinfo` 命令通过四层架构实现用户信息查询：
1. **命令层**: 处理Telegram消息和用户交互
2. **展示层**: 格式化信息和构建界面
3. **业务层**: 处理用户数据和权限逻辑
4. **数据层**: 数据库访问和数据持久化

这种分层设计确保了代码的可维护性、扩展性和安全性。