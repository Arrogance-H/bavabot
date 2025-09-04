# CodeLottery Database Column Fix

## Problem
The CodeLottery system was failing with these errors:
```
(pymysql.err.OperationalError) (1054, "Unknown column 'code_lottery_rounds.start_time' in 'field list'")
(pymysql.err.OperationalError) (1054, "Unknown column 'code_lottery_rounds.creator_tg' in 'field list'")
(pymysql.err.OperationalError) (1054, "Unknown column 'code_lottery_users.total_participation' in 'field list'")
```

This occurred because the database tables were missing required columns that were added to the SQLAlchemy models.

## Solution

### Automatic Fix (Recommended)
The issue is now automatically fixed when the bot starts. The migration code in `bot/sql_helper/sql_codelottery.py` will:

1. Check if the `code_lottery_rounds` and `code_lottery_users` tables exist
2. Compare existing columns with required columns  
3. Add any missing columns automatically
4. Handle the migration safely without breaking existing data

### Manual Fix (If Needed)
If you need to fix the database manually, use the provided migration script:

```bash
# Using bot configuration file
python3 fix_codelottery_columns.py --use-bot-config

# Or specify database details manually
python3 fix_codelottery_columns.py --host localhost --user myuser --password mypass --database mydatabase
```

## Required Columns

### code_lottery_rounds table
- `id` (INT, PRIMARY KEY) - Round ID
- `round_number` (INT, NOT NULL) - Round number (FIXED)
- `lottery_name` (VARCHAR(200), NOT NULL) - Lottery name (FIXED)
- `creator_tg` (BIGINT, NOT NULL) - Creator Telegram ID (FIXED)
- `start_time` (DATETIME, NOT NULL) - Start time (FIXED)
- `end_time` (DATETIME, NOT NULL) - End time (FIXED)
- `entry_fee` (INT, DEFAULT 3) - Entry fee (FIXED)
- `winner_count` (INT, DEFAULT 1) - Winner count (FIXED)
- `status` (VARCHAR(20), DEFAULT 'active') - Status (FIXED)
- `draw_time` (DATETIME, NULL) - Draw time (FIXED)
- `created_at` (DATETIME, DEFAULT CURRENT_TIMESTAMP) - Created time (FIXED)

### code_lottery_users table
- `tg` (BIGINT, PRIMARY KEY) - Telegram user ID
- `total_participation` (INT, DEFAULT 0) - Total participation count
- `total_wins` (INT, DEFAULT 0) - Total wins count  
- `guaranteed_count` (INT, DEFAULT 0) - Current guaranteed count
- `last_participation` (DATETIME, NULL) - Last participation time
- `last_win` (DATETIME, NULL) - Last win time

## Files Modified
- `bot/sql_helper/sql_codelottery.py` - Added automatic migration for ALL missing columns in code_lottery_rounds table
- `fix_codelottery_columns.py` - Updated standalone migration script to handle ALL missing columns

## Testing
After applying the fix, lottery creation and `/codelottery_stats` commands should work without the "Unknown column" errors.