# 抽奖系统 (CodeLottery System)

## 概述

本抽奖系统为 bavabot 实现了一个完整的时间制抽奖功能，支持用户等级限制、费用控制、保底机制等特性。

## 主要功能

### 🎯 核心特性
- **群组成员限制**: 只有群组成员可参与抽奖
- **时间制抽奖**: 可自定义开奖时间（默认30分钟）
- **等概率抽奖**: 保证每位参与者中奖概率相同
- **保底机制**: 连续参与10次未中奖必中下次
- **费用控制**: 需要注册账户并支付参与费用（默认3花币）
- **管理员控制**: 支持手动开启/停止抽奖

### 🤖 命令支持
- `/codelottery_start [名称] [时长分钟]` - 开启新抽奖（管理员）
- `/codelottery_stop` - 停止当前抽奖（管理员）
- `/codelottery_stats` - 查看个人抽奖统计（所有用户）

### 📊 数据库设计

#### 数据表结构
1. **code_lottery_rounds** - 抽奖轮次表
2. **code_lottery_participants** - 参与者记录表
3. **code_lottery_winners** - 获奖者记录表
4. **code_lottery_users** - 用户统计表

#### 字段说明
```sql
-- 抽奖轮次表
CREATE TABLE code_lottery_rounds (
    id INT AUTO_INCREMENT PRIMARY KEY,
    lottery_name VARCHAR(200) NOT NULL,
    creator_tg BIGINT NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    entry_fee INT DEFAULT 3,
    winner_count INT DEFAULT 1,
    status VARCHAR(20) DEFAULT 'active',
    draw_time DATETIME NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 使用方法

### 1. 系统配置
在 `config.json` 中启用抽奖系统：
```json
{
  "code_lottery": {
    "status": true,
    "admin_only": true,
    "entry_fee": 3,
    "guaranteed_win_count": 10,
    "lottery_name": "ME注册资格",
    "duration_minutes": 30,
    "winner_count": 1
  }
}
```

### 2. 开启抽奖
管理员使用命令：
```
/codelottery_start [奖品名称] [持续分钟数]
```
例如：
```
/codelottery_start ME注册资格 30
```

### 3. 用户参与
- 只有群组成员可以参与
- 用户需要注册账户并有足够的花币（默认3个）
- 点击群组中的"参与抽奖"按钮即可

### 4. 自动开奖
- 系统每分钟检查一次过期的抽奖
- 到达设定时间后自动开奖
- 通知获奖者（私信+群组公告）

### 5. 保底机制
- 用户连续参与10次未中奖后，下次必中
- 保底用户优先于普通用户获奖
- 中奖后保底次数重置为0

## 技术实现

### 文件结构
```
bot/
├── sql_helper/
│   └── sql_codelottery.py          # 数据库操作
├── modules/commands/
│   └── codelottery.py              # 命令处理
├── scheduler/
│   └── codelottery_scheduler.py    # 自动开奖调度
└── schemas/
    └── schemas.py                  # 配置模式（更新）
```

### 关键函数

#### SQL 操作
- `sql_create_lottery_round()` - 创建抽奖轮次
- `sql_join_lottery()` - 用户参与抽奖
- `sql_draw_lottery()` - 执行抽奖
- `sql_get_lottery_stats()` - 获取用户统计

#### 命令处理
- `start_codelottery_command()` - 处理开启抽奖命令
- `stop_codelottery_command()` - 处理停止抽奖命令
- `handle_join_lottery()` - 处理参与抽奖回调

#### 调度器
- `auto_draw_expired_lotteries()` - 自动检查并开奖过期抽奖
- `process_lottery_draw()` - 处理单个抽奖的开奖流程

## 安全特性

### 权限控制
- 抽奖开启/停止仅管理员可操作
- 用户等级严格验证
- 重复参与检测

### 数据保护
- 事务处理确保数据一致性
- 异常处理防止系统崩溃
- 日志记录所有关键操作

### 防作弊机制
- 每人每轮次只能参与一次
- 花币扣除防止重复参与
- 保底机制基于历史记录

## 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `status` | `false` | 是否启用抽奖系统 |
| `admin_only` | `true` | 是否仅管理员可控制 |
| `entry_fee` | `3` | 参与费用（花币） |
| `guaranteed_win_count` | `10` | 保底中奖次数 |
| `lottery_name` | `"ME注册资格"` | 默认抽奖名称 |
| `duration_minutes` | `30` | 默认持续时间（分钟） |
| `winner_count` | `1` | 每次抽奖获奖人数 |

## 监控和维护

### 日志记录
系统会记录以下关键事件：
- 抽奖创建/停止
- 用户参与情况
- 开奖结果
- 异常错误

### 数据统计
可通过以下方式查看系统状态：
- 用户个人统计：`/codelottery_stats`
- 数据库直接查询各表记录

### 故障排除
1. **无法参与抽奖**
   - 检查是否为群组成员
   - 检查是否有注册账户
   - 检查花币余额是否足够
   - 检查是否已经参与过

2. **自动开奖不工作**
   - 检查调度器是否启用
   - 查看系统日志错误信息
   - 确认数据库连接正常

3. **通知发送失败**
   - 检查机器人权限
   - 确认群组配置正确
   - 用户可能禁用了私信

## 扩展说明

### 添加新奖品类型
修改 `CodeLotteryRound` 模型，增加奖品类型字段。

### 自定义中奖规则
在 `sql_draw_lottery()` 函数中修改抽奖逻辑。

### 增加通知方式
在 `codelottery_scheduler.py` 中扩展通知函数。

## 版本历史

- **v1.0** - 基础抽奖功能实现
  - 时间制抽奖
  - 用户等级限制
  - 保底机制
  - 管理员控制
  - 自动开奖调度