import datetime
import random
from bot import bot, group, LOGGER
from pyrogram import filters
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby
from bot.schemas import Yulv

@bot.on_message(filters.chat(group) & filters.group)
async def welcome_m_user(_, msg):
    # 只处理真实用户
    if not msg.from_user:
        LOGGER.debug(f"【M尊享欢迎】- 消息无from_user，跳过（可能是频道消息）")
        return
    
    LOGGER.debug(f"【M尊享欢迎】- 收到用户 {msg.from_user.first_name} (ID: {msg.from_user.id}) 的消息")
    
    # 检查数据库和用户等级
    e = sql_get_emby(tg=msg.from_user.id)
    if not e:
        LOGGER.debug(f"【M尊享欢迎】- 用户 {msg.from_user.first_name} (ID: {msg.from_user.id}) 不在数据库中")
        return
    
    # 只欢迎M尊享用户
    if e.lv != 'm':
        LOGGER.debug(f"【M尊享欢迎】- 用户 {msg.from_user.first_name} (ID: {msg.from_user.id}) 等级为 {e.lv}，不是M尊享")
        return
    
    # 检查是否今天已经欢迎过
    today = datetime.date.today()
    if e.m_welcome_date and e.m_welcome_date.date() == today:
        LOGGER.debug(f"【M尊享欢迎】- 用户 {msg.from_user.first_name} (ID: {msg.from_user.id}) 今天已经欢迎过了")
        return
    
    # 更新欢迎日期到数据库
    sql_update_emby(Emby.tg == msg.from_user.id, m_welcome_date=datetime.datetime.now())
    
    # 获取用户昵称
    user_name = msg.from_user.first_name
    
    # 随机选择欢迎语并替换昵称占位符
    welcome_msg = random.choice(Yulv.load_yulv().m_welcome)
    # 如果消息中包含 {name} 占位符，则替换为用户昵称
    welcome_msg = welcome_msg.replace("{name}", user_name)
    
    LOGGER.info(f"【M尊享欢迎】- 欢迎M尊享用户 {user_name} (ID: {msg.from_user.id})")
    await msg.reply(welcome_msg)