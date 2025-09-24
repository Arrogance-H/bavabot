# 保号方式功能数据库迁移指南
# Preservation Mode Database Migration Guide

## 概述 (Overview)

此文档说明如何将保号方式功能的数据库更改应用到现有的 BavaBot 实例中。

This document explains how to apply the preservation mode feature database changes to an existing BavaBot instance.

## 🐳 Docker 模式（推荐）

**对于 Docker 用户，数据库迁移是完全自动的！**

For Docker users, database migration is completely automatic!

### Docker 自动迁移特性

- **自动检测**: Bot 启动时自动检测 `DOCKER_MODE=1` 环境变量
- **智能迁移**: 自动检查和添加缺失的数据库字段
- **零配置**: 无需手动执行任何迁移脚本
- **安全操作**: 只添加新字段，不修改现有数据

### Docker 启动流程

```bash
# 1. 正常启动 Docker 容器
docker-compose up -d

# 2. Bot 会自动执行以下操作：
# - 检测 Docker 模式
# - 检查数据库字段
# - 自动添加保号方式字段
# - 设置现有用户默认值
# - 启动 Bot 服务

# 3. 查看自动迁移日志
docker logs bavabot
```

### Docker 迁移日志示例

```
🐳 Docker模式检测到，执行自动数据库迁移...
➕ 自动添加 preserve_mode 字段...
✅ preserve_mode 字段自动添加成功
➕ 自动添加 preserve_mode_changed 字段...
✅ preserve_mode_changed 字段自动添加成功
🔄 更新现有记录的默认值...
✅ 现有记录默认值更新完成
✅ Docker模式下保号方式字段自动迁移完成
```

## 📋 手动迁移模式（非 Docker 环境）

对于非 Docker 环境，提供了手动迁移选项。

For non-Docker environments, manual migration options are provided.

### 新增数据库字段 (New Database Fields)

保号方式功能在 `emby` 表中添加了两个新字段：

```sql
ALTER TABLE emby ADD COLUMN preserve_mode VARCHAR(10) DEFAULT 'active' COMMENT '保号方式: active=活跃保号, expire=到期保号';
ALTER TABLE emby ADD COLUMN preserve_mode_changed INT DEFAULT 0 COMMENT '是否已切换过保号方式: 0=未切换, 1=已切换';
```

### 方式一：自动迁移脚本

运行提供的迁移脚本：

```bash
cd /path/to/bavabot
python3 migrate_preserve_mode.py
```

### 方式二：手动 SQL 执行

```sql
-- 检查字段是否存在
SELECT COLUMN_NAME FROM information_schema.columns 
WHERE table_schema = 'your_database_name' 
AND table_name = 'emby' 
AND column_name IN ('preserve_mode', 'preserve_mode_changed');

-- 添加字段 (如果不存在)
ALTER TABLE emby ADD COLUMN preserve_mode VARCHAR(10) DEFAULT 'active';
ALTER TABLE emby ADD COLUMN preserve_mode_changed INT DEFAULT 0;

-- 确保现有记录有默认值
UPDATE emby SET preserve_mode = 'active' WHERE preserve_mode IS NULL;
UPDATE emby SET preserve_mode_changed = 0 WHERE preserve_mode_changed IS NULL;
```

## 验证迁移 (Verify Migration)

### Docker 模式验证

Docker 模式下，迁移状态会在启动日志中显示。如需详细验证：

```bash
# 进入容器
docker exec -it bavabot sh

# 运行验证脚本（可选）
python3 verify_preserve_mode_db.py
```

### 手动模式验证

```bash
python3 verify_preserve_mode_db.py
```

## 字段说明 (Field Descriptions)

- **preserve_mode**: 用户的保号方式
  - `'active'`: 活跃保号 (基于观看活跃度)
  - `'expire'`: 到期保号 (基于到期时间)
  
- **preserve_mode_changed**: 用户是否已切换过保号方式
  - `0`: 未切换，用户可以切换一次
  - `1`: 已切换，用户不能再次切换

## 故障排除 (Troubleshooting)

### Docker 模式常见问题

1. **自动迁移失败**
   - 检查容器日志: `docker logs bavabot`
   - 确保数据库连接正常
   - 检查数据库用户权限

2. **环境变量未设置**
   - Dockerfile 中已包含 `DOCKER_MODE=1`
   - 无需手动设置

### 手动模式常见问题

1. **数据库连接失败**
   - 检查 `config.json` 中的数据库配置
   - 确保数据库服务正在运行

2. **权限不足**
   - 确保数据库用户有 ALTER TABLE 权限

## 回滚方案

如果需要回滚更改：

```sql
-- 删除新添加的字段
ALTER TABLE emby DROP COLUMN preserve_mode;
ALTER TABLE emby DROP COLUMN preserve_mode_changed;
```

**注意**: 回滚会丢失所有保号方式相关的用户设置。

## 安全注意事项 (Security Notes)

- Docker 模式下迁移是幂等的，可以安全地重复启动
- 在生产环境中建议先备份数据库
- 所有现有用户数据保持不变，只添加新字段
- 自动迁移只在 Docker 模式下启用，避免意外修改

## 部署建议

### Docker 用户（推荐）
1. 正常启动容器即可，无需额外操作
2. 监控启动日志确认迁移成功
3. 验证保号方式功能正常工作

### 非 Docker 用户
1. 先备份数据库
2. 运行迁移脚本或手动执行 SQL
3. 验证迁移成功后启动 Bot