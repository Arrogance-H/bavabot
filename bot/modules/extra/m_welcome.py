"""
M尊享用户欢迎功能
当M等级用户在群组中发言时自动发送欢迎消息（每天仅一次）
使用配置文件中的m_users列表确定用户身份
使用数据库m_welcome_date字段记录欢迎日期
"""
import datetime
import random
from bot import bot, group, m_users, LOGGER
from pyrogram import filters
from bot.schemas import Yulv
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby


@bot.on_message(filters.chat(group) & filters.group & filters.text, group=1)
async def welcome_m_user(_, msg):
    """
    M尊享用户欢迎处理器
    - 使用 group=1 确保在其他handler之后执行
    - 使用 filters.text 仅处理文本消息，提高性能
    - 使用配置文件m_users列表确定用户身份
    - 使用数据库m_welcome_date字段记录每日欢迎
    """
    # 只处理真实用户
    if not msg.from_user:
        return
    
    user_id = msg.from_user.id
    
    # 检查用户是否在M尊享列表中
    if user_id not in m_users:
        return
    
    # 从数据库获取用户信息
    e = sql_get_emby(tg=user_id)
    if not e:
        LOGGER.debug(f"【M尊享欢迎】- 用户 {msg.from_user.first_name} (ID: {user_id}) 不在数据库中")
        return
    
    # 检查是否今天已经欢迎过
    today = datetime.date.today()
    if e.m_welcome_date:
        last_welcome_date = e.m_welcome_date.date()
        if last_welcome_date == today:
            LOGGER.debug(f"【M尊享欢迎】- 用户 {msg.from_user.first_name} (ID: {user_id}) 今天已经欢迎过了")
            return
    
    # 获取用户昵称
    user_name = msg.from_user.first_name
    
    # 随机选择欢迎语并替换昵称占位符
    welcome_msg = random.choice(Yulv.load_yulv().m_welcome)
    welcome_msg = welcome_msg.replace("{name}", user_name)
    
    # 发送欢迎消息
    LOGGER.info(f"【M尊享欢迎】- 欢迎M尊享用户 {user_name} (ID: {user_id})")
    await msg.reply(welcome_msg)
    
    # 更新数据库中的欢迎日期
    now = datetime.datetime.now()
    sql_update_emby(Emby.tg == user_id, m_welcome_date=now)