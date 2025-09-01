# 🚀 快速修复指南 / Quick Fix Guide

## 问题症状 / Problem Symptoms

如果您看到以下错误，说明需要进行数据库迁移：
If you see the following error, you need to perform database migration:

```
(pymysql.err.OperationalError) (1054, "Unknown column 'hunt.hunt_actions' in 'field list'")
```

## 🎯 一键解决方案 / One-Click Solution

```bash
cd /path/to/bavabot
./migrate.sh
```

按照提示操作即可！ / Follow the prompts!

## 📋 其他解决方案 / Alternative Solutions

### 方案1：Python自动迁移 / Python Auto Migration
```bash
python3 migrate_hunt_table.py
```

### 方案2：独立迁移脚本 / Standalone Migration
```bash
python3 migrate_hunt_table_standalone.py --config
```

### 方案3：手动SQL执行 / Manual SQL Execution
```bash
mysql -u username -p database_name < migrate_hunt_table.sql
```

## ✅ 验证修复 / Verify Fix

迁移完成后，重启您的bot应用程序，车库游戏功能应该正常工作。
After migration, restart your bot application, and the garage game should work normally.

## 📞 需要帮助? / Need Help?

- 📖 详细说明: `MIGRATION_README.md`
- 🎮 游戏文档: `GARAGE_GAME_README.md`
- 🐛 如果问题仍然存在，请提供错误日志联系技术支持

---

💡 **提示**: 大多数用户使用一键解决方案 `./migrate.sh` 即可快速解决问题！