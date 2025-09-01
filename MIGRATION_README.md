# 数据库迁移指南 / Database Migration Guide

## 问题描述 / Problem Description

如果您遇到以下错误：
If you encounter the following error:

```
(pymysql.err.OperationalError) (1054, "Unknown column 'hunt.hunt_actions' in 'field list'")
```

这意味着您的数据库表结构过时，缺少必要的列。需要运行数据库迁移来添加缺失的列。
This means your database table structure is outdated and missing required columns. You need to run a database migration to add the missing columns.

## 迁移方法 / Migration Methods

### 方法一：自动迁移脚本（推荐）/ Method 1: Automatic Migration Script (Recommended)

```bash
cd /path/to/bavabot
python3 migrate_hunt_table.py
```

如果遇到依赖问题，脚本会自动尝试独立版本。
If dependency issues occur, the script will automatically try the standalone version.

### 方法二：独立迁移脚本 / Method 2: Standalone Migration Script

如果自动脚本失败，您可以使用独立版本：
If the automatic script fails, you can use the standalone version:

```bash
# 使用配置文件中的数据库设置
# Use database settings from config file
python3 migrate_hunt_table_standalone.py --config

# 或者手动指定数据库参数
# Or manually specify database parameters
python3 migrate_hunt_table_standalone.py --host localhost --user root --password yourpass --database bavabot
```

### 方法三：直接执行SQL / Method 3: Direct SQL Execution

```bash
mysql -u username -p database_name < migrate_hunt_table.sql
```

## 迁移内容 / Migration Content

该迁移会安全地添加以下列到 `hunt` 表：
This migration will safely add the following columns to the `hunt` table:

- `hunt_actions` (INT, DEFAULT 0) - 寻找装备的次数 / Hunt action count
- `daily_car_info` (TEXT, NULL) - 缓存的每日汽车信息 / Cached daily car info

## 验证迁移 / Verify Migration

迁移完成后，您可以验证表结构：
After migration, you can verify the table structure:

```sql
DESCRIBE hunt;
```

或者查看具体列信息：
Or view specific column information:

```sql
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'hunt' 
AND TABLE_SCHEMA = 'your_database_name'
ORDER BY ORDINAL_POSITION;
```

## 故障排除 / Troubleshooting

### 1. 依赖问题 / Dependency Issues

如果遇到依赖安装问题：
If you encounter dependency installation issues:

```bash
pip install PyMySQL SQLAlchemy loguru pydantic
```

### 2. 权限问题 / Permission Issues

确保数据库用户有ALTER权限：
Make sure the database user has ALTER privileges:

```sql
GRANT ALTER ON database_name.* TO 'username'@'localhost';
```

### 3. 数据库连接问题 / Database Connection Issues

检查以下配置：
Check the following configuration:

- 数据库主机地址和端口 / Database host and port
- 用户名和密码 / Username and password  
- 数据库名称 / Database name
- 网络连通性 / Network connectivity

### 4. 表不存在 / Table Does Not Exist

如果 `hunt` 表不存在，请先运行应用程序让它自动创建表结构：
If the `hunt` table doesn't exist, first run the application to let it automatically create the table structure:

```python
from bot.sql_helper.sql_hunt import Hunt
Hunt.__table__.create(bind=engine, checkfirst=True)
```

## 安全注意事项 / Safety Notes

- ✅ 迁移脚本会检查列是否已存在，避免重复执行
- ✅ 使用事务确保数据一致性
- ✅ 迁移前会验证表存在性
- ✅ 提供详细的错误信息和回滚机制

- ✅ Migration scripts check if columns exist to avoid duplicate execution
- ✅ Use transactions to ensure data consistency
- ✅ Verify table existence before migration
- ✅ Provide detailed error messages and rollback mechanisms

## 备份建议 / Backup Recommendations

在运行迁移前，建议备份数据库：
Before running migration, it's recommended to backup your database:

```bash
mysqldump -u username -p database_name > backup_$(date +%Y%m%d_%H%M%S).sql
```

## 联系支持 / Contact Support

如果迁移过程中遇到问题，请：
If you encounter issues during migration, please:

1. 检查日志文件获取详细错误信息 / Check log files for detailed error information
2. 确保数据库配置正确 / Ensure database configuration is correct
3. 联系技术支持并提供错误信息 / Contact technical support with error information