# Hunt.py 概率配置指南

## 📋 概率修改位置

### 1. 主要概率逻辑文件
**文件路径**: `bot/sql_helper/sql_hunt.py`

#### 🎯 核心函数: `sql_random_equipment_by_rarity()` (第853-898行)
这是实际控制奖品抽取概率的函数，需要修改以下代码行：

```python
# 当前概率设置 (第860-876行)
rand_value = random.random() * 100  # 0-100的随机数

# 紫色装备个别概率判断 
if rand_value < 0.02:  # 0.05% M5紫色装备 → 修改这里
    return 4  
elif rand_value < 0.25:  # 0.5% M4紫色装备 → 修改这里
   return 3  
elif rand_value < 1.55:  # 1.0% M3紫色装备 → 修改这里
   return 2  
elif rand_value < 3.9:  # 2.35% M2紫色装备 → 修改这里
    return 1  
elif rand_value < 8.91:  # 5.0% 概率获得金色装备 → 修改这里
    category = 'gold'
elif rand_value < 15.92:  # 7.0% 概率获得绿色装备 → 修改这里
    category = 'green'
else:  # 84.1% 概率获得蓝色装备 → 自动计算
    category = 'blue'
```

#### 📊 显示信息函数: `sql_get_probability_stats()` (第1095-1111行)
这个函数控制概率信息的显示，修改后需要同步更新：

```python
def sql_get_probability_stats():
    """获取装备抽取概率统计信息"""
    return {
        "purple": {
            "probability": "3.9%",  # 修改总紫色概率显示
            "description": "专属车漆奖励",
            "details": {
                "M2_赞德福特蓝车漆": "2.0%",  # 修改这里
                "M3_曼岛绿车漆": "1.0%",     # 修改这里
                "M4_圣保罗黄车漆": "0.8%",   # 修改这里
                "M5_风暴灰车漆": "0.1%"      # 修改这里
            }
        },
        "gold": {"probability": "5.0%", "description": "高级组件"},      # 修改这里
        "green": {"probability": "7.0%", "description": "车漆变体"},     # 修改这里
        "blue": {"probability": "84.1%", "description": "常见物品"}      # 修改这里
    }
```

## 🔧 概率修改步骤

### 第一步：确定新的概率分布
例如，想要提高金色装备概率：
- 紫色: 3.9% → 3.9% (保持不变)
- 金色: 5.0% → 10.0% (提高到10%)
- 绿色: 7.0% → 5.0% (降低到5%)
- 蓝色: 84.1% → 81.1% (自动调整)

### 第二步：计算累积概率阈值
概率必须按累积方式设置：

```
M5 风暴灰: 0.1% → 阈值: 0.1
M4 圣保罗黄: 0.8% → 阈值: 0.1 + 0.8 = 0.9
M3 曼岛绿: 1.0% → 阈值: 0.9 + 1.0 = 1.9
M2 赞德福特蓝: 2.0% → 阈值: 1.9 + 2.0 = 3.9
金色装备: 10.0% → 阈值: 3.9 + 10.0 = 13.9
绿色装备: 5.0% → 阈值: 13.9 + 5.0 = 18.9
蓝色装备: 81.1% → 阈值: 其余全部 (18.9-100)
```

### 第三步：修改代码
在 `sql_random_equipment_by_rarity()` 函数中修改：

```python
# 修改后的概率设置
if rand_value < 0.1:  # 0.1% M5紫色装备
    return 4  
elif rand_value < 0.9:  # 0.8% M4紫色装备  
   return 3  
elif rand_value < 1.9:  # 1.0% M3紫色装备
   return 2  
elif rand_value < 3.9:  # 2.0% M2紫色装备
    return 1  
elif rand_value < 13.9:  # 10.0% 概率获得金色装备 (新值)
    category = 'gold'
elif rand_value < 18.9:  # 5.0% 概率获得绿色装备 (新值)
    category = 'green'
else:  # 81.1% 概率获得蓝色装备
    category = 'blue'
```

### 第四步：同步更新显示信息
在 `sql_get_probability_stats()` 函数中更新对应的百分比显示。

## ⚠️ 重要注意事项

1. **概率总和**: 确保所有概率加起来等于100%
2. **阈值顺序**: 必须按从小到大的累积概率设置阈值
3. **同步更新**: 修改实际概率后，必须同步更新显示函数中的百分比
4. **测试验证**: 修改后建议进行大量测试验证概率分布是否正确
5. **🔧 浮点精度**: 已修复概率显示中的浮点精度问题 (2024修复)

## 📝 概率修改模板

```python
# 设定你想要的概率分布
NEW_PROBABILITIES = {
    'M5_purple': 0.1,    # M5 风暴灰车漆
    'M4_purple': 0.8,    # M4 圣保罗黄车漆  
    'M3_purple': 1.0,    # M3 曼岛绿车漆
    'M2_purple': 2.0,    # M2 赞德福特蓝车漆
    'gold': 5.0,         # 金色装备
    'green': 7.0,        # 绿色装备
    'blue': 84.1         # 蓝色装备 (100 - 其他概率总和)
}

# 计算累积阈值
cumulative = 0
THRESHOLDS = {}
for key, prob in NEW_PROBABILITIES.items():
    cumulative += prob
    THRESHOLDS[key] = cumulative

print("修改代码时使用的阈值:")
for key, threshold in THRESHOLDS.items():
    print(f"{key}: {threshold}")
```

## 🎮 JOY币消耗修改

如需修改每次寻找的JOY币消耗，请修改：
- **文件**: `bot/modules/commands/hunt.py`
- **位置**: 第470行附近的消耗检查逻辑

```python
# 当前: 每次消耗 1 JOY币
if not user or user.iv < 1:  # 修改这里的数字
    return await callAnswer(call, f"❌ {sakura_b}不足，需要 1{sakura_b}", show_alert=True)

# 扣除金币  
if not sql_update_emby(Emby.tg == call.from_user.id, iv=user.iv - 1):  # 修改这里的数字
```