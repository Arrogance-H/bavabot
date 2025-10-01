import datetime
import random
from bot import bot
from pyrogram import filters
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby
from bot.schemas import Yulv

@bot.on_message(filters.group)
async def welcome_m_user(_, msg):
    # 只处理真实用户
    if not msg.from_user:
        return
    # 查数据库等级
    e = sql_get_emby(tg=msg.from_user.id)
    if not e or e.lv != 'm':
        return  # 只欢迎M尊享
    
    # 检查是否今天已经欢迎过
    today = datetime.date.today()
    if e.m_welcome_date and e.m_welcome_date.date() == today:
        return  # 今天已经欢迎过了
    
    # 更新欢迎日期到数据库
    sql_update_emby(Emby.tg == msg.from_user.id, m_welcome_date=datetime.datetime.now())
    
    # 获取用户昵称
    user_name = msg.from_user.first_name
    
    # 随机选择欢迎语并替换昵称占位符
    welcome_msg = random.choice(Yulv.load_yulv().m_welcome)
    # 如果消息中包含 {name} 占位符，则替换为用户昵称
    welcome_msg = welcome_msg.replace("{name}", user_name)
    
    await msg.reply(welcome_msg)