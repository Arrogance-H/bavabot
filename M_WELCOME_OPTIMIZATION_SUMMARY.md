# m_welcome.py 优化总结 / m_welcome.py Optimization Summary

## 变更概述 / Change Overview

本次优化将 `m_welcome.py` 从"M尊享用户专属欢迎"重构为"随机欢迎消息"功能。

This optimization refactors `m_welcome.py` from "M-tier exclusive welcome" to "random welcome message" feature.

---

## 主要变更 / Key Changes

### 功能变更 / Feature Changes

| 项目 / Item | 旧版本 / Old | 新版本 / New |
|------------|------------|------------|
| **触发条件** / Trigger | 仅M等级用户 / M-tier only | 任何用户 / Any user |
| **触发频率** / Frequency | 每用户每天1次 / Once per user per day | 概率触发+群组冷却 / Probability + group cooldown |
| **数据库依赖** / DB Dependency | 需要查询和更新 / Query & update required | 无需数据库 / No database needed |
| **配置方式** / Configuration | 数据库字段 / Database field | 代码常量 / Code constants |

### 代码变更 / Code Changes

**删除的导入 / Removed imports:**
```python
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby
```

**新增的配置 / New configuration:**
```python
WELCOME_PROBABILITY = 0.05  # 5% probability
WELCOME_COOLDOWN_MINUTES = 60  # 60 minutes cooldown
last_welcome_time = {}  # Track last welcome time per group
```

**函数重命名 / Function renamed:**
- `welcome_m_user()` → `welcome_random_user()`

---

## 优势 / Advantages

1. **更简单** / Simpler
   - 不依赖数据库 / No database dependency
   - 代码更简洁 / Cleaner code
   - 易于维护 / Easier to maintain

2. **更灵活** / More flexible
   - 所有用户都能触发 / All users can trigger
   - 可调节触发频率 / Adjustable frequency
   - 群组级别控制 / Group-level control

3. **更高效** / More efficient
   - 无数据库查询 / No database queries
   - 内存中追踪 / In-memory tracking
   - 响应更快 / Faster response

---

## 配置调整 / Configuration Adjustment

在 `bot/modules/extra/m_welcome.py` 中修改：

Modify in `bot/modules/extra/m_welcome.py`:

```python
# 调整触发概率（0.0-1.0）
# Adjust trigger probability (0.0-1.0)
WELCOME_PROBABILITY = 0.05  # 5% → 可改为 0.1 (10%) 或 0.02 (2%)

# 调整冷却时间（分钟）
# Adjust cooldown time (minutes)  
WELCOME_COOLDOWN_MINUTES = 60  # 60分钟 → 可改为 30 或 120
```

---

## 测试建议 / Testing Recommendations

### 快速测试 / Quick Test

临时修改配置以便快速验证：

Temporarily modify configuration for quick verification:

```python
WELCOME_PROBABILITY = 1.0  # 100% 触发
WELCOME_COOLDOWN_MINUTES = 0  # 无冷却
```

### 正常运行 / Normal Operation

建议配置（基于群组活跃度）：

Recommended configuration (based on group activity):

- **高活跃群组** / High activity: `WELCOME_PROBABILITY = 0.02` (2%), `COOLDOWN = 120` (2 hours)
- **中活跃群组** / Medium activity: `WELCOME_PROBABILITY = 0.05` (5%), `COOLDOWN = 60` (1 hour)
- **低活跃群组** / Low activity: `WELCOME_PROBABILITY = 0.1` (10%), `COOLDOWN = 30` (30 min)

---

## 文件清单 / File List

### 修改的文件 / Modified Files
- `bot/modules/extra/m_welcome.py` - 主要功能实现

### 新增的文件 / New Files
- `M_WELCOME_REFACTOR.md` - 详细文档

### 更新的文件 / Updated Files
- `M_WELCOME_DEBUG_GUIDE.md` - 添加重定向通知
- `M_WELCOME_FIX_SUMMARY.md` - 添加重定向通知

---

## 兼容性 / Compatibility

- ✅ **向前兼容** / Forward compatible: 新代码可以直接使用
- ⚠️ **数据库字段** / Database field: `m_welcome_date` 字段不再使用但保留
- ✅ **配置文件** / Config files: 无需修改 `config.json`
- ✅ **欢迎消息** / Welcome messages: 继续使用 `yvlu.json` 中的 `m_welcome`

---

## 相关链接 / Related Links

- 📖 详细文档 / Detailed docs: [M_WELCOME_REFACTOR.md](./M_WELCOME_REFACTOR.md)
- 🔧 代码文件 / Code file: `bot/modules/extra/m_welcome.py`
- 💬 欢迎消息配置 / Messages config: `bot/func_helper/yvlu.json`

---

**更新时间 / Updated**: 2025-01-XX
