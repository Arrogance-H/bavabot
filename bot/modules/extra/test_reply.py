"""
test_reply - 简单的测试消息回复功能
当用户在群组中发送 "test" 时，bot回复 "测试成功"

Author: Bot
Date: 2025
"""

from bot import bot, group, LOGGER
from pyrogram import filters


@bot.on_message(filters.chat(group) & filters.group)
async def test_reply_handler(_, msg):
    """处理测试消息，当用户发送test时回复测试成功"""
    # 只处理真实用户的文本消息
    if not msg.from_user:
        return
    
    # 检查消息内容是否为 "test"
    if msg.text and msg.text.strip().lower() == "test":
        LOGGER.info(f"【测试回复】- 用户 {msg.from_user.first_name} (ID: {msg.from_user.id}) 发送了测试消息")
        await msg.reply("测试成功")
