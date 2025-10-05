"""
M尊享用户欢迎功能
当M等级用户在群组中发言时自动发送欢迎消息（每天仅一次）
"""
import datetime
import random
from bot import bot, group, LOGGER
from pyrogram import filters
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby
from bot.schemas import Yulv

# 使用缓存来避免频繁查询数据库
# 格式: {user_id: last_check_time}
_last_check_cache = {}
_cache_timeout = 300  # 5分钟缓存


@bot.on_message(filters.chat(group) & filters.group & filters.text, group=1)
async def welcome_m_user(_, msg):
    """
    M尊享用户欢迎处理器
    - 使用 group=1 确保在其他handler之后执行
    - 使用 filters.text 仅处理文本消息，提高性能
    """
    # 只处理真实用户
    if not msg.from_user:
        return
    
    user_id = msg.from_user.id
    
    # 测试模式：允许任何用户发送"test"来测试功能
    if msg.text and msg.text.strip().lower() == "test":
        LOGGER.info(f"【M尊享欢迎】- 测试模式：用户 {msg.from_user.first_name} (ID: {user_id}) 发送了测试消息")
        user_name = msg.from_user.first_name
        welcome_msg = random.choice(Yulv.load_yulv().m_welcome)
        welcome_msg = welcome_msg.replace("{name}", user_name)
        await msg.reply(welcome_msg)
        return
    
    # 性能优化：使用缓存减少数据库查询
    current_time = datetime.datetime.now()
    if user_id in _last_check_cache:
        last_check = _last_check_cache[user_id]
        if (current_time - last_check).total_seconds() < _cache_timeout:
            # 5分钟内已经检查过，跳过
            return
    
    # 更新缓存时间
    _last_check_cache[user_id] = current_time
    
    LOGGER.debug(f"【M尊享欢迎】- 收到用户 {msg.from_user.first_name} (ID: {user_id}) 的消息")
    
    # 检查数据库和用户等级
    e = sql_get_emby(tg=user_id)
    if not e:
        LOGGER.debug(f"【M尊享欢迎】- 用户 {msg.from_user.first_name} (ID: {user_id}) 不在数据库中")
        return
    
    # 只欢迎M尊享用户
    if e.lv != 'm':
        LOGGER.debug(f"【M尊享欢迎】- 用户 {msg.from_user.first_name} (ID: {user_id}) 等级为 {e.lv}，不是M尊享")
        return
    
    # 检查是否今天已经欢迎过
    today = datetime.date.today()
    if e.m_welcome_date and e.m_welcome_date.date() == today:
        LOGGER.debug(f"【M尊享欢迎】- 用户 {msg.from_user.first_name} (ID: {user_id}) 今天已经欢迎过了")
        return
    
    # 更新欢迎日期到数据库
    sql_update_emby(Emby.tg == user_id, m_welcome_date=datetime.datetime.now())
    
    # 获取用户昵称
    user_name = msg.from_user.first_name
    
    # 随机选择欢迎语并替换昵称占位符
    welcome_msg = random.choice(Yulv.load_yulv().m_welcome)
    welcome_msg = welcome_msg.replace("{name}", user_name)
    
    LOGGER.info(f"【M尊享欢迎】- 欢迎M尊享用户 {user_name} (ID: {user_id})")
    await msg.reply(welcome_msg)