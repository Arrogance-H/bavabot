import asyncio
import random
from datetime import datetime, timezone, timedelta

from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot import bot, _open, sakura_b
from bot.func_helper.filters import user_in_group_on_filter
from bot.func_helper.msg_utils import callAnswer, sendMessage, deleteMessage, editMessage
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby

# 存储用户打卡游戏状态的临时数据
punch_in_sessions = {}

# 存储用户每日F1游戏次数的内存数据 {user_id: {'count': int, 'date': 'YYYY-MM-DD'}}
daily_punch_limits = {}

# F1游戏每日限制次数
DAILY_PUNCH_LIMIT = 3


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
