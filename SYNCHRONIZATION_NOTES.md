# User Information Display Synchronization

## Summary

This document outlines the changes made to synchronize user information display logic across `start.py`, `member_panel.py`, and `cr_kk_ikb` function in `fix_bottons.py`.

## Problem Identified

The three functions had inconsistent user information display logic:

1. **`start.py`** - Used basic `members_info()` data without preserve mode details
2. **`member_panel.py`** - Had advanced preserve mode logic with additional database queries  
3. **`cr_kk_ikb`** - Had its own preserve mode display implementation
4. **`create.py`** - Used outdated global `schedall` settings

## Solution Implemented

### 1. Centralized Logic in `members_info()`

Updated `bot/func_helper/utils.py` to handle preserve mode logic centrally:

```python
# Before: Used global schedall settings
if lv == '白名单':
    ex = '+ ∞'
elif data.name is not None and schedall.low_activity and not schedall.check_ex:
    ex = f'__若{config.activity_check_days}天无观看将封禁__'
elif data.name is not None and not schedall.low_activity and not schedall.check_ex:
    ex = ' __无需保号，放心食用__'
else:
    ex = data.ex or '无账户信息'

# After: Uses per-user preserve mode settings
if lv == '白名单':
    ex = '+ ∞'
elif name != '无账户信息':
    if preserve_mode == 'expire':
        ex = data.ex.strftime("%Y-%m-%d %H:%M:%S") if data.ex else '无账户信息'
    elif preserve_mode == 'active':
        ex = f'__若{config.activity_check_days}天无观看将封禁__'
    else:
        ex = '__无需保号，放心食用__'
else:
    ex = data.ex or '无账户信息'
```

### 2. Enhanced `start.py` Display

Added preserve mode information to the start panel:

```python
# Added preserve mode information for non-whitelist users
if not is_whitelist:
    preserve_mode_text = '活跃保号' if preserve_mode == 'active' else '到期保号'
    can_switch = preserve_mode_changed == 0
    preserve_info = f"**· 🛡️ 保号方式** | {preserve_mode_text}" + (" (可切换)" if can_switch else " (已切换)")
    text += f"{preserve_info}\n"
```

### 3. Simplified `member_panel.py`

Removed redundant database queries since `members_info()` now handles preserve mode logic:

```python
# Removed: Redundant preserve mode logic and database fetching
# Now relies on consistent data from members_info()
```

### 4. Updated `create.py`

Fixed preserve mode logic to use per-user settings:

```python
# Before: Used global schedall settings
if e.name and schedall.low_activity and not schedall.check_ex:
    ex = f'__若{config.activity_check_days}天无观看将封禁__'

# After: Uses per-user preserve mode
preserve_mode = getattr(e, 'preserve_mode', 'active')
if preserve_mode == 'expire':
    ex = e.ex.strftime("%Y-%m-%d %H:%M:%S") if e.ex else '无账户信息'
elif preserve_mode == 'active':
    ex = f'__若{config.activity_check_days}天无观看将封禁__'
```

## Consistent Display Format

All functions now use the same format for user information:

### Basic User Info
- **🆔 用户のID** | `{user_id}`
- **📊 当前状态** | {status}
- **🍒 积分** | {points}
- **💠 账号名称** | {account_name}
- **🚨 到期时间** | {expiration}

### Preserve Mode Info (Non-whitelist users)
- **🛡️ 保号方式** | {mode_text} ({switch_status})

## Expiration Display Logic

Consistent across all functions:

| User Type | Preserve Mode | Display |
|-----------|---------------|---------|
| Whitelist | Any | `+ ∞` |
| Normal | `active` | `__若{days}天无观看将封禁__` |
| Normal | `expire` | `YYYY-MM-DD HH:MM:SS` |
| Normal | Other | `__无需保号，放心食用__` |
| No account | Any | `无账户信息` |

## Files Modified

1. `bot/func_helper/utils.py` - Centralized preserve mode logic
2. `bot/modules/commands/start.py` - Enhanced user info display
3. `bot/modules/panel/member_panel.py` - Removed redundant logic
4. `bot/modules/extra/create.py` - Fixed preserve mode handling

## Testing

- All Python files compile without syntax errors
- Logic consistency verified through test scenarios
- Database queries unified through `members_info()` function

## Benefits

1. **Consistency** - All user information displays show the same data
2. **Maintainability** - Single source of truth for preserve mode logic
3. **Performance** - Eliminated redundant database queries
4. **User Experience** - Uniform display across all interfaces