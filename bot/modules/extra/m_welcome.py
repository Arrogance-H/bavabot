import datetime
import random
from bot import bot, group, LOGGER
from pyrogram import filters
from bot.schemas import Yulv

# 全局变量记录上次发送欢迎消息的时间（每个群组独立）
last_welcome_time = {}

# 配置参数
WELCOME_PROBABILITY = 0.05  # 5% 的概率发送欢迎消息
WELCOME_COOLDOWN_MINUTES = 60  # 冷却时间（分钟），防止刷屏
TARGET_USER_ID = 7095984257  # 目标用户TG ID

@bot.on_message(filters.chat(group) & filters.group)
async def welcome_random_user(_, msg):
    """
    当群组中有人发言时，随机发送一条欢迎词
    - 仅针对特定用户 (TG ID: 7095984257) 触发
    - 有一定概率（默认5%）发送欢迎消息
    - 使用冷却时间防止频繁发送
    """
    # 只处理真实用户
    if not msg.from_user:
        LOGGER.debug(f"【随机欢迎】- 消息无from_user，跳过（可能是频道消息）")
        return
    
    # 只针对特定用户触发
    if msg.from_user.id != TARGET_USER_ID:
        return
    
    # 跳过命令消息（以/开头的消息）
    if msg.text and msg.text.startswith('/'):
        return
    
    chat_id = msg.chat.id
    current_time = datetime.datetime.now()
    
    # 检查冷却时间
    if chat_id in last_welcome_time:
        time_diff = (current_time - last_welcome_time[chat_id]).total_seconds() / 60
        if time_diff < WELCOME_COOLDOWN_MINUTES:
            LOGGER.debug(f"【随机欢迎】- 群组 {chat_id} 在冷却时间内，距离上次欢迎 {time_diff:.1f} 分钟")
            return
    
    # 随机概率判断是否发送欢迎消息
    if random.random() > WELCOME_PROBABILITY:
        return
    
    # 获取用户昵称
    user_name = msg.from_user.first_name
    
    # 随机选择欢迎语并替换昵称占位符
    welcome_msg = random.choice(Yulv.load_yulv().m_welcome)
    welcome_msg = welcome_msg.replace("{name}", user_name)
    
    # 更新最后欢迎时间
    last_welcome_time[chat_id] = current_time
    
    LOGGER.info(f"【随机欢迎】- 在群组 {chat_id} 向用户 {user_name} (ID: {msg.from_user.id}) 发送欢迎消息")
    await msg.reply(welcome_msg)