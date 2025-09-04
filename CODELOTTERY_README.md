# CodeLottery System Implementation

This document describes the implementation of the round-based codelottery system for the bavabot project.

## Requirements

The codelottery system implements the following rules:
1. Only users with 'lv' equal to 'c' can participate in the lottery
2. Admin-controlled lottery rounds with button-based participation
3. 3-coin entry fee automatically deducted upon participation
4. If a user participates 10 times without winning, they are guaranteed to win
5. Fair lottery: each participant can only win once per round

## Implementation

### Database Schema

The system uses multiple tables to track round-based lottery:

#### CodeLotteryUser Table
```sql
CREATE TABLE code_lottery_users (
  id int(11) NOT NULL AUTO_INCREMENT,
  tg bigint(20) NOT NULL UNIQUE,           -- Telegram user ID
  total_participations int(11) DEFAULT 0,  -- Total participations across all rounds
  total_wins int(11) DEFAULT 0,            -- Total wins across all rounds
  created_date datetime DEFAULT CURRENT_TIMESTAMP,
  updated_date datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
);
```

#### CodeLotteryRound Table
```sql
CREATE TABLE code_lottery_rounds (
  id int(11) NOT NULL AUTO_INCREMENT,
  round_number int(11) NOT NULL,           -- Round number (第几次抽奖)
  lottery_name varchar(100) NOT NULL,     -- Lottery name (e.g., "ME注册资格")
  max_participants int(11) NOT NULL,      -- Maximum participants
  entry_fee int(11) NOT NULL,             -- Entry fee in coins
  winner_count int(11) DEFAULT 1,         -- Number of winners
  status varchar(20) DEFAULT 'active',    -- active, completed, cancelled
  created_by bigint(20) NOT NULL,         -- Admin who created this round
  created_date datetime DEFAULT CURRENT_TIMESTAMP,
  completed_date datetime,
  PRIMARY KEY (id)
);
```

#### CodeLotteryParticipant Table
```sql
CREATE TABLE code_lottery_participants (
  id int(11) NOT NULL AUTO_INCREMENT,
  round_id int(11) NOT NULL,              -- Foreign key to rounds table
  tg bigint(20) NOT NULL,                 -- Participant telegram ID
  nickname varchar(100),                 -- Participant nickname
  participation_date datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  FOREIGN KEY (round_id) REFERENCES code_lottery_rounds(id)
);
```

#### CodeLotteryWinner Table
```sql
CREATE TABLE code_lottery_winners (
  id int(11) NOT NULL AUTO_INCREMENT,
  round_id int(11) NOT NULL,                    -- Foreign key to rounds table
  tg bigint(20) NOT NULL,                       -- Winner telegram ID
  nickname varchar(100),                       -- Winner nickname
  total_participations_at_win int(11) NOT NULL, -- Total participations when won
  win_date datetime DEFAULT CURRENT_TIMESTAMP,
  notified boolean DEFAULT FALSE,              -- Whether winner was notified
  PRIMARY KEY (id),
  FOREIGN KEY (round_id) REFERENCES code_lottery_rounds(id)
);
```

### Configuration

Add to `config.json`:
```json
{
  "code_lottery": {
    "status": false,
    "admin_only": true,
    "entry_fee": 3,
    "guaranteed_win_count": 10,
    "lottery_name": "ME注册资格",
    "max_participants": 100,
    "winner_count": 1
  }
}
```

### Commands

#### `/codelottery_start` (Admin Only)
- Creates a new lottery round
- Posts lottery information with participation button
- Includes round number, participant limit, entry fee

#### `/codelottery_stop` (Admin Only)  
- Stops current active lottery round
- Only works if no participants have joined

#### `/codelottery_stats` (All Users)
- Shows personal and global lottery statistics
- Displays participation count, wins, guaranteed win progress
- Shows current active round information

### User Interaction Flow

1. **Admin starts lottery**: Uses `/codelottery_start` command
2. **Bot posts lottery info** with "参与抽奖" button
3. **Users click button** to participate (lv=c users only)
4. **Entry fee deducted** automatically (3 coins)
5. **Participant count updates** in real-time
6. **Auto-draw when full**: When max participants reached
7. **Winners announced** publicly and notified privately

### Logic Flow

1. **User Participation Check**:
   - Verify user is registered in the system
   - Check user level is 'c' (restricted users)
   - Check sufficient coins for entry fee
   - Verify not already participated in current round

2. **Guaranteed Win Logic**:
   - Track total participations across all rounds
   - Users with ≥10 total participations get priority in drawing
   - Guaranteed winners selected first, then random from remaining

3. **Fair Drawing System**:
   - Each user can only win once per round
   - Guaranteed winners (10+ participations) get priority
   - Remaining slots filled randomly from other participants

4. **Winner Notification**:
   - Public announcement in group with winner details
   - Private message to winners: "联系me领奖"
   - Winner info includes total participation count

### Key Features

- **Admin Control**: Only admins can start/stop lottery rounds
- **Button Interface**: Modern inline keyboard for participation
- **Real-time Updates**: Participant count updates as users join
- **Automatic Drawing**: Triggers when participant limit reached
- **Guaranteed Win**: After 10 participations, priority in drawing
- **Fair System**: One win per round per user
- **Private Notifications**: Winners notified privately
- **Comprehensive Stats**: Personal and global statistics

### Files Added/Modified

**New Files:**
- `bot/sql_helper/sql_codelottery.py` - Database operations for round-based lottery
- `bot/modules/commands/codelottery.py` - Round-based lottery commands
- `test_codelottery_database.py` - Test script for new system
- `CODELOTTERY_README.md` - This documentation

**Modified Files:**
- `bot/schemas/schemas.py` - Added CodeLottery configuration schema
- `config_example.json` - Added codelottery configuration
- `bot/modules/commands/__init__.py` - Updated imports from lottery to codelottery

**Renamed Files:**
- `lottery.py` → `codelottery.py`
- `sql_lottery.py` → `sql_codelottery.py`
- `test_lottery_database.py` → `test_codelottery_database.py`
- `LOTTERY_README.md` → `CODELOTTERY_README.md`

### Security & Quality

- ✅ Admin-only lottery control prevents unauthorized rounds
- ✅ User level validation (lv=c only) as requested
- ✅ Automatic coin deduction with balance verification
- ✅ Anti-duplicate participation per round
- ✅ Guaranteed win tracking across all rounds
- ✅ Database transactions with proper error handling
- ✅ Comprehensive logging and error reporting
- ✅ Private winner notifications for security

The implementation completely redesigns the lottery system from individual instant lottery to admin-controlled round-based lottery with fair drawing mechanics and guaranteed win conditions.