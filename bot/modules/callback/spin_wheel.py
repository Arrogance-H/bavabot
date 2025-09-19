import asyncio
import random
from datetime import datetime, timezone, timedelta

from pyrogram import filters

from bot import bot, _open, sakura_b
from bot.func_helper.filters import user_in_group_on_filter
from bot.func_helper.msg_utils import callAnswer, sendMessage, deleteMessage
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby


# 简单的内存存储，记录用户今天是否已经转过转盘 
# 格式: {user_id: "YYYY-MM-DD"}
spin_wheel_daily_records = {}


def cleanup_old_spin_records():
    """清理过期的转盘记录，只保留今天的"""
    today = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    global spin_wheel_daily_records
    spin_wheel_daily_records = {uid: date for uid, date in spin_wheel_daily_records.items() if date == today}


@bot.on_callback_query(filters.regex('spin_wheel') & user_in_group_on_filter)
async def user_spin_wheel(_, call):
    now = datetime.now(timezone(timedelta(hours=8)))  
    today = now.strftime("%Y-%m-%d")
    user_id = call.from_user.id
    
    if not _open.checkin:  # 使用checkin开关来控制转盘功能
        await callAnswer(call, '❌ 转盘功能暂未开启！', True)
        return
        
    e = sql_get_emby(user_id)
    if not e:
        await callAnswer(call, '🧮 未查询到数据库', True)
        return

    # 检查是否已经转过盘（使用内存存储）
    # 定期清理过期记录
    cleanup_old_spin_records()
    last_spin_date = spin_wheel_daily_records.get(user_id)
    if last_spin_date == today:
        await callAnswer(call, '⭕ 您今天已经转过转盘了！明天再来试试运气吧。', True)
        return

    # 转盘奖励概率设置
    # 空气: 99.8%，1币: 0.1%，19币: 0.1%
    rand_num = random.random() * 100  # 0-100的随机数
    
    if rand_num < 0.1:  # 0.1% 概率获得19币
        reward = 19
        reward_text = f"🎊 **恭喜中大奖！** 获得 {reward} {sakura_b}！"
        emoji = "🎊"
    elif rand_num < 0.2:  # 0.1% 概率获得1币  
        reward = 1
        reward_text = f"🎉 **小有所获！** 获得 {reward} {sakura_b}！"
        emoji = "🎉"
    else:  # 99.8% 概率获得空气
        reward = 0
        reward_text = "💨 **很遗憾，获得了空气**"
        emoji = "💨"

    # 更新用户积分和记录转盘使用
    new_iv = e.iv + reward
    sql_update_emby(Emby.tg == user_id, iv=new_iv)
    spin_wheel_daily_records[user_id] = today  # 记录今天已转盘
    
    # 构建消息文本
    spin_animation = "🎯 转盘旋转中...\n\n🌪️ ➡️ 🎁 ➡️ 💨 ➡️ 🎊 ➡️ 🌟\n\n"
    
    if reward > 0:
        text = f'{spin_animation}{emoji} **转盘结果**\n\n{reward_text}\n💴 **当前持有** | {new_iv} {sakura_b}\n⏰ **转盘日期** | {today}'
    else:
        text = f'{spin_animation}{emoji} **转盘结果**\n\n{reward_text}\n💴 **当前持有** | {new_iv} {sakura_b}\n⏰ **转盘日期** | {today}\n\n💡 明天再来试试运气吧！'
    
    await asyncio.gather(deleteMessage(call), sendMessage(call, text=text))