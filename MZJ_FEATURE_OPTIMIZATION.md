# MZJ功能优化说明 / MZJ Feature Optimization

## 概述 / Overview

本次优化将mzj命令从原本的单一奖励（100 joy币）升级为三选一奖励系统，提供更多选择灵活性。

This optimization upgrades the mzj command from a single reward (100 joy coins) to a three-choice reward system, providing more flexibility.

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

1. **奖励选择界面 / Reward Selection Interface**
   - 用户执行 `/mzj` 命令后，不再自动发放100 joy币
   - 显示三个选项供用户选择：
     - 💰 100 Joy币
     - 🎫 ME注册资格
     - 🧧 红包（100 joy币，用于发红包）

2. **防重复领取机制 / Duplicate Claim Prevention**
   - 添加了检查机制，确保用户每月只能领取一次
   - 如果用户本月已领取，会显示下次可领取时间
   - 使用 `mzj_claim_date` 字段来追踪

3. **回调处理器 / Callback Handler**
   - 新增 `mzj_reward_callback` 函数处理用户的选择
   - 验证用户身份，确保只有奖励的拥有者可以领取
   - 再次验证所有条件（日期、等级、是否已领取等）
   - 根据用户选择发放相应奖励并更新数据库

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

#### Option 3: 🧧 红包 / Red Envelope
- 增加用户的 `iv` (joy币) 余额 100
- 更新 `mzj_claim_date` 防止重复领取
- 提示用户可以在群组中发红包给其他用户
- 本质上是给予用户100 joy币用于发红包

## 安全性 / Security

1. **验证机制 / Verification Mechanisms**:
   - 检查用户是否为M尊享用户 (lv == 'm')
   - 检查是否为每月19日
   - 检查本月是否已领取
   - 检查是否为奖励拥有者（防止他人点击）

2. **数据安全 / Data Safety**:
   - 检查joy币余额是否超出安全范围 (MAX_INT_VALUE)
   - 所有数据库操作都有错误处理

## 使用流程 / Usage Flow

1. M尊享用户在每月19日执行 `/mzj` 命令
2. 系统显示三个奖励选项
3. 用户点击选择其中一个奖励
4. 系统验证并发放奖励
5. 更新领取日期，防止本月重复领取
6. 下个月19日可以再次领取

## 向后兼容性 / Backward Compatibility

- 新增的 `mzj_claim_date` 字段使用 `nullable=True`，不影响现有数据
- 现有用户在首次使用新功能时，该字段为 `None`，可以正常领取
- SQLAlchemy 的 `checkfirst=True` 确保数据库表安全创建

## 测试建议 / Testing Recommendations

由于此功能依赖特定日期（每月19日），建议测试时：

1. 临时修改日期检查逻辑以允许任意日期测试
2. 测试所有三种奖励类型的发放
3. 测试防重复领取机制
4. 测试非M尊享用户的访问控制
5. 测试错误处理（数据库失败等）

Since this feature depends on a specific date (19th of each month), it's recommended to:

1. Temporarily modify the date check logic to allow testing on any date
2. Test all three reward types
3. Test duplicate claim prevention
4. Test access control for non-M tier users
5. Test error handling (database failures, etc.)

## 文件变更清单 / Files Changed

1. `bot/sql_helper/sql_emby.py` - 添加 mzj_claim_date 字段
2. `bot/modules/commands/mzj.py` - 重写主要逻辑，添加选择界面和回调处理
3. `bot/modules/commands/__init__.py` - 导出新的回调处理函数

## 日志记录 / Logging

所有奖励领取都会记录到日志：
- 【mzj】用户 {用户名}-{用户ID} 领取了 {奖励内容}

All reward claims are logged:
- 【mzj】User {username}-{userID} claimed {reward details}
