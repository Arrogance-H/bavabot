import asyncio
import random
from datetime import datetime, timezone, timedelta

from pyrogram import filters
from pyromod.helpers import ikb

from bot import bot, _open, sakura_b
from bot.func_helper.filters import user_in_group_on_filter
from bot.func_helper.msg_utils import callAnswer, sendMessage, deleteMessage, editMessage
from bot.func_helper.utils import cache
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby


@bot.on_callback_query(filters.regex('^checkin$') & user_in_group_on_filter)
async def user_in_checkin(_, call):
    now = datetime.now(timezone(timedelta(hours=8)))
    today = now.strftime("%Y-%m-%d")
    if _open.checkin:
        e = sql_get_emby(call.from_user.id)
        if not e:
            await callAnswer(call, '🧮 未查询到数据库', True)

        elif not e.ch or e.ch.strftime("%Y-%m-%d") < today:
            # Calculate reward but don't update database yet
            reward = random.randint(_open.checkin_reward[0], _open.checkin_reward[1])
            
            # Store the pending checkin data in cache
            checkin_data = {
                'reward': reward,
                'date': now,
                'user_id': call.from_user.id
            }
            cache.set(f'pending_checkin_{call.from_user.id}', checkin_data, ttl=300)  # 5 minutes to claim
            
            # Create claim reward button
            claim_button = ikb([[('🎁 领取奖励', f'claim_checkin_{call.from_user.id}'), ('❌ 取消', 'closeit')]])
            
            text = f'✅ **签到检查完成**\n🎁 **可领取奖励** | {reward} {sakura_b}\n⏳ **签到日期** | {now.strftime("%Y-%m-%d")}\n\n💡 点击下方按钮领取奖励'
            await editMessage(call, text=text, buttons=claim_button)

        else:
            await callAnswer(call, '⭕ 您今天已经签到过了！签到是无聊的活动哦。', True)
    else:
        await callAnswer(call, '❌ 未开启签到功能，等待！', True)


@bot.on_callback_query(filters.regex(r'^claim_checkin_(\d+)$') & user_in_group_on_filter)
async def claim_checkin_reward(_, call):
    user_id = int(call.matches[0].group(1))
    
    # Verify the user claiming is the same as the one who checked in
    if call.from_user.id != user_id:
        await callAnswer(call, '❌ 您无法领取他人的签到奖励', True)
        return
    
    # Get the pending checkin data from cache
    checkin_data = cache.get(f'pending_checkin_{user_id}')
    if not checkin_data:
        await callAnswer(call, '⏰ 签到数据已过期，请重新签到', True)
        return
    
    # Get current user data
    e = sql_get_emby(user_id)
    if not e:
        await callAnswer(call, '🧮 未查询到数据库', True)
        return
    
    # Double check if user hasn't already checked in today
    now = datetime.now(timezone(timedelta(hours=8)))
    today = now.strftime("%Y-%m-%d")
    if e.ch and e.ch.strftime("%Y-%m-%d") >= today:
        await callAnswer(call, '⭕ 您今天已经签到过了！', True)
        return
    
    # Apply the reward and update database
    reward = checkin_data['reward']
    checkin_date = checkin_data['date']
    s = e.iv + reward
    sql_update_emby(Emby.tg == user_id, iv=s, ch=checkin_date)
    
    # Clear the cache
    cache.delete(f'pending_checkin_{user_id}')
    
    # Show success message
    text = f'🎉 **签到成功** | {reward} {sakura_b}\n💴 **当前持有** | {s} {sakura_b}\n⏳ **签到日期** | {checkin_date.strftime("%Y-%m-%d")}'
    await editMessage(call, text=text)
