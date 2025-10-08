"""
mzj命令 - M尊享用户每月19日领取奖励
"""
from datetime import datetime, timezone, timedelta
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import bot, prefixes, LOGGER, sakura_b
from bot.func_helper.msg_utils import sendMessage, deleteMessage, callAnswer, editMessage
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby
from bot.func_helper.fix_bottons import group_f
from bot.schemas import MAX_INT_VALUE


@bot.on_message(filters.command('mzj', prefixes=prefixes))
async def mzj_command(_, msg):
    """
    mzj命令 - M尊享用户可以在每月19日使用此命令领取奖励（三选一）
    """
    user_id = msg.from_user.id
    
    # 获取用户信息
    e = sql_get_emby(tg=user_id)
    if not e:
        return await sendMessage(msg, f"数据库中没有你的信息。请先私聊我 /start", buttons=group_f, timer=30)
    
    # 检查用户是否为M尊享
    if e.lv != 'm':
        return await sendMessage(msg, f"❌ 仅限M尊享用户使用", timer=30)
    
    # 检查是否为每月19日
    now = datetime.now(timezone(timedelta(hours=8)))
    if now.day != 19:
        return await sendMessage(msg, f"❌ 仅限每月19日领取", timer=30)
    
    # 检查本月是否已领取
    if e.mzj_claim_date:
        last_claim = e.mzj_claim_date
        # 将last_claim转换为同一时区以便比较
        if last_claim.tzinfo is None:
            last_claim = last_claim.replace(tzinfo=timezone(timedelta(hours=8)))
        else:
            last_claim = last_claim.astimezone(timezone(timedelta(hours=8)))
        
        # 检查是否在同一个月
        if last_claim.year == now.year and last_claim.month == now.month:
            next_claim_date = (now.replace(day=1) + timedelta(days=32)).replace(day=19)
            return await sendMessage(msg, 
                                   f"❌ 本月已领取过奖励\n"
                                   f"下次领取时间: {next_claim_date.strftime('%Y-%m-%d')}", 
                                   timer=30)
    
    # 显示奖励选项
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 100 Joy币", callback_data=f"mzj_reward-coins-{user_id}")],
        [InlineKeyboardButton("🎫 ME注册资格", callback_data=f"mzj_reward-register-{user_id}")],
        [InlineKeyboardButton("🧧 红包", callback_data=f"mzj_reward-redenvelope-{user_id}")],
    ])
    
    await sendMessage(msg, 
                     f"🎉 **M尊享月度福利**\n\n"
                     f"请选择你要领取的奖励（三选一）：\n\n"
                     f"💰 **100 Joy币** - 直接充值到账户\n"
                     f"🎫 **ME注册资格** - 获得1个注册资格\n"
                     f"🧧 **红包** - 获得一个价值100的红包\n\n"
                     f"⚠️ 每月只能领取一次，请谨慎选择！",
                     buttons=keyboard,
                     timer=120)
    await deleteMessage(msg)


@bot.on_callback_query(filters.regex(r'^mzj_reward-'))
async def mzj_reward_callback(_, call):
    """
    处理mzj奖励选择的回调
    """
    parts = call.data.split("-")
    reward_type = parts[1]
    claimed_user_id = int(parts[2])
    
    # 检查是否为本人操作
    if call.from_user.id != claimed_user_id:
        return await callAnswer(call, "❌ 这不是你的奖励！", show_alert=True)
    
    user_id = call.from_user.id
    
    # 再次获取用户信息并验证
    e = sql_get_emby(tg=user_id)
    if not e:
        return await callAnswer(call, "❌ 数据库中没有你的信息", show_alert=True)
    
    if e.lv != 'm':
        return await callAnswer(call, "❌ 仅限M尊享用户使用", show_alert=True)
    
    # 检查是否为每月19日
    now = datetime.now(timezone(timedelta(hours=8)))
    if now.day != 19:
        return await callAnswer(call, "❌ 仅限每月19日领取", show_alert=True)
    
    # 再次检查本月是否已领取
    if e.mzj_claim_date:
        last_claim = e.mzj_claim_date
        if last_claim.tzinfo is None:
            last_claim = last_claim.replace(tzinfo=timezone(timedelta(hours=8)))
        else:
            last_claim = last_claim.astimezone(timezone(timedelta(hours=8)))
        
        if last_claim.year == now.year and last_claim.month == now.month:
            return await callAnswer(call, "❌ 本月已领取过奖励", show_alert=True)
    
    # 处理不同类型的奖励
    if reward_type == "coins":
        # 100 Joy币
        reward = 100
        new_balance = e.iv + reward
        
        if new_balance > MAX_INT_VALUE:
            return await callAnswer(call, "❌ 操作失败！领取后余额将超出安全范围。", show_alert=True)
        
        if sql_update_emby(Emby.tg == user_id, iv=new_balance, mzj_claim_date=now):
            await editMessage(call, 
                            f"🎉 **领取成功！**\n\n"
                            f"· 奖励类型: 💰 Joy币\n"
                            f"· 获得 {reward} {sakura_b}\n"
                            f"· 当前余额: **{new_balance}** {sakura_b}")
            LOGGER.info(f"【mzj】用户 {call.from_user.first_name}-{user_id} 领取了 {reward}{sakura_b}")
        else:
            return await callAnswer(call, "⚠️ 数据库操作失败，请稍后重试", show_alert=True)
    
    elif reward_type == "register":
        # ME注册资格
        new_us = e.us + 1
        
        if sql_update_emby(Emby.tg == user_id, us=new_us, mzj_claim_date=now):
            await editMessage(call, 
                            f"🎉 **领取成功！**\n\n"
                            f"· 奖励类型: 🎫 ME注册资格\n"
                            f"· 获得 1 个注册资格\n"
                            f"· 当前注册资格数: **{new_us}**")
            LOGGER.info(f"【mzj】用户 {call.from_user.first_name}-{user_id} 领取了 1个注册资格")
        else:
            return await callAnswer(call, "⚠️ 数据库操作失败，请稍后重试", show_alert=True)
    
    elif reward_type == "redenvelope":
        # 红包
        red_amount = 100
        new_balance = e.iv + red_amount
        
        if new_balance > MAX_INT_VALUE:
            return await callAnswer(call, "❌ 操作失败！领取后余额将超出安全范围。", show_alert=True)
        
        if sql_update_emby(Emby.tg == user_id, iv=new_balance, mzj_claim_date=now):
            await editMessage(call, 
                            f"🎉 **领取成功！**\n\n"
                            f"· 奖励类型: 🧧 红包\n"
                            f"· 获得 {red_amount} {sakura_b}\n"
                            f"· 当前余额: **{new_balance}** {sakura_b}\n\n"
                            f"💡 你可以使用这些{sakura_b}在群组中发红包给其他用户！")
            LOGGER.info(f"【mzj】用户 {call.from_user.first_name}-{user_id} 领取了红包 {red_amount}{sakura_b}")
        else:
            return await callAnswer(call, "⚠️ 数据库操作失败，请稍后重试", show_alert=True)
