# CodeLottery Database Column Fix

## Problem
The CodeLottery system was failing with this error:
```
(pymysql.err.OperationalError) (1054, "Unknown column 'code_lottery_users.total_participation' in 'field list'")
```

This occurred because the `code_lottery_users` table was missing required columns that were added to the SQLAlchemy model.

## Solution

### Automatic Fix (Recommended)
The issue is now automatically fixed when the bot starts. The migration code in `bot/sql_helper/sql_codelottery.py` will:

1. Check if the `code_lottery_users` table exists
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
The `code_lottery_users` table requires these columns:

- `tg` (BIGINT, PRIMARY KEY) - Telegram user ID
- `total_participation` (INT, DEFAULT 0) - Total participation count
- `total_wins` (INT, DEFAULT 0) - Total wins count  
- `guaranteed_count` (INT, DEFAULT 0) - Current guaranteed count
- `last_participation` (DATETIME, NULL) - Last participation time
- `last_win` (DATETIME, NULL) - Last win time

## Files Modified
- `bot/sql_helper/sql_codelottery.py` - Added automatic migration function
- `fix_codelottery_columns.py` - Standalone migration script (NEW)

## Testing
After applying the fix, the `/codelottery_stats` command should work without errors.