# 🎮 Treasure Hunt Game (寻宝游戏)

## 概述 (Overview)

这是一个为bavabot开发的寻宝游戏功能。用户可以通过`/hunt`命令开始寻宝游戏，收集碎片并合成宝物。

This is a treasure hunt game feature developed for bavabot. Users can start treasure hunt games with the `/hunt` command, collect fragments, and synthesize treasures.

## 功能特点 (Features)

### 🎯 游戏机制 (Game Mechanics)
- **开始游戏**: 使用 `/hunt` 命令免费开始游戏
- **游戏时长**: 每场游戏持续30分钟
- **寻宝动作**: 每次寻宝消耗1个金币，1秒冷却时间
- **每日限制**: 每用户每天最多5场游戏

### 🧩 碎片系统 (Fragment System)
- **碎片类型**: 6种碎片 (1-6)
- **随机获得**: 每次寻宝随机获得一个碎片
- **有效期**: 碎片仅在获得当天有效，午夜清除

### 🏆 宝物系统 (Treasure System)
- **宝物类型**: 
  - 宝物 "m": 需要碎片 1, 2, 3
  - 宝物 "l": 需要碎片 4, 5, 6
- **每日宝物**: 每天随机选择一个目标宝物
- **合成**: 收集齐所需碎片即可合成宝物

### 🎮 界面功能 (Interface Features)
- **寻宝按钮**: 进行寻宝动作
- **背包查看**: 查看当前拥有的碎片
- **合成界面**: 检查合成条件并执行合成
- **游戏结束**: 手动结束游戏或30分钟自动结束

## 数据库结构 (Database Schema)

### Hunt Table (寻宝会话表)
```sql
- id: 会话ID (Primary Key)
- tg: 用户Telegram ID
- start_time: 游戏开始时间
- end_time: 游戏结束时间
- game_date: 游戏日期
- is_active: 游戏是否进行中
- fragments_found: 找到的碎片数量
- coins_spent: 消耗的金币数量
- last_hunt_time: 上次寻宝时间
```

### Fragment Table (碎片表)
```sql
- id: 碎片ID (Primary Key)
- tg: 用户Telegram ID
- fragment_id: 碎片类型 (1-6)
- obtained_date: 获得日期
- obtained_time: 获得时间
- hunt_session_id: 对应的寻宝会话ID
```

### Treasure Table (宝物配置表)
```sql
- id: 宝物ID (Primary Key)
- treasure_name: 宝物名称
- fragment_ids: 需要的碎片ID (逗号分隔)
- description: 宝物描述
```

### DailyTreasure Table (每日宝物表)
```sql
- date: 日期 (Primary Key)
- treasure_id: 当日宝物ID
```

## 文件结构 (File Structure)

```
bot/
├── sql_helper/
│   └── sql_hunt.py              # 寻宝游戏数据库操作
├── modules/
│   └── commands/
│       ├── hunt.py              # 寻宝游戏命令和回调处理
│       └── __init__.py          # 导入寻宝命令
└── scheduler/
    ├── hunt_scheduler.py        # 寻宝游戏定时任务
    └── __init__.py             # 导入定时任务
```

## API 函数 (API Functions)

### SQL Helper Functions
- `sql_start_hunt(tg)`: 开始新的寻宝游戏
- `sql_end_hunt(hunt_id)`: 结束寻宝游戏
- `sql_get_active_hunt(tg)`: 获取用户活跃的游戏会话
- `sql_add_fragment(tg, hunt_id, fragment_id)`: 添加碎片
- `sql_get_user_fragments(tg, today_only)`: 获取用户碎片
- `sql_get_today_hunt_count(tg)`: 获取今日游戏次数
- `sql_get_daily_treasure(date)`: 获取每日宝物
- `sql_check_treasure_synthesis(tg, treasure_id)`: 检查合成条件
- `sql_synthesize_treasure(tg, treasure_id)`: 执行宝物合成
- `sql_cleanup_expired_fragments()`: 清理过期碎片

### Command Handlers
- `start_hunt()`: `/hunt` 命令处理
- `hunt_action()`: 寻宝动作回调
- `hunt_inventory()`: 背包查看回调
- `hunt_synthesis()`: 合成界面回调
- `hunt_do_synthesis()`: 执行合成回调
- `hunt_end()`: 结束游戏回调
- `hunt_game_return()`: 返回游戏回调

## 定时任务 (Scheduled Tasks)

### 自动清理任务
- **过期碎片清理**: 每天凌晨1点清理前一天的碎片
- **超时游戏清理**: 每10分钟清理超过30分钟的活跃游戏

## 使用方法 (Usage)

### 用户操作流程
1. 发送 `/hunt` 命令开始游戏
2. 点击 "🎯 寻宝" 按钮进行寻宝（消耗1金币）
3. 点击 "📦 背包" 查看收集的碎片
4. 点击 "🔧 合成" 查看合成条件
5. 收集齐所需碎片后点击 "✨ 合成" 获得宝物
6. 点击 "❌ 结束游戏" 或等待30分钟自动结束

### 游戏规则
- 每用户每天最多5场游戏
- 每次寻宝消耗1个金币
- 寻宝有1秒冷却时间
- 碎片仅当天有效
- 每日随机选择目标宝物

## 配置扩展 (Configuration & Extension)

### 添加新宝物
在 `sql_hunt.py` 的 `init_treasures()` 函数中添加新的宝物配置：

```python
treasures = [
    Treasure(treasure_name="新宝物名", fragment_ids="7,8,9", description="新宝物描述"),
    # ... 其他宝物
]
```

### 调整游戏参数
- 游戏时长: 修改 `1800` 秒 (30分钟)
- 每日限制: 修改 `5` 次
- 冷却时间: 修改 `1` 秒
- 寻宝成本: 修改 `1` 金币

## 测试 (Testing)

运行测试脚本验证功能：
```bash
python /tmp/test_hunt.py     # 基础功能测试
python /tmp/demo_hunt.py     # 游戏演示
```

## 安全考虑 (Security Considerations)

- ✅ 防止重复开始游戏
- ✅ 验证游戏会话有效性  
- ✅ 金币扣除失败时回滚
- ✅ 冷却时间防止快速点击
- ✅ 游戏超时自动结束
- ✅ 输入验证和错误处理

## 性能优化 (Performance Optimizations)

- ✅ 数据库连接池
- ✅ 事务回滚机制
- ✅ 定时清理过期数据
- ✅ 索引优化 (通过Telegram ID)
- ✅ 缓存每日宝物配置

## 日志记录 (Logging)

系统记录以下事件：
- 游戏开始/结束
- 碎片获得
- 宝物合成
- 错误和异常
- 定时清理任务

## 故障排除 (Troubleshooting)

### 常见问题
1. **数据库连接失败**: 检查数据库配置
2. **表不存在**: 确保运行了表创建代码
3. **冷却时间不生效**: 检查时间同步
4. **碎片不显示**: 检查日期格式

### 调试方法
- 检查日志文件中的错误信息
- 验证数据库表结构
- 测试各个SQL函数
- 使用提供的测试脚本

---

🎮 **寻宝游戏已准备就绪！祝您游戏愉快！**