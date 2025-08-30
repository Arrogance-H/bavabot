"""
诗词功能命令
Poetry feature command
"""
import asyncio
from pyrogram import filters

from bot import bot, prefixes
from bot.func_helper.filters import user_in_group_on_filter
from bot.func_helper.msg_utils import deleteMessage, sendMessage
from bot.func_helper.utils import get_bot_shici
from bot.func_helper.fix_bottons import shici_button, checkin_button


@bot.on_message(filters.command('shici', prefixes) & user_in_group_on_filter)
async def shici_command(_, msg):
    """诗词填空游戏命令"""
    try:
        await deleteMessage(msg)
        
        # 发送正在获取诗词的提示
        loading_msg = await msg.reply('🔍 正在获取诗词...')
        
        result = await get_bot_shici()
        if not result:
            await loading_msg.edit('❌ 获取诗词失败，请稍后再试')
            return
        
        original_poem, char_options, masked_poem, source = result
        
        if not char_options:
            # 如果没有选项字符，显示完整诗词
            text = f'📖 **今日诗词**\n\n{original_poem}\n\n—— {source}'
            await loading_msg.edit(text, reply_markup=checkin_button)
            return
        
        # 创建诗词填空游戏
        text = f'📝 **诗词填空游戏**\n\n{masked_poem}\n\n—— {source}\n\n请选择正确的字符填入空白处：'
        
        # 创建字符选择按钮
        keyboard = shici_button(char_options)
        # 添加提示和返回按钮
        from pyromod.helpers import ikb
        additional_buttons = ikb([[('💡 查看答案', f'shici_answer-{original_poem[:20]}'), ('🔙 返回', 'back_start')]])
        keyboard.inline_keyboard.extend(additional_buttons.inline_keyboard)
        
        await loading_msg.edit(text, reply_markup=keyboard)
        
    except Exception as e:
        print(f"Poetry command error: {e}")
        await msg.reply('❌ 启动诗词游戏失败')