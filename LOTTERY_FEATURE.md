# 抽奖系统功能说明 (Lottery System Feature Documentation)

## 新增功能 (New Feature)

本次更新为 bavabot 新增了完整的抽奖系统，支持管理员创建多种类型的抽奖活动，用户可以通过群组参与并获得奖品。

## 主要特性 (Key Features)

### 🎯 多种抽奖模式
- **免费抽奖** - 用户免费参与
- **付费抽奖** - 消耗指定数量的币参与  
- **emby专享** - 限制拥有emby账号的用户参与
- **群组限制** - 只有在TG群组中的用户才能参与

### ⏰ 灵活开奖方式
- **定时开奖** - 指定时间自动开奖
- **人数开奖** - 达到指定参与人数自动开奖
- **手动开奖** - 管理员可随时手动执行开奖

### 🎁 多样化奖品
- **币奖励** - 自动发放到用户账户
- **其他奖品** - 需要联系管理员领取
- **自定义数量** - 每种奖品可设置不同数量

### ⚖️ 公平性保证
- **真随机算法** - 确保所有参与者获奖概率相等
- **单次中奖限制** - 每人在同一抽奖中最多中奖一次
- **透明过程** - 完整的操作日志和审计记录

## 用户命令 (User Commands)

| 命令 | 功能 | 使用范围 |
|------|------|----------|
| `/lottery` | 查看当前抽奖列表 | 群组用户 |
| `/my_lottery` | 查看我的抽奖状态 | 群组用户 |

## 管理员命令 (Admin Commands)

| 命令 | 功能 | 参数说明 |
|------|------|----------|
| `/lottery_create` | 创建抽奖 | 标题\|描述\|模式\|开奖方式 |
| `/lottery_add_prize` | 添加奖品 | 抽奖ID 奖品名\|类型\|价值\|数量 |
| `/lottery_manage` | 管理抽奖面板 | 无参数 |
| `/lottery_draw` | 手动开奖 | 抽奖ID |
| `/lottery_list_all` | 查看所有抽奖 | 无参数 |

## 配置示例 (Configuration Example)

在 `config.json` 中添加抽奖系统配置：

```json
{
  "lottery": {
    "status": true,
    "default_max_participants": 100,
    "default_cost": 10,
    "allow_free_lottery": true,
    "auto_draw": true,
    "admin_only_create": true
  }
}
```

## 使用示例 (Usage Examples)

### 创建免费抽奖
```bash
/lottery_create 新年抽奖 | 新年快乐，送花币啦！ | free,emby:true | time:2024-01-01 12:00
```

### 创建付费抽奖
```bash
/lottery_create 会员专享 | 高价值奖品抽奖 | cost:50,emby:true | count:20
```

### 添加奖品
```bash
# 添加币奖励
/lottery_add_prize 1 一等奖 | coins | 1000 | 1 | 大额花币奖励

# 添加其他奖品  
/lottery_add_prize 1 二等奖 | other | 永久会员 | 2 | 联系管理员领取
```

## 数据库变更 (Database Changes)

新增以下数据表：
- `lottery` - 抽奖基本信息
- `lottery_prize` - 奖品配置
- `lottery_participant` - 参与记录
- `lottery_winner` - 中奖记录

## 安装和更新 (Installation & Update)

1. 拉取最新代码
2. 更新配置文件（参考 `config_example_with_lottery.json`）
3. 重启 bot
4. 数据库表会自动创建

## 注意事项 (Important Notes)

- 抽奖系统默认关闭，需要在配置中启用
- 确保数据库有足够权限创建新表
- 建议在测试环境先验证功能
- 自动开奖需要调度器正常运行

## 更多信息 (More Information)

详细使用说明请参考 [LOTTERY_MANUAL.md](LOTTERY_MANUAL.md)