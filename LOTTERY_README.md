# Lottery System Implementation

This document describes the implementation of the lottery system for the bavabot project.

## Requirements

The lottery system implements the following rules:
1. Only users with 'lv' equal to 'b' can participate in the lottery
2. If a 'b' user participates 9 times and does not win, they are guaranteed to win on the 10th attempt

## Implementation

### Database Schema

The system uses a `lottery` table to track user participation:

```sql
CREATE TABLE lottery (
  id int(11) NOT NULL AUTO_INCREMENT,
  tg bigint(20) NOT NULL,                    -- Telegram user ID
  participation_count int(11) DEFAULT 0,     -- Total participations
  wins_count int(11) DEFAULT 0,              -- Total wins
  consecutive_losses int(11) DEFAULT 0,      -- Consecutive losses (for guaranteed win)
  last_participation datetime,               -- Last participation timestamp
  created_date datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY (tg)
);
```

### Commands

#### `/lottery`
- Allows level 'b' users to participate in the lottery
- Checks for guaranteed win condition (9 consecutive losses)
- Awards 50-200 coins on win
- Updates participation statistics
- Base win rate: 30%

#### `/lottery_stats`
- Shows personal and global lottery statistics
- Displays participation count, wins, win rate
- Shows consecutive loss streak
- Provides system-wide statistics

### Files Added/Modified

1. **`bot/sql_helper/sql_lottery.py`** - Database operations for lottery system
2. **`bot/modules/commands/lottery.py`** - Lottery command implementation
3. **`bot/modules/commands/__init__.py`** - Updated to import lottery commands
4. **`bot/__init__.py`** - Added lottery commands to bot command list
5. **`lottery_table.sql`** - Database schema creation script
6. **`test_lottery_database.py`** - Test script for lottery system

### Logic Flow

1. **User Participation Check**:
   - Verify user is registered in the system
   - Check user level is 'b' (normal user)
   - Reject participation for levels 'a', 'c', 'd'

2. **Win Determination**:
   - If consecutive_losses >= 9: Guaranteed win
   - Otherwise: 30% random chance

3. **Reward Distribution**:
   - Win: Random amount between 50-200 coins
   - Update user's coin balance
   - Reset consecutive losses to 0

4. **Statistics Update**:
   - Increment participation count
   - Update wins count if applicable
   - Update consecutive losses counter
   - Record participation timestamp

### Security Features

- User level validation prevents unauthorized participation
- Database transactions ensure data consistency
- Error handling and logging for debugging
- Input validation and sanitization

### Testing

Run the test script to verify functionality:

```bash
python3 test_lottery_database.py
```

The test validates:
- Database connection and schema
- Guaranteed win logic
- User level restrictions
- Reward calculation ranges

## Usage Examples

### Normal User Participation
```
User: /lottery
Bot: 😔 很遗憾，未中奖
     📊 您的抽奖统计：
        • 总参与次数：3
        • 总中奖次数：1  
        • 连续未中奖：2次
```

### Guaranteed Win (10th attempt)
```
User: /lottery
Bot: 🎉 恭喜中奖！
     💰 获得奖励：150币
     🏆 中奖原因：保底中奖
     📊 您的抽奖统计：
        • 总参与次数：10
        • 总中奖次数：1
        • 当前连胜：重置为0
```

### Level Restriction
```
Whitelist User: /lottery  
Bot: ❌ 抱歉，只有普通用户(lv=b)可以参与抽奖
     您当前是：白名单用户
```

### Statistics View
```
User: /lottery_stats
Bot: 📊 抽奖系统统计
     👤 您的统计：
        • 参与次数：15
        • 中奖次数：4
        • 中奖率：26.67%
        • 连续未中奖：1次
     🌍 全局统计：
        • 参与用户数：45
        • 总抽奖次数：230
        • 总中奖次数：69
        • 全局中奖率：30.0%
```

## Deployment

1. Apply the database schema:
   ```bash
   mysql -u username -p database_name < lottery_table.sql
   ```

2. Restart the bot to load the new commands

3. The lottery commands will be available to users

The system will automatically create the database table if it doesn't exist when first used.