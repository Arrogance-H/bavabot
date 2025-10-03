"""
mzj命令 - 用户领取100joy币
"""
from datetime import datetime, timezone, timedelta
from pyrogram import filters
from bot import bot, prefixes, LOGGER, sakura_b
from bot.func_helper.msg_utils import sendMessage, deleteMessage
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby
from bot.func_helper.fix_bottons import group_f
from bot.schemas import MAX_INT_VALUE


@bot.on_message(filters.command('mzj', prefixes=prefixes))
async def mzj_command(_, msg):
    """
    mzj命令 - M尊享用户可以在每月19日使用此命令领取100joy币
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
    
    # 计算新的joy币数量
    reward = 100
    new_balance = e.iv + reward
    
    # 检查是否超出安全范围
    if new_balance > MAX_INT_VALUE:
        return await sendMessage(msg, f"❌ 操作失败！领取后余额将超出安全范围。", timer=30)
    
    # 更新用户的joy币
    if sql_update_emby(Emby.tg == user_id, iv=new_balance):
        await sendMessage(msg, 
                         f"🎉 **领取成功！**\n\n"
                         f"· 获得 {reward} {sakura_b}\n"
                         f"· 当前余额: **{new_balance}** {sakura_b}",
                         timer=60)
        await deleteMessage(msg)
        LOGGER.info(f"【mzj】用户 {msg.from_user.first_name}-{user_id} 领取了 {reward}{sakura_b}")
    else:
        await sendMessage(msg, '⚠️ 数据库操作失败，请稍后重试', timer=30)
        LOGGER.error(f"【mzj】用户 {msg.from_user.first_name}-{user_id} 领取失败 - 数据库错误")
