# Hunt Database Reconstruction Guide / 寻宝游戏数据库重构指南

## 问题描述 / Problem Description

如果您遇到以下错误，说明寻宝游戏数据库结构与当前代码不兼容：
If you encounter the following errors, it means the hunt game database structure is incompatible with current code:

```
❌ 数据库已修复，但游戏启动仍失败，请联系管理员
(pymysql.err.OperationalError) (1054, "Unknown column 'hunt.hunt_actions' in 'field list'")
(pymysql.err.OperationalError) (1054, "Unknown column 'hunt.daily_car_info' in 'field list'")
```

## 解决方案 / Solution

本修复包含两个重构脚本，可以完全重建寻宝游戏数据库结构：
This fix includes two reconstruction scripts that can completely rebuild the hunt game database structure:

1. **主脚本** (推荐): `reconstruct_hunt_database.py` - 使用机器人依赖项
2. **独立脚本**: `reconstruct_hunt_database_standalone.py` - 不需要机器人依赖项

## 使用方法 / Usage

### 方法一：主脚本 / Method 1: Main Script (Recommended)

```bash
cd /path/to/bavabot

# 基本重构 (Basic reconstruction)
python3 reconstruct_hunt_database.py

# 创建备份后重构 (Reconstruction with backup)
python3 reconstruct_hunt_database.py --backup

# 强制重构 (即使表已存在) (Force reconstruction even if tables exist)
python3 reconstruct_hunt_database.py --force

# 备份+强制重构 (Backup + force reconstruction)
python3 reconstruct_hunt_database.py --backup --force
```

### 方法二：独立脚本 / Method 2: Standalone Script

```bash
cd /path/to/bavabot

# 使用配置文件 (Use config file)
python3 reconstruct_hunt_database_standalone.py --config

# 手动指定数据库参数 (Manually specify database parameters)
python3 reconstruct_hunt_database_standalone.py \
  --host localhost \
  --user root \
  --password yourpassword \
  --database bavabot \
  --port 3306

# 带备份的重构 (Reconstruction with backup)
python3 reconstruct_hunt_database_standalone.py --config --backup --force
```

## 重构内容 / Reconstruction Content

该脚本将完全重建以下表结构：
The script will completely rebuild the following table structures:

### 核心表 / Core Tables

1. **hunt** - 游戏会话表 / Game session table
   - `hunt_actions` - 寻找装备次数 / Hunt action count  
   - `daily_car_info` - 缓存的每日汽车信息 / Cached daily car info
   - 其他必需列 / Other required columns

2. **equipment** - 用户装备表 / User equipment table
3. **equipment_definition** - 装备定义表 / Equipment definition table  
4. **car** - 汽车配置表 / Car configuration table
5. **daily_car** - 每日汽车表 / Daily car table

### 奖励系统表 / Reward System Tables

6. **assembly_reward** - 组装奖励记录表 / Assembly reward records
7. **reward_config** - 奖励配置表 / Reward configuration table
8. **reward_button** - 自定义奖励按钮表 / Custom reward button table

### 默认数据 / Default Data

脚本会自动初始化：
The script will automatically initialize:

- **25种装备定义** / 25 equipment definitions
  - 4个紫色专属车漆 / 4 purple exclusive paints
  - 10个金色高级组件 / 10 gold high-end components  
  - 4个绿色车漆变体 / 4 green paint variants
  - 7个蓝色常见物品 / 7 blue common items

- **4款汽车配置** / 4 car configurations
  - 赞德福特蓝M2 / Zandvoort Blue M2
  - 曼岛绿M3 / Isle of Man Green M3
  - 圣保罗黄M4 / Sao Paulo Yellow M4
  - 风暴灰M5 / Storm Grey M5

- **奖励配置** / Reward configurations
  - M2: 100金币 / 100 coins
  - M3: 1916金币 / 1916 coins  
  - M4: 1个注册码 / 1 registration code
  - M5: 1个白名单 / 1 whitelist

## 安全特性 / Safety Features

✅ **事务安全** - 所有操作在事务中进行
✅ **备份支持** - 可选择在重构前创建备份  
✅ **表存在检查** - 检查现有表并提供确认提示
✅ **结构验证** - 重构后验证数据库结构
✅ **功能测试** - 测试关键游戏功能确保兼容性
✅ **详细日志** - 提供详细的操作日志和错误信息

✅ **Transaction Safety** - All operations in transactions
✅ **Backup Support** - Optional backup creation before reconstruction
✅ **Table Existence Check** - Check existing tables with confirmation prompts
✅ **Structure Verification** - Verify database structure after reconstruction  
✅ **Function Testing** - Test key game functions for compatibility
✅ **Detailed Logging** - Detailed operation logs and error messages

## 验证重构结果 / Verify Reconstruction Results

重构完成后，可以通过以下方式验证：
After reconstruction, verify with the following methods:

### 1. 数据库结构检查 / Database Structure Check

```sql
-- 检查表是否存在 / Check if tables exist
SHOW TABLES LIKE '%hunt%' OR SHOW TABLES LIKE 'equipment%' OR SHOW TABLES LIKE 'car%';

-- 检查hunt表结构 / Check hunt table structure  
DESCRIBE hunt;

-- 检查数据是否初始化 / Check if data is initialized
SELECT COUNT(*) FROM equipment_definition;
SELECT COUNT(*) FROM car;
SELECT COUNT(*) FROM reward_config;
```

### 2. 游戏功能测试 / Game Function Test

```bash
# 启动机器人 / Start bot
python3 main.py

# 在Telegram中测试 / Test in Telegram
/hunt
```

应该看到游戏正常启动，显示今日目标汽车和装备信息。
You should see the game start normally, showing today's target car and equipment info.

## 故障排除 / Troubleshooting

### 1. 依赖问题 / Dependency Issues

如果主脚本失败，使用独立脚本：
If the main script fails, use the standalone script:

```bash
# 安装依赖 / Install dependencies
pip install PyMySQL

# 运行独立脚本 / Run standalone script
python3 reconstruct_hunt_database_standalone.py --config
```

### 2. 权限问题 / Permission Issues

确保数据库用户有足够权限：
Ensure database user has sufficient privileges:

```sql
GRANT CREATE, DROP, ALTER, INSERT, UPDATE, DELETE, SELECT ON database_name.* TO 'username'@'localhost';
FLUSH PRIVILEGES;
```

### 3. 连接问题 / Connection Issues

检查数据库配置：
Check database configuration:

- 主机地址和端口 / Host and port
- 用户名和密码 / Username and password
- 数据库名称 / Database name  
- 网络连通性 / Network connectivity

### 4. 恢复备份 / Restore Backup

如果需要恢复备份：
If you need to restore backup:

```bash
mysql -u username -p database_name < hunt_database_backup_YYYYMMDD_HHMMSS.sql
```

## 重要提醒 / Important Notes

⚠️ **数据丢失警告** - 重构会删除所有现有的寻宝游戏数据！
⚠️ **Data Loss Warning** - Reconstruction will delete all existing hunt game data!

🔄 **定期备份** - 建议定期备份数据库
🔄 **Regular Backups** - Recommend regular database backups

📝 **日志检查** - 如有问题，请检查详细的输出日志
📝 **Log Checking** - If issues occur, check detailed output logs

## 技术支持 / Technical Support

如果重构后仍有问题：
If issues persist after reconstruction:

1. 检查机器人日志获取详细错误信息 / Check bot logs for detailed error info
2. 确保所有依赖项已正确安装 / Ensure all dependencies are correctly installed  
3. 验证数据库权限设置 / Verify database permission settings
4. 联系技术支持并提供错误日志 / Contact technical support with error logs

## 更新历史 / Update History

- **v1.0** - 初始版本，完整的数据库重构功能 / Initial version with complete database reconstruction
- 修复hunt_actions和daily_car_info列缺失问题 / Fixed missing hunt_actions and daily_car_info columns
- 添加完整的游戏数据初始化 / Added complete game data initialization
- 提供独立和集成两种重构方案 / Provided both standalone and integrated reconstruction solutions