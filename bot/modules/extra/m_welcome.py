"""
M尊享用户欢迎功能
当M等级用户在群组中发言时自动发送欢迎消息（每天仅一次）
使用配置文件中的m_users列表，无需数据库查询
"""
import datetime
import random
from bot import bot, group, m_users, LOGGER
from pyrogram import filters
from bot.schemas import Yulv

# 使用缓存来记录今天已经欢迎过的用户
# 格式: {user_id: date}
_welcomed_today = {}


@bot.on_message(filters.chat(group) & filters.group & filters.text, group=1)
async def welcome_m_user(_, msg):
    """
    M尊享用户欢迎处理器
    - 使用 group=1 确保在其他handler之后执行
    - 使用 filters.text 仅处理文本消息，提高性能
    - 使用配置文件m_users列表，无需数据库查询
    """
    # 只处理真实用户
    if not msg.from_user:
        return
    
    user_id = msg.from_user.id
    
    # 检查用户是否在M尊享列表中
    if user_id not in m_users:
        return
    
    # 检查是否今天已经欢迎过
    today = datetime.date.today()
    if user_id in _welcomed_today and _welcomed_today[user_id] == today:
        LOGGER.debug(f"【M尊享欢迎】- 用户 {msg.from_user.first_name} (ID: {user_id}) 今天已经欢迎过了")
        return
    
    # 记录今天已经欢迎过
    _welcomed_today[user_id] = today
    
    # 获取用户昵称
    user_name = msg.from_user.first_name
    
    # 随机选择欢迎语并替换昵称占位符
    welcome_msg = random.choice(Yulv.load_yulv().m_welcome)
    welcome_msg = welcome_msg.replace("{name}", user_name)
    
    LOGGER.info(f"【M尊享欢迎】- 欢迎M尊享用户 {user_name} (ID: {user_id})")
    await msg.reply(welcome_msg)