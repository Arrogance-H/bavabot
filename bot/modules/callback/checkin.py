import asyncio
import random
from datetime import datetime, timezone, timedelta

from pyrogram import filters
from pyromod.helpers import ikb

from bot import bot, _open, sakura_b
from bot.func_helper.filters import user_in_group_on_filter
from bot.func_helper.msg_utils import callAnswer, sendMessage, deleteMessage, editMessage
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby


def get_daily_reward(user_id: int, date: str) -> int:
    """Generate consistent daily reward based on user ID and date"""
    # Use user ID and date as seed for consistent random reward
    seed = hash(f"{user_id}_{date}") % (2**31)
    random.seed(seed)
    reward = random.randint(_open.checkin_reward[0], _open.checkin_reward[1])
    # Reset random seed
    random.seed()
    return reward


@bot.on_callback_query(filters.regex('checkin') & user_in_group_on_filter)
async def user_in_checkin(_, call):
    now = datetime.now(timezone(timedelta(hours=8)))
    today = now.strftime("%Y-%m-%d")
    if _open.checkin:
        e = sql_get_emby(call.from_user.id)
        if not e:
            await callAnswer(call, '🧮 未查询到数据库', True)

        elif not e.ch or e.ch.strftime("%Y-%m-%d") < today:
            # First step: Record checkin but don't give rewards yet
            reward = get_daily_reward(call.from_user.id, today)
            sql_update_emby(Emby.tg == call.from_user.id, ch=now)
            
            # Create claim reward button
            claim_button = ikb([[('🎁 领取奖励', f'claim_checkin_reward_{reward}'), ('❌ 关闭', 'closeit')]])
            
            text = f'✅ **签到成功**\n🎯 **今日奖励** | {reward} {sakura_b}\n⏳ **签到日期** | {now.strftime("%Y-%m-%d")}\n\n🔔 点击下方按钮领取奖励！'
            await asyncio.gather(deleteMessage(call), sendMessage(call, text=text, buttons=claim_button))

        elif e.ch and e.ch.strftime("%Y-%m-%d") == today and (not e.ch_claimed or e.ch_claimed.strftime("%Y-%m-%d") < today):
            # User checked in today but hasn't claimed reward yet - show consistent reward
            reward = get_daily_reward(call.from_user.id, today)
            
            # Create claim reward button
            claim_button = ikb([[('🎁 领取奖励', f'claim_checkin_reward_{reward}'), ('❌ 关闭', 'closeit')]])
            
            text = f'🎯 **今日签到已完成**\n🎁 **待领取奖励** | {reward} {sakura_b}\n⏳ **签到日期** | {now.strftime("%Y-%m-%d")}\n\n🔔 点击下方按钮领取奖励！'
            await asyncio.gather(deleteMessage(call), sendMessage(call, text=text, buttons=claim_button))
        else:
            await callAnswer(call, '⭕ 您今天已经签到过了！签到是无聊的活动哦。', True)
    else:
        await callAnswer(call, '❌ 未开启签到功能，等待！', True)


@bot.on_callback_query(filters.regex('claim_checkin_reward_') & user_in_group_on_filter)
async def claim_checkin_reward(_, call):
    now = datetime.now(timezone(timedelta(hours=8)))
    today = now.strftime("%Y-%m-%d")
    
    # Extract reward amount from callback data
    try:
        reward = int(call.data.split('_')[-1])
    except (ValueError, IndexError):
        await callAnswer(call, '❌ 无效的奖励数据', True)
        return
    
    e = sql_get_emby(call.from_user.id)
    if not e:
        await callAnswer(call, '🧮 未查询到数据库', True)
        return
    
    # Verify the reward amount is correct for this user and date
    expected_reward = get_daily_reward(call.from_user.id, today)
    if reward != expected_reward:
        await callAnswer(call, '❌ 奖励数据不匹配，请重新签到', True)
        return
    
    # Check if user has checked in today but not claimed yet
    if e.ch and e.ch.strftime("%Y-%m-%d") == today and (not e.ch_claimed or e.ch_claimed.strftime("%Y-%m-%d") < today):
        # Give the reward
        s = e.iv + reward
        sql_update_emby(Emby.tg == call.from_user.id, iv=s, ch_claimed=now)
        
        text = f'🎉 **奖励领取成功**\n💰 **获得奖励** | {reward} {sakura_b}\n💴 **当前持有** | {s} {sakura_b}\n⏳ **领取时间** | {now.strftime("%Y-%m-%d %H:%M:%S")}'
        await asyncio.gather(deleteMessage(call), sendMessage(call, text=text))
    elif e.ch_claimed and e.ch_claimed.strftime("%Y-%m-%d") == today:
        await callAnswer(call, '⭕ 您今天已经领取过奖励了！', True)
    else:
        await callAnswer(call, '❌ 您今天还没有签到，请先签到！', True)
