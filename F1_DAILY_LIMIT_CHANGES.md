# F1 Daily Limit Implementation

## Changes Made

### Database Schema Changes (sql_emby.py)
- Added `punch_count` column (Integer, default=0): Tracks daily F1 game plays
- Added `punch_date` column (DateTime, nullable=True): Tracks the date of the last play

### Game Logic Changes (checkin.py)

#### start_punch_in_game function:
- Added daily limit check (3 games per day)
- Added automatic reset of count when date changes
- Shows remaining attempts to users
- Prevents game start if daily limit is reached

#### end_punch_game function:
- Increments daily play count after each completed game
- Updates punch_date to current date
- Shows remaining attempts in game result message
- Handles date rollover automatically

## Features
1. **Daily Limit**: Users can play F1 game maximum 3 times per day
2. **Automatic Reset**: Count resets at midnight (China timezone UTC+8)
3. **User Feedback**: Shows remaining attempts to users
4. **Persistent Tracking**: Uses database to track across bot restarts

## Database Migration
The new columns will be automatically created when the bot starts due to SQLAlchemy's `checkfirst=True` setting in the table creation.

## Backward Compatibility
- Existing users will have `punch_count=0` and `punch_date=NULL` by default
- First game play will initialize these values properly
- No data migration required