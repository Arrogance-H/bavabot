# myinfo命令数据流程图

## 整体架构流程

```
用户发送 /myinfo 命令
           ↓
    [1. 命令入口层]
    bot/modules/commands/start.py
    - my_info() 函数
    - 删除原始消息
    - 验证用户权限
           ↓
    [2. 信息构建层]
    bot/func_helper/fix_bottons.py
    - cr_kk_ikb() 函数
    - 格式化显示文本
    - 构建操作按钮
           ↓
    [3. 数据获取层]
    bot/func_helper/utils.py
    - members_info() 函数
    - 处理用户状态
    - 转换显示格式
           ↓
    [4. 数据库访问层]
    bot/sql_helper/sql_emby.py
    - sql_get_emby() 函数
    - MySQL数据库查询
           ↓
    [5. 外部服务层]
    Emby媒体服务器
    - 用户播放统计
    - 媒体库权限信息
           ↓
    格式化的用户信息返回给用户
```

## 详细数据流程

### 第一步：命令接收
```python
# 用户输入: /myinfo
@bot.on_message(filters.command('myinfo', prefixes) & user_in_group_on_filter)
async def my_info(_, msg):
    # 提取数据:
    # - msg.from_user.id (用户TG ID)
    # - msg.from_user.first_name (用户名)
```

### 第二步：权限验证
```python
# 过滤器检查:
# - user_in_group_on_filter: 确保用户在群组中
# - filters.command('myinfo', prefixes): 匹配命令格式
# - 排除频道消息: if msg.sender_chat: return
```

### 第三步：数据查询链
```python
# 调用链:
my_info() 
    → cr_kk_ikb(uid, first_name)
        → members_info(tg_id)
            → sql_get_emby(tg_id)
                → 数据库查询
```

### 第四步：数据处理
```python
# 数据库返回字段:
{
    'tg': 123456789,              # Telegram用户ID
    'embyid': 'emby_user_123',    # Emby服务器用户ID
    'name': 'user_account',       # Emby账户名
    'lv': 'b',                    # 用户等级 (a/b/c/d)
    'iv': 100,                    # 用户积分
    'ex': '2024-12-31',          # 到期时间
    'pwd2': 'password'            # 用户密码
}

# 转换为显示格式:
{
    'name': 'user_account',
    'lv': '**正常**',             # 'b' → '**正常**'
    'ex': '2024-12-31',
    'iv': 100,
    'embyid': 'emby_user_123',
    'pwd2': 'password'
}
```

### 第五步：Emby服务器查询
```python
# 如果用户有Emby账户，额外查询:
# 1. 媒体库权限: emby.user(emby_id=embyid)
# 2. 播放统计: emby.emby_cust_commit(emby_id=embyid, days=30)

# 返回数据:
{
    'last_activity': '2024-01-15 10:30:00',  # 最后播放时间
    'total_minutes': 1200,                   # 30天播放时长
    'blocked_libraries': ['额外库1', '额外库2'] # 被阻止的媒体库
}
```

### 第六步：文本格式化
```python
# 生成显示文本:
text = f"""
**· 🍉 TG&名称** | [用户名](tg://user?id={uid})
**· 🍒 识别のID** | `{uid}`
**· 🍓 当前状态** | {lv}
**· 🍥 持有积分** | {iv}
**· 💠 账号名称** | {name}
**· 🚨 到期时间** | **{ex}**
**· 🔋 上次活动** | {last_time}
**· 📅 过去30天** | {total_minutes} 分钟
"""
```

### 第七步：按钮生成
```python
# 根据用户状态和权限生成操作按钮:
keyboard = [
    ['🌟 解除禁用' | '💢 禁用账户', f'user_ban-{uid}'],
    ['⚠️ 删除账户', f'closeemby-{uid}'],
    ['✔️ 额外媒体库', f'embyextralib_block-{uid}'],
    ['🚫 踢出并封禁', f'fuckoff-{uid}'],
    ['❌ 删除消息', f'closeit']
]
```

### 第八步：消息发送
```python
# 发送格式化消息:
await sendMessage(msg, text, timer=60)
# - text: 格式化的用户信息
# - timer=60: 60秒后自动删除保护隐私
```

## 错误处理流程

### 用户不存在
```
sql_get_emby(tg) → None
    ↓
members_info() → None
    ↓
cr_kk_ikb() → "数据库中没有此ID。ta 还没有私聊过我"
```

### Emby服务器连接失败
```
emby.user() → Exception
    ↓
跳过媒体库权限检查
    ↓
emby.emby_cust_commit() → Exception
    ↓
显示 "过去30天未有记录"
```

### 权限不足
```
user_in_group_on_filter → False
    ↓
命令不会被处理，直接忽略
```

## 性能优化点

1. **异步处理**: 所有数据库和API调用都是异步的
2. **缓存机制**: members_info函数支持缓存装饰器
3. **批量查询**: 可以一次性获取多个用户信息
4. **连接池**: 数据库连接使用连接池管理
5. **错误恢复**: 单个服务失败不影响基础信息显示

## 安全机制

1. **权限验证**: 多层权限检查
2. **消息清理**: 自动删除敏感信息
3. **输入验证**: 防止SQL注入和恶意输入
4. **访问控制**: 不同用户看到不同的操作按钮