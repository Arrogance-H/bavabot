# 🏎️ Garage Game (车库游戏)

## 概述 (Overview)

这是一个为bavabot开发的车库游戏功能。用户可以通过`/hunt`命令开始车库游戏，收集装备并组装BMW M系列汽车。

This is a garage game feature developed for bavabot. Users can start garage games with the `/hunt` command, collect equipment, and assemble BMW M-series cars.

## 功能特点 (Features)

### 🎯 游戏机制 (Game Mechanics)
- **开始游戏**: 使用 `/hunt` 命令免费开始游戏
- **游戏时长**: 每场游戏持续30分钟
- **寻找装备**: 每次寻找消耗1个金币，1秒冷却时间
- **每日限制**: 每用户每天最多5场游戏
- **背包容量**: 最多存放30个装备

### 🔧 装备系统 (Equipment System)
- **装备类别**: 按稀有度分为四类（蓝、绿、金、紫）
- **随机获得**: 每次寻找根据稀有度权重随机获得装备
- **选择机制**: 获得装备后可选择保留或丢弃
- **有效期**: 装备仅在获得当天有效，午夜清除

### 🏎️ 汽车系统 (Car System)
- **汽车类型**: 
  - 赞德福特蓝M2: 需要 S58发动机, 碳陶瓷刹车系统, 赤金色轮毂, 磨砂纯灰车漆, 赞德福特蓝车漆
  - 曼岛绿M3: 需要 S58发动机, xDrive智能全轮驱动系统, 碳纤维赛道桶椅, 曼岛绿车漆, 布鲁克林灰车漆
  - 圣保罗黄M4: 需要 S58发动机, 主动M差速器, M精英驾驶模式, 圣保罗黄车漆, 多伦多红车漆
  - 风暴灰M5: 需要 V8双涡轮增压发动机, 自适应M运动悬架, 整体主动转向系统, 风暴灰车漆, 海滨湾蓝车漆
- **每日汽车**: 每天随机选择一个目标汽车
- **组装**: 收集齐所需装备即可组装汽车

### 🎨 装备稀有度 (Equipment Rarity)
- **🔵 蓝色装备** (最常见): 98#汽油, 玻璃水, 车钥匙, 漏气的轮胎, 空气, 空调滤芯, 刹车盘
- **🟢 绿色装备** (常见): 磨砂纯灰车漆, 布鲁克林灰车漆, 多伦多红车漆, 海滨湾蓝车漆
- **🟡 金色装备** (稀有): S58发动机, 赤金色轮毂, xDrive智能全轮驱动系统, 碳纤维赛道桶椅, 主动M差速器, V8双涡轮增压发动机, 自适应M运动悬架
- **🟣 紫色装备** (最稀有): 赞德福特蓝车漆, 曼岛绿车漆, 圣保罗黄车漆, 风暴灰车漆

### 🎮 界面功能 (Interface Features)
- **寻找装备按钮**: 进行寻找装备动作
- **背包查看**: 查看当前拥有的装备
- **组装界面**: 检查组装条件并执行组装
- **装备选择**: 获得装备时选择保留或丢弃
- **游戏结束**: 手动结束游戏或30分钟自动结束

## 数据库结构 (Database Schema)

### Hunt Table (车库会话表)
```sql
- id: 会话ID (Primary Key)
- tg: 用户Telegram ID
- start_time: 游戏开始时间
- end_time: 游戏结束时间
- game_date: 游戏日期
- is_active: 游戏是否进行中
- equipment_found: 找到的装备数量
- coins_spent: 消耗的金币数量
- last_hunt_time: 上次寻找时间
```

### Equipment Table (装备表)
```sql
- id: 装备ID (Primary Key)
- tg: 用户Telegram ID
- equipment_id: 装备类型ID
- obtained_date: 获得日期
- obtained_time: 获得时间
- hunt_session_id: 对应的车库会话ID
```

### EquipmentDefinition Table (装备定义表)
```sql
- equipment_id: 装备类型ID (Primary Key)
- equipment_name: 装备名称
- description: 装备描述
- category: 装备类别 (blue/green/gold/purple)
- rarity_weight: 稀有度权重
```

### Car Table (汽车配置表)
```sql
- id: 汽车ID (Primary Key)
- car_name: 汽车名称
- equipment_ids: 需要的装备ID (逗号分隔)
- description: 汽车描述
```

### DailyCar Table (每日汽车表)
```sql
- date: 日期 (Primary Key)
- car_id: 当日汽车ID
```

## 文件结构 (File Structure)

```
bot/
├── sql_helper/
│   └── sql_hunt.py              # 车库游戏数据库操作
├── modules/
│   └── commands/
│       ├── hunt.py              # 车库游戏命令和回调处理
│       └── __init__.py          # 导入车库命令
└── scheduler/
    ├── hunt_scheduler.py        # 车库游戏定时任务
    └── __init__.py             # 导入定时任务
```

## API 函数 (API Functions)

### SQL Helper Functions
- `sql_start_hunt(tg)`: 开始新的车库游戏
- `sql_end_hunt(hunt_id)`: 结束车库游戏
- `sql_get_active_hunt(tg)`: 获取用户活跃的游戏会话
- `sql_add_equipment(tg, hunt_id, equipment_id)`: 添加装备
- `sql_get_user_equipment(tg, today_only)`: 获取用户装备
- `sql_get_today_hunt_count(tg)`: 获取今日游戏次数
- `sql_get_daily_car(date)`: 获取每日汽车
- `sql_check_car_assembly(tg, car_id)`: 检查组装条件
- `sql_assemble_car(tg, car_id)`: 执行汽车组装
- `sql_cleanup_expired_equipment()`: 清理过期装备
- `sql_random_equipment_by_rarity()`: 按稀有度随机选择装备

### Command Handlers
- `start_hunt()`: `/hunt` 命令处理
- `hunt_action()`: 寻找装备动作回调
- `keep_equipment()`: 保留装备回调
- `discard_equipment()`: 丢弃装备回调
- `hunt_inventory()`: 背包查看回调
- `hunt_assembly()`: 组装界面回调
- `hunt_do_assembly()`: 执行组装回调
- `hunt_end()`: 结束游戏回调
- `hunt_game_return()`: 返回游戏回调

## 定时任务 (Scheduled Tasks)

### 自动清理任务
- **过期装备清理**: 每天凌晨1点清理前一天的装备
- **超时游戏清理**: 每10分钟清理超过30分钟的活跃游戏

## 使用方法 (Usage)

### 用户操作流程
1. 发送 `/hunt` 命令开始游戏
2. 点击 "🔍 寻找装备" 按钮进行寻找（消耗1金币）
3. 选择保留或丢弃获得的装备
4. 点击 "🎒 背包" 查看收集的装备
5. 点击 "🔧 组装" 查看组装条件
6. 收集齐所需装备后点击 "✨ 组装" 获得汽车
7. 点击 "❌ 结束游戏" 或等待30分钟自动结束

### 游戏规则
- 每用户每天最多5场游戏
- 每次寻找消耗1个金币
- 寻找有1秒冷却时间
- 装备仅当天有效
- 背包最多存放30个装备
- 获得装备时可选择保留或丢弃
- 每日随机选择目标汽车

## 配置扩展 (Configuration & Extension)

### 添加新汽车
在 `sql_hunt.py` 的 `init_cars_and_equipment()` 函数中添加新的汽车配置：

```python
cars = [
    Car(car_name="新汽车名", equipment_ids="25,26,27", description="新汽车描述"),
    # ... 其他汽车
]
```

### 添加新装备
在装备定义中添加新装备：

```python
EquipmentDefinition(equipment_id=26, equipment_name="新装备", description="描述", category="blue", rarity_weight=10)
```

### 调整游戏参数
- 游戏时长: 修改 `1800` 秒 (30分钟)
- 每日限制: 修改 `5` 次
- 冷却时间: 修改 `1` 秒
- 寻找成本: 修改 `1` 金币
- 背包容量: 修改 `30` 个装备

### 调整装备稀有度
修改 `rarity_weight` 参数：
- 数值越大，获得概率越高
- 蓝色装备: 权重 10 (最常见)
- 绿色装备: 权重 6
- 金色装备: 权重 3
- 紫色装备: 权重 1 (最稀有)

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

🏎️ **车库游戏已准备就绪！祝您游戏愉快！**