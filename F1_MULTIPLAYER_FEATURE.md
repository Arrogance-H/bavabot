# F1 Multiplayer Game Feature

## Overview
This feature adds a multiplayer F1 racing game that can be played in group chats. Multiple players can join a game and compete by clicking their acceleration button as fast as possible.

## How to Use

### Starting a Game
In a group chat, use the command:
```
/f1
```

This will:
- Deduct 5 joy coins from the initiator
- Create a new game room
- Display a message with "Join Game" and "Start Race" buttons

### Joining a Game
Other players can click the "🎮 加入游戏" button to join the game. Each player who joins will:
- Pay 5 joy coins to enter
- Be added to the participant list
- See their name in the player roster

### Starting the Race
- Only the game initiator can start the race
- Minimum 2 players required to start
- Click "🏁 开始比赛" button to begin

### Racing
Once started:
1. A 3-second countdown begins
2. Each player gets their own acceleration button
3. Players have 5 seconds to click their button as many times as possible
4. Real-time ranking is displayed during the race

### Winning
- The player with the most clicks wins all the joy coins in the prize pool
- If multiple players tie for the highest clicks, they split the prize evenly
- Prize distribution uses floor division (decimal parts are discarded)

## Technical Details

### Implementation
- File: `bot/modules/callback/checkin.py`
- Command handler: `start_multiplayer_f1()`
- Callback handlers:
  - `join_multiplayer_f1()` - Handle player joining
  - `start_multiplayer_f1_game()` - Start the race
  - `handle_multiplayer_f1_click()` - Track clicks
  - `end_multiplayer_f1_game()` - Calculate winners

### Game Data Structure
```python
multiplayer_f1_games = {
    game_id: {
        'creator': user_id,
        'participants': {
            user_id: {
                'name': str,
                'clicks': int
            }
        },
        'started': bool,
        'game_active': bool,
        'chat_id': int,
        'message_id': int
    }
}
```

### Entry Fee
- Each player pays 5 joy coins to participate
- Fees are deducted immediately upon joining
- Total prize pool = number_of_players × 5

### Prize Distribution
- Winner(s) = player(s) with highest click count
- Prize per winner = total_prize_pool // number_of_winners
- Floor division ensures integer coin amounts

## Differences from Single-Player F1
The original single-player F1 game (`punch_in` callback) remains unchanged:
- Uses daily limit (3 games per day)
- Solo racing with predetermined rewards
- Access via checkin panel button

The new multiplayer F1 game:
- No daily limit
- Multiple players compete
- Winner takes all (or splits evenly)
- Started via `/f1` command in groups

## Requirements
- Must be in a group chat to use `/f1` command
- F1 feature must be enabled (`_open.punch_in = True`)
- Players must have sufficient joy coin balance (≥5)
- Minimum 2 players required to start

## Example Flow
```
User A: /f1
Bot: Creates game, deducts 5 coins from A
     Shows: "1 player joined, need 2 to start"

User B: Clicks "Join Game"
Bot: Deducts 5 coins from B
     Shows: "2 players joined, can start now"

User A: Clicks "Start Race"
Bot: Countdown 3... 2... 1...
     Shows acceleration buttons for A and B

[5 seconds of racing]

Bot: "Game Over! Winner: User A (23 clicks)"
     Awards 10 coins to User A
```
