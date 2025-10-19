# F1多人游戏自动开始/取消功能

## 功能概述

为F1多人竞速游戏添加了5分钟自动开始/取消机制：

- **自动开始**：游戏发起5分钟后，如果参与人数≥2人，游戏自动开始
- **自动取消**：游戏发起5分钟后，如果参与人数<2人，游戏自动取消并退还所有参与者的5个joy币

## 实现细节

### 1. 新增常量

```python
# F1多人游戏自动开始等待时间（秒）
F1_AUTO_START_TIMEOUT = 300  # 5分钟
```

### 2. 游戏数据结构更新

在 `multiplayer_f1_games` 字典中添加了 `auto_start_task` 字段：

```python
{
    'creator': user_id,
    'participants': {user_id: {'name': str, 'clicks': int}},
    'started': bool,
    'game_active': bool,
    'chat_id': int,
    'message_id': int,
    'auto_start_task': asyncio.Task  # 新增字段
}
```

### 3. 核心函数：`auto_start_or_cancel_game()`

这个异步函数在游戏创建时启动，执行以下逻辑：

1. **等待5分钟**（300秒）
2. **检查游戏状态**：
   - 游戏是否还存在
   - 游戏是否已被手动开始
3. **判断参与人数**：
   - **≥2人**：执行自动开始流程
   - **<2人**：执行自动取消流程

#### 自动开始流程

```python
if participant_count >= 2:
    # 1. 标记游戏已开始
    game['started'] = True
    
    # 2. 显示准备提示（3秒）
    # 3. 激活游戏
    game['game_active'] = True
    
    # 4. 显示点击按钮
    # 5. 游戏运行5秒
    # 6. 调用 end_multiplayer_f1_game() 结算
```

#### 自动取消流程

```python
else:  # participant_count < 2
    # 1. 给所有参与者退款（5个joy币）
    # 2. 记录退款失败的情况（用户不在数据库）
    # 3. 更新消息显示取消信息
    # 4. 30秒后删除消息
    # 5. 取消自动任务并清理游戏数据
```

### 4. 任务管理

#### 创建任务（游戏发起时）

```python
auto_task = asyncio.create_task(auto_start_or_cancel_game(game_id))
multiplayer_f1_games[game_id]['auto_start_task'] = auto_task
```

#### 取消任务（手动开始游戏时）

```python
if game['auto_start_task'] and not game['auto_start_task'].done():
    game['auto_start_task'].cancel()
```

### 5. UI更新

#### 游戏创建时的提示

```
🏎️ **多人F1竞速赛**

🎯 发起者: XXX
💰 参与费用: 5 joy币
👥 当前玩家: 1/∞

📋 参与玩家:
1️⃣ XXX

⚠️ 至少需要2名玩家才能开始游戏
⏰ 5分钟后自动开始（满足人数）或取消（不满足人数）
🏆 获胜者将赢得所有投入的joy币！
```

#### 满足人数后的提示

```
✅ 已满足最低人数，发起者可以开始游戏
🏆 奖池: XX joy币
⏰ 5分钟后将自动开始游戏
```

#### 自动取消时的提示

```
🏎️ **多人F1竞速赛 - 已取消**

⏰ 5分钟等待时间已到
❌ 参与人数不足（需要至少2人）

📋 参与玩家:
1️⃣ XXX

💰 已退还所有参与者的 5 joy币
```

## 错误处理

### 1. 竞态条件保护

使用双重检查防止手动开始和自动开始冲突：

```python
# 第一次检查
if game['started']:
    return

# 再次检查（Python GIL保证布尔值操作的原子性）
if game['started']:
    return
```

### 2. 异常处理

```python
try:
    # 主逻辑
    ...
except asyncio.CancelledError:
    # 任务被取消（手动开始游戏时）
    pass
except Exception as e:
    # 记录其他异常
    LOGGER.error(f"【F1多人游戏】自动开始/取消任务异常 - game_id: {game_id}, error: {e}")
```

### 3. 退款失败记录

```python
refunded_count = 0
failed_refunds = []
for user_id in game['participants'].keys():
    e = sql_get_emby(user_id)
    if e:
        sql_update_emby(Emby.tg == user_id, iv=e.iv + 5)
        refunded_count += 1
    else:
        failed_refunds.append(user_id)
        LOGGER.warning(f"【F1多人游戏】退款失败，用户不在数据库 - user_id: {user_id}")
```

## 测试场景

### 场景1：自动开始（满足人数）

1. 用户A发起游戏
2. 用户B加入游戏（现在2人）
3. 等待5分钟
4. 游戏自动开始
5. 5秒后自动结束并结算

**预期结果**：游戏正常自动开始和结束

### 场景2：自动取消（不满足人数）

1. 用户A发起游戏
2. 无人加入（只有1人）
3. 等待5分钟
4. 游戏自动取消
5. 用户A获得5个joy币退款

**预期结果**：游戏取消，退款成功

### 场景3：手动开始（取消自动任务）

1. 用户A发起游戏
2. 用户B加入游戏
3. 在5分钟内，用户A点击"开始比赛"
4. 游戏手动开始
5. 自动任务被取消

**预期结果**：游戏正常手动开始，自动任务不会干扰

### 场景4：多人同时加入

1. 用户A发起游戏
2. 用户B、C、D陆续加入
3. 等待5分钟或手动开始
4. 游戏正常进行

**预期结果**：多人游戏正常运行

## 代码质量

- ✅ 语法检查通过
- ✅ CodeQL安全扫描通过（0个告警）
- ✅ 代码审查通过
- ✅ 错误处理完善
- ✅ 日志记录完整

## 兼容性

- 不影响现有单人F1游戏功能
- 不影响现有多人F1游戏的手动开始流程
- 完全向后兼容

## 修改文件

- `bot/modules/callback/checkin.py` (+154行)

## 作者

实现日期：2025-10-19
