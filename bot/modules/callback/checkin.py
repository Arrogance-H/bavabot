import asyncio
import random
from datetime import datetime, timezone, timedelta

from pyrogram import filters

from bot import bot, _open, sakura_b
from bot.func_helper.filters import user_in_group_on_filter
from bot.func_helper.msg_utils import callAnswer, sendMessage, deleteMessage
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby


@bot.on_callback_query(filters.regex('checkin') & user_in_group_on_filter)
async def user_in_checkin(_, call):
    now = datetime.now(timezone(timedelta(hours=8)))
    today = now.strftime("%Y-%m-%d")
    if _open.checkin:
        e = sql_get_emby(call.from_user.id)
        if not e:
            await callAnswer(call, '🧮 未查询到数据库', True)
            return
        
        # Check if user level is 'a' or 'b'
        if e.lv not in ['a', 'b']:
            await callAnswer(call, '❌ 您的等级不足，无法使用签到功能', True)
            return

        elif not e.ch or e.ch.strftime("%Y-%m-%d") < today:
            # First step: Show check-in success and claim reward button
            reward = random.randint(_open.checkin_reward[0], _open.checkin_reward[1])
            # Store the reward temporarily (we'll use the user's current timestamp to track this)
            text = f'🎯 **签到成功！**\n🎁 **可领取奖励** | {reward} {sakura_b}\n⏳ **签到日期** | {now.strftime("%Y-%m-%d")}\n\n💡 点击下方按钮领取奖励'
            from bot.func_helper.fix_bottons import ikb
            claim_button = ikb([[('🎁 领取奖励', f'claim_reward-{reward}'), ('🔙 返回主页', 'back_start')]])
            await asyncio.gather(deleteMessage(call), sendMessage(call, text=text, buttons=claim_button))

        else:
            await callAnswer(call, '⭕ 您今天已经签到过了！签到是无聊的活动哦。', True)
    else:
        await callAnswer(call, '❌ 未开启签到功能，等待！', True)


@bot.on_callback_query(filters.regex('claim_reward') & user_in_group_on_filter)
async def claim_checkin_reward(_, call):
    now = datetime.now(timezone(timedelta(hours=8)))
    today = now.strftime("%Y-%m-%d")
    
    # Extract reward amount from callback data
    try:
        reward = int(call.data.split('-')[1])
    except (IndexError, ValueError):
        await callAnswer(call, '❌ 无效的奖励数据', True)
        return
    
    e = sql_get_emby(call.from_user.id)
    if not e:
        await callAnswer(call, '🧮 未查询到数据库', True)
        return
    
    # Check if user already claimed today's reward
    if e.ch and e.ch.strftime("%Y-%m-%d") >= today:
        await callAnswer(call, '⭕ 您今天已经领取过奖励了！', True)
        return
    
    # Second step: Actually give the reward
    s = e.iv + reward
    sql_update_emby(Emby.tg == call.from_user.id, iv=s, ch=now)
    text = f'🎉 **奖励领取成功！**\n💰 **获得奖励** | {reward} {sakura_b}\n💴 **当前持有** | {s} {sakura_b}\n⏳ **签到日期** | {now.strftime("%Y-%m-%d")}'
    await asyncio.gather(deleteMessage(call), sendMessage(call, text=text))
