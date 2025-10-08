"""
mzj命令 - M尊享用户每月19日随机领取奖励
"""
from datetime import datetime, timezone, timedelta
import random
from pyrogram import filters
from bot import bot, prefixes, LOGGER, sakura_b
from bot.func_helper.msg_utils import sendMessage
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby
from bot.func_helper.fix_bottons import group_f
from bot.schemas import MAX_INT_VALUE


@bot.on_message(filters.command('mzj', prefixes=prefixes))
async def mzj_command(_, msg):
    """
    mzj命令 - M尊享用户可以在每月19日使用此命令随机领取奖励
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
    
    # 随机选择一种奖励
    reward_options = ["coins", "register", "redenvelope"]
    reward_type = random.choice(reward_options)
    
    # 获取用户昵称
    user_name = msg.from_user.first_name
    
    # 处理不同类型的奖励
    if reward_type == "coins":
        # 100 Joy币
        reward = 100
        new_balance = e.iv + reward
        
        if new_balance > MAX_INT_VALUE:
            return await sendMessage(msg, f"❌ 操作失败！领取后余额将超出安全范围。", timer=30)
        
        if sql_update_emby(Emby.tg == user_id, iv=new_balance, mzj_claim_date=now):
            await sendMessage(msg, 
                            f"🎉 **M尊享礼**\n\n"
                            f"· M尊享: [{user_name}](tg://user?id={user_id}) `{user_id}`\n"
                            f"· 奖励类型: 💰 JOY币\n"
                            f"· 获得 {reward} {sakura_b}\n"
                            f"· 当前余额: **{new_balance}** {sakura_b}")
            LOGGER.info(f"【mzj】用户 {user_name}-{user_id} 随机领取了 {reward}{sakura_b}")
        else:
            return await sendMessage(msg, '⚠️ 数据库操作失败，请稍后重试', timer=30)
    
    elif reward_type == "register":
        # ME注册资格 - 荣誉奖励，不实际增加注册资格数量
        if sql_update_emby(Emby.tg == user_id, mzj_claim_date=now):
            await sendMessage(msg, 
                            f"🎉 **M尊享礼**\n\n"
                            f"· M尊享: [{user_name}](tg://user?id={user_id}) `{user_id}`\n"
                            f"· 奖励类型: 🎫 ME注册资格（荣誉）\n"
                            f"· 恭喜您获得本月荣誉奖励！")
            LOGGER.info(f"【mzj】用户 {user_name}-{user_id} 随机领取了 ME注册资格（荣誉）")
        else:
            return await sendMessage(msg, '⚠️ 数据库操作失败，请稍后重试', timer=30)
    
    elif reward_type == "redenvelope":
        # 支付宝红包 - 独立红包奖励
        if sql_update_emby(Emby.tg == user_id, mzj_claim_date=now):
            await sendMessage(msg, 
                            f"🎉 **M尊享里**\n\n"
                            f"· M用户: [{user_name}](tg://user?id={user_id}) `{user_id}`\n"
                            f"· 奖励类型: 🧧 支付宝红包\n"
                            f"· 请联系管理员领取支付宝红包\n\n")
            LOGGER.info(f"【mzj】用户 {user_name}-{user_id} 随机领取了支付宝红包")
        else:
            return await sendMessage(msg, '⚠️ 数据库操作失败，请稍后重试', timer=30)
