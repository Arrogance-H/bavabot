# 保号方式功能数据库迁移指南
# Preservation Mode Database Migration Guide

## 概述 (Overview)

此文档说明如何安全地将保号方式功能的数据库更改应用到现有的 BavaBot 实例中。

This document explains how to safely apply the preservation mode feature database changes to an existing BavaBot instance.

## 新增数据库字段 (New Database Fields)

保号方式功能在 `emby` 表中添加了两个新字段：

The preservation mode feature adds two new fields to the `emby` table:

```sql
ALTER TABLE emby ADD COLUMN preserve_mode VARCHAR(10) DEFAULT 'active' COMMENT '保号方式: active=活跃保号, expire=到期保号';
ALTER TABLE emby ADD COLUMN preserve_mode_changed INT DEFAULT 0 COMMENT '是否已切换过保号方式: 0=未切换, 1=已切换';
```

### 字段说明 (Field Descriptions)

- **preserve_mode**: 用户的保号方式
  - `'active'`: 活跃保号 (基于观看活跃度)
  - `'expire'`: 到期保号 (基于到期时间)
  
- **preserve_mode_changed**: 用户是否已切换过保号方式
  - `0`: 未切换，用户可以切换一次
  - `1`: 已切换，用户不能再次切换

## 迁移方式 (Migration Methods)

### 方式一：自动迁移脚本 (推荐)

运行提供的迁移脚本：

```bash
cd /path/to/bavabot
python3 migrate_preserve_mode.py
```

这个脚本会：
- 检查数据库连接
- 检查字段是否已存在
- 安全地添加缺失的字段
- 为现有用户设置默认值

### 方式二：手动 SQL 执行

如果自动脚本无法运行，可以手动执行 SQL：

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

### 方式三：SQLAlchemy 自动创建

对于新安装或表结构完全重建的情况，SQLAlchemy 会自动创建包含新字段的表。

## 验证迁移 (Verify Migration)

运行验证脚本检查迁移是否成功：

```bash
python3 verify_preserve_mode_db.py
```

这个脚本会：
- 检查字段是否正确添加
- 验证数据完整性
- 测试 SQLAlchemy 集成
- 提供详细的统计信息

## 启动 Bot (Starting the Bot)

迁移完成后，Bot 可以正常启动。新的保号方式功能将自动可用：

- 新用户默认使用活跃保号
- 现有用户保持活跃保号模式
- 用户可以在用户面板中切换保号方式
- 管理员可以在管理面板和 kk 命令中管理用户保号方式

## 故障排除 (Troubleshooting)

### 常见问题

1. **数据库连接失败**
   - 检查 `config.json` 中的数据库配置
   - 确保数据库服务正在运行
   - 检查用户权限

2. **字段添加失败**
   - 确保数据库用户有 ALTER TABLE 权限
   - 检查是否有其他进程正在使用数据库
   - 尝试重启数据库服务

3. **SQLAlchemy 报错**
   - 重启 Bot 应用
   - 检查 Python 依赖是否完整
   - 查看详细错误日志

### 回滚方案

如果需要回滚更改：

```sql
-- 删除新添加的字段
ALTER TABLE emby DROP COLUMN preserve_mode;
ALTER TABLE emby DROP COLUMN preserve_mode_changed;
```

**注意**: 回滚会丢失所有保号方式相关的用户设置。

## 安全注意事项 (Security Notes)

- 在生产环境中进行迁移前，请先备份数据库
- 建议在维护时间窗口内执行迁移
- 迁移脚本设计为幂等的，可以安全地多次运行
- 所有现有用户数据保持不变，只添加新字段

## 支持 (Support)

如果遇到迁移问题，请：

1. 检查日志输出
2. 运行验证脚本
3. 查看此文档的故障排除部分
4. 在 GitHub Issues 中报告问题并附上详细日志