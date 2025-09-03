# 🔧 Hunt Database Reconstruction Guide / 寻宝游戏数据库重构指南

## 问题描述 (Problem Description)

当您看到此消息时，说明寻宝游戏的数据库结构需要重构以兼容当前的游戏代码：

```
❌ 数据库已修复，但游戏启动仍失败

🔧 请管理员运行数据库重构脚本：
python3 reconstruct_hunt_database.py --backup

或查看 HUNT_RECONSTRUCTION_README.md 获取详细说明
```

这表明数据库表结构与当前代码不兼容，需要完全重构数据库。

When you see this message, it means the hunt game database structure needs to be reconstructed to be compatible with the current game code.

## 快速解决方案 (Quick Solution)

### 方法一：自动重构（推荐）

```bash
cd /path/to/bavabot
python3 reconstruct_hunt_database.py --backup
```

### 方法二：独立脚本重构（如果依赖有问题）

如果主脚本因为依赖问题失败，使用独立版本：

```bash
# 使用配置文件
python3 reconstruct_hunt_database_standalone.py --config --backup

# 或手动指定数据库参数
python3 reconstruct_hunt_database_standalone.py --host localhost --user root --password yourpass --database bavabot --backup
```

### 方法三：强制重构

如果已存在表格但需要重构：

```bash
python3 reconstruct_hunt_database.py --backup --force
# 或
python3 reconstruct_hunt_database_standalone.py --config --backup --force
```

## 详细步骤 (Detailed Steps)

### 1. 确认环境

确保您在bavabot项目的根目录下：

```bash
cd /path/to/bavabot
ls -la reconstruct_hunt_database.py  # 应该存在此文件
```

### 2. 检查配置

确保 `config.json` 文件存在且包含正确的数据库配置：

```json
{
  "db_host": "localhost",
  "db_port": 3306,
  "db_user": "your_username",
  "db_pwd": "your_password",
  "db_name": "your_database"
}
```

### 3. 运行重构脚本

#### 带备份的重构（强烈推荐）

```bash
python3 reconstruct_hunt_database.py --backup
```

此命令会：
- ✅ 创建当前数据库的备份
- ✅ 删除旧的寻宝游戏表
- ✅ 创建新的兼容表结构
- ✅ 初始化默认游戏数据
- ✅ 验证数据库结构
- ✅ 测试基本功能

#### 不备份的重构

```bash
python3 reconstruct_hunt_database.py
```

#### 强制重构（覆盖现有表）

```bash
python3 reconstruct_hunt_database.py --backup --force
```

### 4. 验证结果

重构完成后，您应该看到：

```
==================================================
✅ Hunt database reconstruction completed successfully!

🎮 The hunt game should now be fully functional.
You can now start the bot and test the /hunt command.

💡 If you encounter any issues, check the bot logs for detailed error messages.
```

## 命令选项说明 (Command Options)

| 选项 | 说明 |
|------|------|
| `--backup` | 在重构前创建数据库备份（强烈推荐） |
| `--force` | 强制重构，即使表已存在 |
| `--help` | 显示帮助信息 |

## 重构后的表结构 (Reconstructed Table Structure)

重构完成后将创建以下表：

### 核心游戏表

1. **hunt** - 寻宝游戏会话表
   - 存储游戏会话信息
   - 包含用户ID、开始时间、游戏状态等

2. **equipment** - 装备表
   - 存储用户获得的装备
   - 关联到游戏会话

3. **equipment_definition** - 装备定义表
   - 装备类型和属性定义
   - 稀有度权重配置

4. **car** - 汽车配置表
   - 汽车类型和所需装备
   - 汽车描述信息

5. **daily_car** - 每日汽车表
   - 每日随机汽车配置

### 奖励系统表

6. **assembly_reward** - 组装奖励记录表
7. **reward_config** - 奖励配置表
8. **reward_button** - 自定义奖励按钮表

## 故障排除 (Troubleshooting)

### 依赖问题

如果遇到依赖问题：

```bash
pip install sqlalchemy pymysql
```

如果pip安装失败，使用独立脚本：

```bash
python3 reconstruct_hunt_database_standalone.py --config --backup
```

独立脚本使用Python内置的数据库连接，不需要额外依赖。

### 权限问题

确保数据库用户有以下权限：
- CREATE
- DROP
- INSERT
- UPDATE
- DELETE
- SELECT

### 配置文件问题

如果配置文件不存在或格式错误：

1. 检查 `config.json` 是否存在
2. 验证JSON格式是否正确
3. 确认数据库连接参数

### 连接问题

如果数据库连接失败：

1. 检查数据库服务是否运行
2. 验证连接参数（主机、端口、用户名、密码）
3. 确认网络连接

## 备份恢复 (Backup Recovery)

如果需要恢复备份：

```bash
# 找到备份文件
ls -la hunt_database_backup_*.sql

# 恢复备份（替换为实际备份文件名）
mysql -u username -p database_name < hunt_database_backup_20240101_120000.sql
```

## 手动验证 (Manual Verification)

重构完成后，您可以手动验证：

```sql
-- 检查表是否存在
SHOW TABLES LIKE '%hunt%';
SHOW TABLES LIKE '%equipment%';
SHOW TABLES LIKE '%car%';

-- 检查hunt表结构
DESCRIBE hunt;

-- 验证关键列存在
SELECT hunt_actions, daily_car_info FROM hunt LIMIT 1;
```

## 常见问题 (FAQ)

### Q: 重构会丢失数据吗？
A: 使用 `--backup` 选项会先创建备份。重构过程会删除旧表并创建新表，所以历史游戏数据会丢失，但可以从备份恢复。

### Q: 可以在生产环境运行吗？
A: 建议先在测试环境验证。生产环境务必使用 `--backup` 选项。

### Q: 重构需要多长时间？
A: 通常在几秒到几分钟内完成，取决于数据库大小和连接速度。

### Q: 重构失败怎么办？
A: 检查错误信息，确认数据库连接和权限。如有备份可以恢复后重试。

## 技术支持 (Technical Support)

如果遇到问题：

1. 检查bot日志文件中的详细错误信息
2. 确认数据库连接和权限
3. 验证配置文件格式
4. 查看重构脚本的错误输出

## 相关文件 (Related Files)

- `reconstruct_hunt_database.py` - 主重构脚本
- `reconstruct_hunt_database_standalone.py` - 独立重构脚本（无依赖）
- `bot/sql_helper/sql_hunt.py` - 寻宝游戏数据库操作
- `bot/modules/commands/hunt.py` - 寻宝游戏命令处理
- `GARAGE_GAME_README.md` - 详细游戏文档

## 独立脚本使用说明 (Standalone Script Usage)

如果主脚本无法运行，可以使用独立版本：

```bash
# 选项1: 从配置文件读取数据库设置
python3 reconstruct_hunt_database_standalone.py --config --backup

# 选项2: 手动指定数据库连接参数
python3 reconstruct_hunt_database_standalone.py \
  --host localhost \
  --user your_username \
  --password your_password \
  --database your_database \
  --port 3306 \
  --backup

# 强制重构（覆盖现有表）
python3 reconstruct_hunt_database_standalone.py --config --backup --force
```

独立脚本的优势：
- ✅ 不需要安装额外的Python包
- ✅ 直接使用MySQL连接
- ✅ 支持所有重构功能
- ✅ 提供详细的执行日志

---

✅ **重构完成后，寻宝游戏将完全恢复功能！**

🎮 **After reconstruction, the hunt game will be fully functional!**