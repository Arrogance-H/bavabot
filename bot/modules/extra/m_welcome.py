import datetime
from bot import bot
from pyrogram import filters
from bot.sql_helper.sql_emby import sql_get_emby

# 记录当天已欢迎的 M尊享用户
m_first_speak = {}

def is_first_speak_today(user_id):
    today = datetime.date.today().isoformat()
    if m_first_speak.get(user_id) == today:
        return False
    m_first_speak[user_id] = today
    return True

@bot.on_message(filters.group)
async def welcome_m_user(_, msg):
    # 只处理真实用户
    if not msg.from_user:
        return
    # 查数据库等级
    e = sql_get_emby(tg=msg.from_user.id)
    if not e or e.lv != 'm':
        return  # 只欢迎M尊享
    if is_first_speak_today(msg.from_user.id):
        await msg.reply("🎉 欢迎尊贵的M尊享用户首次发言！")