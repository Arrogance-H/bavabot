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
    if not _open.checkin:
        await callAnswer(call, '❌ 未开启签到功能，等待！', True)
        return
    
    e = sql_get_emby(call.from_user.id)
    if not e:
        await callAnswer(call, '🧮 未查询到数据库', True)
        return
    
    user_id = call.from_user.id
    
    # 创建准备按钮
    ready_button = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ 准备好了", f"punch_ready_{user_id}")]
    ])
    
    await editMessage(call, "🎮 **打卡游戏**\n\n准备好开始了吗？", buttons=ready_button)


@bot.on_callback_query(filters.regex(r'punch_ready_(\d+)'))
async def punch_ready(_, call):
    """处理准备按钮点击，3秒后显示加速按钮"""
    user_id = int(call.matches[0].group(1))
    
    # 验证用户身份
    if call.from_user.id != user_id:
        await callAnswer(call, '❌ 这不是你的游戏！', True)
        return
    
    # 初始化用户游戏会话
    punch_in_sessions[user_id] = {
        'clicks': 0,
        'game_active': False
    }
    
    await editMessage(call, "🎮 **打卡游戏**\n\n⏳ 准备中...\n\n3秒后开始，请疯狂点击加速按钮！")
    
    # 等待3秒
    await asyncio.sleep(3)
    
    # 检查会话是否仍然存在（防止用户中途退出）
    if user_id not in punch_in_sessions:
        return
    
    # 激活游戏并显示加速按钮
    punch_in_sessions[user_id]['game_active'] = True
    
    speed_button = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ 加速吧！", f"punch_click_{user_id}")]
    ])
    
    await editMessage(call, "🎮 **打卡游戏**\n\n⚡ 加速吧！\n\n📊 点击次数: 0\n⏰ 剩余时间: 3秒", buttons=speed_button)
    
    # 3秒后结束游戏
    await asyncio.sleep(3)
    await end_punch_game(call, user_id)


@bot.on_callback_query(filters.regex(r'punch_click_(\d+)'))
async def handle_punch_click(_, call):
    """处理加速按钮点击"""
    user_id = int(call.matches[0].group(1))
    
    # 验证用户身份
    if call.from_user.id != user_id:
        await callAnswer(call, '❌ 这不是你的游戏！', True)
        return
    
    # 检查游戏是否活跃
    if user_id not in punch_in_sessions or not punch_in_sessions[user_id]['game_active']:
        await callAnswer(call, '⏰ 游戏已结束！', True)
        return
    
    # 增加点击次数
    punch_in_sessions[user_id]['clicks'] += 1
    clicks = punch_in_sessions[user_id]['clicks']
    
    # 更新显示但不阻塞
    try:
        speed_button = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚡ 加速吧！", f"punch_click_{user_id}")]
        ])
        
        await editMessage(call, f"🎮 **打卡游戏**\n\n⚡ 加速吧！\n\n📊 点击次数: {clicks}", buttons=speed_button)
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
    
    # 计算奖励
    reward = 0
    reward_text = ""
    
    if clicks <= 3:
        reward_text = "💔 **没有奖励**\n\n点击次数太少了，需要更努力哦！"
    elif clicks <= 12:
        reward = random.randint(1, 3)
        reward_text = f"🎉 **获得奖励**: {reward} {sakura_b}\n\n不错的手速！"
    else:
        reward = 19
        reward_text = f"🏆 **超级奖励**: {reward} {sakura_b}\n\n手速惊人！"
    
    # 发放奖励
    if reward > 0:
        e = sql_get_emby(user_id)
        if e:
            new_total = e.iv + reward
            sql_update_emby(Emby.tg == user_id, iv=new_total)
            reward_text += f"\n💰 **当前持有**: {new_total} {sakura_b}"
    
    result_text = f"🎮 **打卡游戏结果**\n\n📊 **点击次数**: {clicks}\n{reward_text}"
    
    # 清理会话数据
    del punch_in_sessions[user_id]
    
    try:
        await editMessage(call, result_text)
    except Exception:
        # 如果编辑失败，发送新消息
        await sendMessage(call, text=result_text)
