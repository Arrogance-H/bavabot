import asyncio
import random
from datetime import datetime, timezone, timedelta

from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot import bot, _open, sakura_b, prefixes, group
from bot.func_helper.filters import user_in_group_on_filter
from bot.func_helper.msg_utils import callAnswer, sendMessage, deleteMessage, editMessage
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby

# 存储用户打卡游戏状态的临时数据
punch_in_sessions = {}

# 存储用户每日F1游戏次数的内存数据 {user_id: {'count': int, 'date': 'YYYY-MM-DD'}}
daily_punch_limits = {}

# F1游戏每日限制次数
DAILY_PUNCH_LIMIT = 3

# 存储多人F1游戏房间 {game_id: {'creator': user_id, 'participants': {user_id: {'name': str, 'clicks': int}}, 'started': bool, 'game_active': bool, 'chat_id': int, 'message_id': int}}
multiplayer_f1_games = {}


def get_punch_count(user_id: int) -> tuple[int, int]:
    """
    获取用户今日F1游戏次数和剩余次数
    返回: (今日已玩次数, 剩余次数)
    """
    # 定期清理过期数据
    if len(daily_punch_limits) > 100:  # 当数据量较大时才清理，避免频繁操作
        cleanup_old_punch_data()
    
    now = datetime.now(timezone(timedelta(hours=8)))
    today = now.strftime("%Y-%m-%d")
    
    if user_id not in daily_punch_limits:
        daily_punch_limits[user_id] = {'count': 0, 'date': today}
        return 0, DAILY_PUNCH_LIMIT
    
    user_data = daily_punch_limits[user_id]
    
    # 如果日期变了，重置计数
    if user_data['date'] != today:
        daily_punch_limits[user_id] = {'count': 0, 'date': today}
        return 0, DAILY_PUNCH_LIMIT
    
    current_count = user_data['count']
    remaining = max(0, DAILY_PUNCH_LIMIT - current_count)
    return current_count, remaining


def increment_punch_count(user_id: int) -> tuple[int, int]:
    """
    增加用户今日F1游戏次数
    返回: (今日已玩次数, 剩余次数)
    """
    now = datetime.now(timezone(timedelta(hours=8)))
    today = now.strftime("%Y-%m-%d")
    
    if user_id not in daily_punch_limits:
        daily_punch_limits[user_id] = {'count': 1, 'date': today}
        return 1, DAILY_PUNCH_LIMIT - 1
    
    user_data = daily_punch_limits[user_id]
    
    # 如果日期变了，重置为1
    if user_data['date'] != today:
        daily_punch_limits[user_id] = {'count': 1, 'date': today}
        return 1, DAILY_PUNCH_LIMIT - 1
    
    # 增加计数
    new_count = user_data['count'] + 1
    daily_punch_limits[user_id]['count'] = new_count
    remaining = max(0, DAILY_PUNCH_LIMIT - new_count)
    return new_count, remaining


def cleanup_old_punch_data():
    """
    清理过期的F1游戏限制数据（保留最近2天的数据）
    """
    now = datetime.now(timezone(timedelta(hours=8)))
    today = now.strftime("%Y-%m-%d")
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    
    users_to_remove = []
    for user_id, data in daily_punch_limits.items():
        if data['date'] not in [today, yesterday]:
            users_to_remove.append(user_id)
    
    for user_id in users_to_remove:
        del daily_punch_limits[user_id]


@bot.on_callback_query(filters.regex('checkin') & user_in_group_on_filter)
async def user_in_checkin(_, call):
    now = datetime.now(timezone(timedelta(hours=8)))
    today = now.strftime("%Y-%m-%d")
    if _open.checkin:
        e = sql_get_emby(call.from_user.id)
        if not e:
            await callAnswer(call, '🧮 未查询到数据库', True)

        elif not e.ch or e.ch.strftime("%Y-%m-%d") < today:
            reward = random.randint(_open.checkin_reward[0], _open.checkin_reward[1])
            s = e.iv + reward
            sql_update_emby(Emby.tg == call.from_user.id, iv=s, ch=now)
            text = f'🎉 **签到成功** | {reward} {sakura_b}\n💴 **当前持有** | {s} {sakura_b}\n⏳ **签到日期** | {now.strftime("%Y-%m-%d")}'
            await asyncio.gather(deleteMessage(call), sendMessage(call, text=text))

        else:
            await callAnswer(call, '⭕ 您今天已经签到过了！签到是无聊的活动哦。', True)
    else:
        await callAnswer(call, '❌ 未开启签到功能，等待！', True)


@bot.on_callback_query(filters.regex('punch_in') & user_in_group_on_filter)
async def start_punch_in_game(_, call):
    """开始打卡游戏"""
    if not _open.punch_in:
        await callAnswer(call, '❌ 未开启F1功能，等待！', True)
        return
    
    e = sql_get_emby(call.from_user.id)
    if not e:
        await callAnswer(call, '🧮 未查询到数据库', True)
        return
    
    user_id = call.from_user.id
    
    # 检查用户是否已经在游戏中
    if user_id in punch_in_sessions:
        await callAnswer(call, '🎮 您已经在游戏中了！', True)
        return
    
    # 检查今日游戏次数限制（使用内存跟踪）
    current_count, remaining = get_punch_count(user_id)
    
    # 检查是否已达到每日限制
    if current_count >= DAILY_PUNCH_LIMIT:
        await callAnswer(call, f'🎮 今日F1游戏次数已用完！每日限制{DAILY_PUNCH_LIMIT}次，明天再来吧！', True)
        return
    
    # 初始化用户游戏会话（预占位）
    punch_in_sessions[user_id] = {
        'clicks': 0,
        'game_active': False,
        'stage': 'waiting'
    }
    
    # 创建准备按钮
    ready_button = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ 准备好了", f"punch_ready_{user_id}")]
    ])
    
    await editMessage(call, f"🎮 **F1**\n\n准备好开始了吗？\n\n🎯 今日剩余次数: {remaining}/{DAILY_PUNCH_LIMIT}", buttons=ready_button)


@bot.on_callback_query(filters.regex(r'punch_ready_(\d+)'))
async def punch_ready(_, call):
    """处理准备按钮点击，3秒后显示加速按钮"""
    user_id = int(call.matches[0].group(1))
    
    # 验证用户身份
    if call.from_user.id != user_id:
        await callAnswer(call, '❌ 请您开自己的车！', True)
        return
    
    # 检查会话是否存在
    if user_id not in punch_in_sessions:
        await callAnswer(call, '❌ 比赛已结束！', True)
        return
    
    # 更新游戏状态
    punch_in_sessions[user_id]['stage'] = 'preparing'
    
    await editMessage(call, "🎮 **F1**\n\n⏳ 准备中...\n\n3秒后开始，请疯狂点击加速按钮！")
    
    # 等待3秒
    await asyncio.sleep(3)
    
    # 检查会话是否仍然存在（防止用户中途退出）
    if user_id not in punch_in_sessions:
        return
    
    # 激活游戏并显示加速按钮
    punch_in_sessions[user_id]['game_active'] = True
    punch_in_sessions[user_id]['stage'] = 'playing'
    
    speed_button = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ 加速吧！", f"punch_click_{user_id}")]
    ])
    
    await editMessage(call, "🎮 **F1**\n\n⚡ 加速吧！\n\n⏰ 剩余时间: 3秒", buttons=speed_button)
    
    # 3秒后结束游戏
    await asyncio.sleep(3)
    await end_punch_game(call, user_id)


@bot.on_callback_query(filters.regex(r'punch_click_(\d+)'))
async def handle_punch_click(_, call):
    """处理加速按钮点击"""
    user_id = int(call.matches[0].group(1))
    
    # 验证用户身份
    if call.from_user.id != user_id:
        await callAnswer(call, '❌ 请开自己的车！', True)
        return
    
    # 检查游戏是否活跃
    if user_id not in punch_in_sessions or not punch_in_sessions[user_id]['game_active']:
        await callAnswer(call, '⏰ 比赛已结束！', True)
        return
    
    # 增加点击次数
    punch_in_sessions[user_id]['clicks'] += 1
    clicks = punch_in_sessions[user_id]['clicks']
    
    # 更新显示但不阻塞
    try:
        speed_button = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚡ 加速吧！", f"punch_click_{user_id}")]
        ])
        
        await editMessage(call, f"🎮 **F1**\n\n⚡ 加速吧！\n\n📊 点击次数: {clicks}", buttons=speed_button)
    except Exception:
        # 忽略编辑消息的错误，因为可能点击太快
        pass
    
    await callAnswer(call, f"⚡ 第{clicks}次点击！", False)


async def end_punch_game(call, user_id):
    """结束打卡游戏并发放奖励"""
    if user_id not in punch_in_sessions:
        return
    
    clicks = punch_in_sessions[user_id]['clicks']
    punch_in_sessions[user_id]['game_active'] = False
    
    # 增加今日游戏次数（使用内存跟踪）
    new_punch_count, remaining = increment_punch_count(user_id)
    
    # 计算奖励
    reward = 0
    reward_text = ""
    
    if clicks <= 3:
        reward_text = "💔 **爆胎咯，需要更努力哦!**"
    elif clicks <= 9:
        reward = random.randint(1, 3)
        reward_text = f"🎉 **获得奖励**: {reward} {sakura_b}"
    else:
        reward = 19
        reward_text = f"🏆 **超级奖励**: {reward} {sakura_b}"
    
    # 发放奖励
    if reward > 0:
        e = sql_get_emby(user_id)
        if e:
            new_total = e.iv + reward
            sql_update_emby(Emby.tg == user_id, iv=new_total)
            reward_text += f"\n💰 **当前持有**: {new_total} {sakura_b}"
    
    # 添加剩余次数提示
    if remaining > 0:
        remaining_text = f"\n\n🎯 今日剩余次数: {remaining}/{DAILY_PUNCH_LIMIT}"
    else:
        remaining_text = f"\n\n🎯 今日游戏次数已用完，明天再来！"
    
    result_text = f"🎮 **F1结果**\n\n📊 **点击次数**: {clicks}\n{reward_text}{remaining_text}"
    
    # 根据剩余次数添加相应按钮
    buttons = None
    if remaining > 0:
        # 还有游戏次数，显示"继续冲刺"按钮
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏁 继续冲刺", "punch_in")]
        ])
    else:
        # 没有游戏次数，显示"返回主页"按钮
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 返回主页", "back_start")]
        ])
    
    # 清理会话数据
    del punch_in_sessions[user_id]
    
    try:
        await editMessage(call, result_text, buttons=buttons)
    except Exception:
        # 如果编辑失败，发送新消息
        await sendMessage(call, text=result_text, buttons=buttons)


# ============== 多人F1游戏功能 ==============

@bot.on_message(filters.command('f1', prefixes) & filters.chat(group))
async def start_multiplayer_f1(_, msg):
    """在群组中发起多人F1游戏"""
    if not _open.punch_in:
        await sendMessage(msg, '❌ 未开启F1功能，等待！', timer=5)
        await deleteMessage(msg)
        return
    
    e = sql_get_emby(msg.from_user.id)
    if not e:
        await sendMessage(msg, '🧮 未查询到数据库', timer=5)
        await deleteMessage(msg)
        return
    
    # 检查余额是否足够
    if e.iv < 5:
        await sendMessage(msg, f'❌ 余额不足！参与游戏需要 5 {sakura_b}', timer=5)
        await deleteMessage(msg)
        return
    
    # 创建游戏ID
    game_id = f"f1_mp_{msg.chat.id}_{msg.from_user.id}_{int(datetime.now().timestamp())}"
    
    # 扣除发起者的5个joy币
    sql_update_emby(Emby.tg == msg.from_user.id, iv=e.iv - 5)
    
    # 创建游戏房间
    multiplayer_f1_games[game_id] = {
        'creator': msg.from_user.id,
        'participants': {
            msg.from_user.id: {
                'name': msg.from_user.first_name or '玩家',
                'clicks': 0
            }
        },
        'started': False,
        'game_active': False,
        'chat_id': msg.chat.id,
        'message_id': None
    }
    
    # 创建按钮
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 加入游戏", f"f1_join_{game_id}")],
        [InlineKeyboardButton("🏁 开始比赛 (1/2)", f"f1_start_{game_id}")]
    ])
    
    text = (
        f"🏎️ **多人F1竞速赛**\n\n"
        f"🎯 发起者: {msg.from_user.first_name}\n"
        f"💰 参与费用: 5 {sakura_b}\n"
        f"👥 当前玩家: 1/∞\n\n"
        f"📋 参与玩家:\n"
        f"1️⃣ {msg.from_user.first_name}\n\n"
        f"⚠️ 至少需要2名玩家才能开始游戏\n"
        f"🏆 获胜者将赢得所有投入的joy币！"
    )
    
    sent = await sendMessage(msg, text=text, buttons=buttons, send=True)
    multiplayer_f1_games[game_id]['message_id'] = sent.id
    
    await deleteMessage(msg)


@bot.on_callback_query(filters.regex(r'f1_join_(.+)'))
async def join_multiplayer_f1(_, call):
    """加入多人F1游戏"""
    game_id = call.matches[0].group(1)
    
    if game_id not in multiplayer_f1_games:
        await callAnswer(call, '❌ 游戏不存在或已结束', True)
        return
    
    game = multiplayer_f1_games[game_id]
    user_id = call.from_user.id
    
    # 检查游戏是否已开始
    if game['started']:
        await callAnswer(call, '❌ 游戏已经开始，无法加入', True)
        return
    
    # 检查是否已经参与
    if user_id in game['participants']:
        await callAnswer(call, '✅ 您已经在游戏中了', True)
        return
    
    # 检查数据库
    e = sql_get_emby(user_id)
    if not e:
        await callAnswer(call, '🧮 未查询到数据库', True)
        return
    
    # 检查余额
    if e.iv < 5:
        await callAnswer(call, f'❌ 余额不足！参与游戏需要 5 {sakura_b}', True)
        return
    
    # 扣除5个joy币
    sql_update_emby(Emby.tg == user_id, iv=e.iv - 5)
    
    # 添加到游戏
    game['participants'][user_id] = {
        'name': call.from_user.first_name or '玩家',
        'clicks': 0
    }
    
    # 更新消息
    participant_count = len(game['participants'])
    participant_list = '\n'.join([
        f"{i+1}️⃣ {p['name']}" 
        for i, p in enumerate(game['participants'].values())
    ])
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 加入游戏", f"f1_join_{game_id}")],
        [InlineKeyboardButton(f"🏁 开始比赛 ({participant_count}/2)", f"f1_start_{game_id}")]
    ])
    
    text = (
        f"🏎️ **多人F1竞速赛**\n\n"
        f"🎯 发起者: {game['participants'][game['creator']]['name']}\n"
        f"💰 参与费用: 5 {sakura_b}\n"
        f"👥 当前玩家: {participant_count}/∞\n\n"
        f"📋 参与玩家:\n"
        f"{participant_list}\n\n"
    )
    
    if participant_count >= 2:
        text += "✅ 已满足最低人数，发起者可以开始游戏\n"
        text += f"🏆 奖池: {participant_count * 5} {sakura_b}"
    else:
        text += "⚠️ 至少需要2名玩家才能开始游戏\n"
        text += "🏆 获胜者将赢得所有投入的joy币！"
    
    await editMessage(call, text, buttons=buttons)
    await callAnswer(call, f'✅ 成功加入游戏！已扣除 5 {sakura_b}', False)


@bot.on_callback_query(filters.regex(r'f1_start_(.+)'))
async def start_multiplayer_f1_game(_, call):
    """开始多人F1游戏"""
    game_id = call.matches[0].group(1)
    
    if game_id not in multiplayer_f1_games:
        await callAnswer(call, '❌ 游戏不存在或已结束', True)
        return
    
    game = multiplayer_f1_games[game_id]
    user_id = call.from_user.id
    
    # 只有发起者可以开始游戏
    if user_id != game['creator']:
        await callAnswer(call, '❌ 只有发起者可以开始游戏', True)
        return
    
    # 检查是否已开始
    if game['started']:
        await callAnswer(call, '❌ 游戏已经开始了', True)
        return
    
    # 检查人数
    participant_count = len(game['participants'])
    if participant_count < 2:
        await callAnswer(call, '❌ 至少需要2名玩家才能开始', True)
        return
    
    # 标记游戏已开始
    game['started'] = True
    
    # 显示准备阶段
    await editMessage(call, "🎮 **多人F1竞速赛**\n\n⏳ 准备中...\n\n3秒后开始，请疯狂点击加速按钮！")
    await asyncio.sleep(3)
    
    # 激活游戏
    game['game_active'] = True
    
    # 为每个参与者创建点击按钮
    buttons_rows = []
    for pid, pdata in game['participants'].items():
        buttons_rows.append([
            InlineKeyboardButton(f"⚡ {pdata['name']}", f"f1_click_{game_id}_{pid}")
        ])
    
    buttons = InlineKeyboardMarkup(buttons_rows)
    
    text = (
        f"🎮 **多人F1竞速赛 - 进行中**\n\n"
        f"⚡ 疯狂点击你的按钮加速吧！\n"
        f"⏰ 剩余时间: 5秒\n\n"
        f"📊 实时排名:\n"
    )
    
    await editMessage(call, text, buttons=buttons)
    
    # 5秒后结束游戏
    await asyncio.sleep(5)
    await end_multiplayer_f1_game(game_id)


@bot.on_callback_query(filters.regex(r'f1_click_([^_]+)_(\d+)'))
async def handle_multiplayer_f1_click(_, call):
    """处理多人F1游戏的点击"""
    game_id = call.matches[0].group(1)
    target_user_id = int(call.matches[0].group(2))
    
    if game_id not in multiplayer_f1_games:
        await callAnswer(call, '❌ 游戏不存在或已结束', True)
        return
    
    game = multiplayer_f1_games[game_id]
    
    # 验证用户只能点击自己的按钮
    if call.from_user.id != target_user_id:
        await callAnswer(call, '❌ 请点击你自己的按钮！', True)
        return
    
    # 检查游戏是否活跃
    if not game['game_active']:
        await callAnswer(call, '⏰ 游戏已结束！', True)
        return
    
    # 增加点击次数
    game['participants'][target_user_id]['clicks'] += 1
    clicks = game['participants'][target_user_id]['clicks']
    
    await callAnswer(call, f'⚡ 第{clicks}次点击！', False)
    
    # 更新排行榜显示（不频繁更新消息，避免限流）
    try:
        # 创建按钮
        buttons_rows = []
        for pid, pdata in game['participants'].items():
            buttons_rows.append([
                InlineKeyboardButton(f"⚡ {pdata['name']}", f"f1_click_{game_id}_{pid}")
            ])
        buttons = InlineKeyboardMarkup(buttons_rows)
        
        # 排序参与者
        sorted_participants = sorted(
            game['participants'].items(),
            key=lambda x: x[1]['clicks'],
            reverse=True
        )
        
        ranking = '\n'.join([
            f"{i+1}. {p[1]['name']}: {p[1]['clicks']} 次"
            for i, p in enumerate(sorted_participants)
        ])
        
        text = (
            f"🎮 **多人F1竞速赛 - 进行中**\n\n"
            f"⚡ 疯狂点击你的按钮加速吧！\n\n"
            f"📊 实时排名:\n{ranking}"
        )
        
        await editMessage(call, text, buttons=buttons)
    except Exception:
        # 忽略更新失败，可能是点击太快
        pass


async def end_multiplayer_f1_game(game_id):
    """结束多人F1游戏并发放奖励"""
    if game_id not in multiplayer_f1_games:
        return
    
    game = multiplayer_f1_games[game_id]
    game['game_active'] = False
    
    # 计算总奖池
    total_prize = len(game['participants']) * 5
    
    # 找出最高点击次数
    max_clicks = max(p['clicks'] for p in game['participants'].values())
    
    # 找出所有获胜者（点击次数最多的）
    winners = [
        user_id for user_id, data in game['participants'].items()
        if data['clicks'] == max_clicks
    ]
    
    # 计算每个获胜者分得的奖励（向下取整）
    prize_per_winner = total_prize // len(winners)
    
    # 发放奖励
    winner_names = []
    for winner_id in winners:
        e = sql_get_emby(winner_id)
        if e:
            sql_update_emby(Emby.tg == winner_id, iv=e.iv + prize_per_winner)
        winner_names.append(game['participants'][winner_id]['name'])
    
    # 排序参与者
    sorted_participants = sorted(
        game['participants'].items(),
        key=lambda x: x[1]['clicks'],
        reverse=True
    )
    
    ranking = '\n'.join([
        f"{i+1}. {p[1]['name']}: {p[1]['clicks']} 次"
        for i, p in enumerate(sorted_participants)
    ])
    
    # 构建结果消息
    if len(winners) == 1:
        result_text = (
            f"🏎️ **多人F1竞速赛 - 结束**\n\n"
            f"🏆 获胜者: {winner_names[0]}\n"
            f"💰 奖励: {prize_per_winner} {sakura_b}\n\n"
            f"📊 最终排名:\n{ranking}\n\n"
            f"🎯 总奖池: {total_prize} {sakura_b}"
        )
    else:
        winners_str = '、'.join(winner_names)
        result_text = (
            f"🏎️ **多人F1竞速赛 - 结束**\n\n"
            f"🏆 平局获胜者: {winners_str}\n"
            f"💰 每人奖励: {prize_per_winner} {sakura_b}\n\n"
            f"📊 最终排名:\n{ranking}\n\n"
            f"🎯 总奖池: {total_prize} {sakura_b}"
        )
    
    # 尝试更新消息
    try:
        # 从游戏数据获取chat_id和message_id
        chat_id = game['chat_id']
        message_id = game['message_id']
        
        if chat_id and message_id:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=result_text
            )
    except Exception as e:
        # 如果更新失败，尝试发送新消息
        try:
            await bot.send_message(
                chat_id=game['chat_id'],
                text=result_text
            )
        except Exception:
            pass
    
    # 清理游戏数据
    del multiplayer_f1_games[game_id]
