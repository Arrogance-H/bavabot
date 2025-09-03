# Hunt Game Fix Instructions / 寻宝游戏修复说明

## Problem / 问题
The hunt game (`hunt.py`) cannot start due to database schema incompatibility. The hunt table is missing required columns that the current game code expects.

寻宝游戏 (`hunt.py`) 无法启动，因为数据库结构与当前游戏代码不兼容。hunt 表缺少当前游戏代码需要的必需列。

## Error Symptoms / 错误症状
- `/hunt` command fails to start
- Bot shows database-related errors
- Game sessions cannot be created

- `/hunt` 命令启动失败
- 机器人显示数据库相关错误
- 无法创建游戏会话

## Root Cause / 根本原因
The hunt table is missing these required columns:
- `hunt_actions` - Tracks number of hunt actions performed
- `daily_car_info` - Caches daily car information
- `message_id` - Associates messages with hunt sessions
- `chat_id` - Tracks chat where hunt message was sent

hunt 表缺少以下必需列：
- `hunt_actions` - 跟踪执行的寻宝操作次数
- `daily_car_info` - 缓存每日汽车信息
- `message_id` - 将消息与寻宝会话关联
- `chat_id` - 跟踪发送寻宝消息的聊天

## Solutions / 解决方案

### Option 1: SQL Script (Recommended / 推荐)
Run the provided SQL script to add missing columns:

运行提供的 SQL 脚本来添加缺少的列：

1. Connect to your MySQL database
   连接到您的 MySQL 数据库

2. Run the script:
   运行脚本：
   ```bash
   mysql -u your_username -p your_database < fix_hunt_schema.sql
   ```

3. Restart your bot
   重启您的机器人

### Option 2: Automatic Reconstruction (Requires Dependencies)
If you have Python dependencies installed:

如果您已安装 Python 依赖项：

```bash
# Method 1: Use standalone script
python3 reconstruct_hunt_database_standalone.py --config --backup

# Method 2: Use main reconstruction script
python3 reconstruct_hunt_database.py --backup
```

### Option 3: Manual Database Update
Connect to your database and run these commands manually:

连接到您的数据库并手动运行这些命令：

```sql
-- Add hunt_actions column
ALTER TABLE hunt ADD COLUMN hunt_actions INT DEFAULT 0 COMMENT '寻找装备的次数';

-- Add daily_car_info column  
ALTER TABLE hunt ADD COLUMN daily_car_info TEXT NULL COMMENT '缓存的每日汽车信息';

-- Add message_id column
ALTER TABLE hunt ADD COLUMN message_id INT NULL COMMENT '关联的消息ID';

-- Add chat_id column
ALTER TABLE hunt ADD COLUMN chat_id BIGINT NULL COMMENT '消息所在的聊天ID';
```

## Verification / 验证

After applying the fix, verify the structure:

应用修复后，验证结构：

```sql
DESCRIBE hunt;
```

You should see all the new columns listed.

您应该看到列出的所有新列。

## Testing / 测试

1. Start your bot
   启动您的机器人

2. Try the hunt command:
   尝试寻宝命令：
   ```
   /hunt
   ```

3. The game should start successfully
   游戏应该成功启动

## Files Included / 包含的文件

- `fix_hunt_schema.sql` - SQL script to fix the database schema
- `HUNT_FIX_README.md` - This documentation

- `fix_hunt_schema.sql` - 修复数据库结构的 SQL 脚本
- `HUNT_FIX_README.md` - 本文档

## Additional Resources / 其他资源

For more comprehensive database reconstruction:
- `reconstruct_hunt_database.py` - Full reconstruction script
- `reconstruct_hunt_database_standalone.py` - Standalone version
- `HUNT_RECONSTRUCTION_README.md` - Detailed reconstruction guide

用于更全面的数据库重构：
- `reconstruct_hunt_database.py` - 完整重构脚本
- `reconstruct_hunt_database_standalone.py` - 独立版本
- `HUNT_RECONSTRUCTION_README.md` - 详细重构指南

## Support / 支持

If you encounter issues:
1. Check bot logs for specific error messages
2. Verify database connection settings in `config.json`
3. Ensure database user has proper permissions

如果遇到问题：
1. 检查机器人日志中的具体错误消息
2. 验证 `config.json` 中的数据库连接设置
3. 确保数据库用户具有适当的权限