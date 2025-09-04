# CodeLottery Docker 部署指南

## 📋 概述

CodeLottery 是一个基于时间的抽奖系统，支持在 Docker 环境中运行。本文档详细说明了如何在 Docker 环境下部署和测试 CodeLottery 系统。

## 🎯 系统特点

- **时间制抽奖**: 固定30分钟抽奖时间，到期自动开奖
- **用户限制**: 仅限 `lv='c'` 用户参与
- **参与费用**: 每次参与需支付 3 花币
- **保底机制**: 累计参与 10 次保证获奖
- **管理员控制**: 支持手动开启/停止抽奖
- **自动通知**: 获奖者私信通知 + 群组公告

## 🐳 Docker 环境部署

### 1. 配置文件准备

确保 `config.json` 包含以下 CodeLottery 配置：

```json
{
  "code_lottery": {
    "status": false,
    "admin_only": true,
    "entry_fee": 3,
    "guaranteed_win_count": 10,
    "lottery_name": "ME注册资格",
    "duration_minutes": 30,
    "winner_count": 1
  },
  "db_is_docker": true,
  "db_docker_name": "mysql",
  "db_host": "localhost",
  "db_port": 3306,
  "db_user": "your_user",
  "db_pwd": "your_password",
  "db_name": "your_database"
}
```

### 2. Docker Compose 启动

```bash
# 启动 MySQL 数据库（如果需要）
docker-compose up -d mysql

# 启动 Bot
docker-compose up -d bavabot
```

### 3. 数据库表创建

CodeLottery 系统会自动创建以下数据库表：

- `code_lottery_users` - 用户参与记录
- `code_lottery_rounds` - 抽奖轮次信息  
- `code_lottery_participants` - 参与者记录
- `code_lottery_winners` - 获奖者记录

## 🧪 测试数据库连接

### 方法1: 使用Docker测试脚本

```bash
# 在容器内运行测试
docker exec -it bavabot python3 test_docker_db_connection.py

# 或者运行完整测试
docker exec -it bavabot python3 test_docker_codelottery.py
```

### 方法2: 手动测试数据库连接

```bash
# 检查MySQL容器状态
docker ps | grep mysql

# 测试数据库连接
docker exec -it mysql mysql -u your_user -p your_database -e "SHOW TABLES;"

# 检查CodeLottery表
docker exec -it mysql mysql -u your_user -p your_database -e "SHOW TABLES LIKE 'code_lottery%';"
```

### 方法3: 使用Python测试脚本

如果已安装依赖，可直接运行：

```bash
python3 test_codelottery_database.py
```

## 🎮 使用方法

### 管理员命令

```bash
/codelottery_start  # 开启新的抽奖轮次
/codelottery_stop   # 停止当前抽奖轮次  
/codelottery_stats  # 查看抽奖统计信息
```

### 用户命令

```bash
/codelottery_stats  # 查看个人抽奖统计
```

### 参与抽奖

用户通过点击抽奖信息中的「参与抽奖」按钮参与。

## 📊 抽奖信息显示

```
🎉 ME注册资格 🎉

📅 第 1 次开启抽奖
⏰ 抽奖时间：30 分钟
💰 参与费用：3 花币
🏆 获奖人数：1 人
🔑 参与条件：仅限lv=c用户

📊 当前参与人数：45 人
⏱️ 剩余时间：15分32秒
```

## 🎊 自动开奖结果

```
🎊 开奖结果 🎊

🎲 抽奖名称：ME注册资格
📅 轮次：第1次
⏰ 时间到期自动开奖
👥 参与人数：100人
🏆 获奖人数：1人

🎉 获奖名单 🎉
1. 张三 (累计参与12次)

🎁 获奖者请联系me领奖
```

## 🔧 故障排除

### 数据库连接问题

1. **检查MySQL容器状态**:
   ```bash
   docker ps | grep mysql
   docker logs mysql
   ```

2. **检查网络连接**:
   ```bash
   docker exec -it bavabot ping mysql
   ```

3. **检查配置文件**:
   ```bash
   docker exec -it bavabot cat /app/config.json | grep -A 10 "db_"
   ```

### 表创建问题

1. **手动创建表**:
   ```bash
   docker exec -it bavabot python3 -c "from bot.sql_helper.sql_codelottery import *; print('Tables created')"
   ```

2. **检查表结构**:
   ```bash
   docker exec -it mysql mysql -u user -p database -e "DESCRIBE code_lottery_users;"
   ```

### 调度器问题

1. **检查日志**:
   ```bash
   docker logs bavabot | grep "抽奖定时"
   ```

2. **检查配置**:
   确保 `config.json` 中 `code_lottery.status` 为 `true`

## 📝 监控和日志

### 查看系统日志

```bash
# Bot 主日志
docker logs -f bavabot

# 抽奖相关日志
docker logs bavabot | grep "抽奖"

# 数据库日志  
docker logs mysql
```

### 监控抽奖状态

```bash
# 检查活跃抽奖
docker exec -it mysql mysql -u user -p database -e "SELECT * FROM code_lottery_rounds WHERE status='active';"

# 检查参与统计
docker exec -it mysql mysql -u user -p database -e "SELECT COUNT(*) as total_users FROM code_lottery_users;"
```

## 🔒 安全建议

1. **数据库密码**: 使用强密码并定期更换
2. **网络隔离**: 考虑使用自定义Docker网络
3. **数据备份**: 定期备份数据库
4. **日志轮转**: 配置日志轮转避免磁盘占满

## 📚 相关文档

- [CODELOTTERY_README.md](./CODELOTTERY_README.md) - 系统功能详细说明
- [config_example.json](./config_example.json) - 配置文件示例
- [docker-compose.yml](./docker-compose.yml) - Docker部署配置

## ❓ 常见问题

**Q: 为什么抽奖系统不自动开启？**
A: 需要在配置文件中设置 `code_lottery.status: true` 并重启容器。

**Q: 如何修改抽奖时间？**
A: 修改配置文件中的 `code_lottery.duration_minutes` 值并重启。

**Q: 用户无法参与抽奖？**
A: 检查用户等级是否为 'c'，以及是否有足够的花币。

**Q: 获奖通知没有发送？**
A: 检查用户是否已私聊机器人，以及Bot权限设置。