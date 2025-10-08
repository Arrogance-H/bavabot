# MZJ功能优化说明 / MZJ Feature Optimization

## 概述 / Overview

本次优化将mzj命令从原本的单一奖励（100 joy币）升级为随机奖励系统，用户使用命令后将随机获得三种奖励之一。

This optimization upgrades the mzj command from a single reward (100 joy coins) to a random reward system where users randomly receive one of three rewards.

## 问题陈述 / Problem Statement

原需求：优化功能，m用户使用每月19日可以领取 100joy币 ME注册资格 红包其中的一个

Original requirement: Optimize the feature so that M users can claim one of: 100 joy coins, ME registration qualification, or red envelope on the 19th of each month.

## 实施的更改 / Changes Implemented

### 1. 数据库更改 / Database Changes

**文件**: `bot/sql_helper/sql_emby.py`

添加了新的字段来跟踪用户的mzj领取日期：
- `mzj_claim_date`: DateTime字段，记录用户最后一次领取奖励的日期

Added a new field to track user's mzj claim date:
- `mzj_claim_date`: DateTime field that records the last time the user claimed a reward

```python
mzj_claim_date = Column(DateTime, nullable=True)  # Last mzj monthly claim date
```

### 2. MZJ命令更新 / MZJ Command Update

**文件**: `bot/modules/commands/mzj.py`

#### 主要功能变更 / Main Functional Changes:

1. **随机奖励系统 / Random Reward System**
   - 用户执行 `/mzj` 命令后，系统随机选择一种奖励发放
   - 三种奖励：
     - 💰 100 Joy币
     - 🎫 ME注册资格
     - 🧧 支付宝红包（独立红包）

2. **防重复领取机制 / Duplicate Claim Prevention**
   - 添加了检查机制，确保用户每月只能领取一次
   - 如果用户本月已领取，会显示下次可领取时间
   - 使用 `mzj_claim_date` 字段来追踪

### 3. 三种奖励类型详解 / Three Reward Types Explained

#### Option 1: 💰 100 Joy币 / 100 Joy Coins
- 直接增加用户的 `iv` (joy币) 余额
- 更新 `mzj_claim_date` 防止重复领取
- 显示当前余额

#### Option 2: 🎫 ME注册资格 / ME Registration Qualification
- 增加用户的 `us` (注册资格) 数量 +1
- 更新 `mzj_claim_date` 防止重复领取
- 显示当前注册资格总数
- 用户可以使用注册资格邀请他人注册

#### Option 3: 🧧 支付宝红包 / Alipay Red Envelope
- 这是一个独立的支付宝红包奖励
- 更新 `mzj_claim_date` 防止重复领取
- 提示用户联系管理员领取支付宝红包
- 这不是用于在群组发红包的joy币，而是独立的支付宝红包奖励

## 安全性 / Security

1. **验证机制 / Verification Mechanisms**:
   - 检查用户是否为M尊享用户 (lv == 'm')
   - 检查是否为每月19日
   - 检查本月是否已领取

2. **数据安全 / Data Safety**:
   - 检查joy币余额是否超出安全范围 (MAX_INT_VALUE)
   - 所有数据库操作都有错误处理

## 使用流程 / Usage Flow

1. M尊享用户在每月19日执行 `/mzj` 命令
2. 系统随机选择一种奖励（100 joy币、ME注册资格、或支付宝红包）
3. 系统验证并自动发放奖励
4. 更新领取日期，防止本月重复领取
5. 下个月19日可以再次领取

## 向后兼容性 / Backward Compatibility

- 新增的 `mzj_claim_date` 字段使用 `nullable=True`，不影响现有数据
- 现有用户在首次使用新功能时，该字段为 `None`，可以正常领取
- SQLAlchemy 的 `checkfirst=True` 确保数据库表安全创建

### 数据库迁移 / Database Migration

提供了两种方式添加新字段：

**方式一：自动迁移（推荐）**
- Docker 用户：直接启动容器，SQLAlchemy 会自动创建字段
- 非 Docker 用户：启动 Bot 时，SQLAlchemy 会自动创建字段

**方式二：手动迁移脚本**
- 运行迁移脚本：`python3 migrate_mzj_claim_date.py`
- 该脚本会安全地检查并添加 `mzj_claim_date` 字段
- Docker 用户无需运行此脚本（自动处理）

Two methods to add the new field:

**Method 1: Automatic Migration (Recommended)**
- Docker users: Start container, SQLAlchemy auto-creates the field
- Non-Docker users: Start Bot, SQLAlchemy auto-creates the field

**Method 2: Manual Migration Script**
- Run migration script: `python3 migrate_mzj_claim_date.py`
- This script safely checks and adds the `mzj_claim_date` field
- Docker users don't need to run this (handled automatically)

## 测试建议 / Testing Recommendations

由于此功能依赖特定日期（每月19日），建议测试时：

1. 临时修改日期检查逻辑以允许任意日期测试
2. 测试所有三种奖励类型的随机发放
3. 测试防重复领取机制
4. 测试非M尊享用户的访问控制
5. 测试错误处理（数据库失败等）

Since this feature depends on a specific date (19th of each month), it's recommended to:

1. Temporarily modify the date check logic to allow testing on any date
2. Test all three reward types with random distribution
3. Test duplicate claim prevention
4. Test access control for non-M tier users
5. Test error handling (database failures, etc.)

## 文件变更清单 / Files Changed

1. `bot/sql_helper/sql_emby.py` - 添加 mzj_claim_date 字段
2. `bot/modules/commands/mzj.py` - 重写为随机奖励系统
3. `bot/modules/commands/__init__.py` - 移除callback处理函数导出
4. `migrate_mzj_claim_date.py` - 数据库迁移脚本（新增）

## 日志记录 / Logging

所有奖励领取都会记录到日志：
- 【mzj】用户 {用户名}-{用户ID} 随机领取了 {奖励内容}

All reward claims are logged:
- 【mzj】User {username}-{userID} randomly claimed {reward details}
