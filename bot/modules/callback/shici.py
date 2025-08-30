import asyncio
import random
from pyrogram import filters

from bot import bot, _open
from bot.func_helper.filters import user_in_group_on_filter
from bot.func_helper.msg_utils import callAnswer, sendMessage, deleteMessage, editMessage
from bot.func_helper.utils import get_bot_shici
from bot.func_helper.fix_bottons import shici_button, checkin_button


@bot.on_callback_query(filters.regex('shici_game') & user_in_group_on_filter)
async def start_shici_game(_, call):
    """开始诗词填空游戏"""
    try:
        await callAnswer(call, '🔍 正在获取诗词...')
        
        result = await get_bot_shici()
        if not result:
            await callAnswer(call, '❌ 获取诗词失败，请稍后再试', True)
            return
        
        original_poem, char_options, masked_poem, source = result
        
        if not char_options:
            # 如果没有选项字符，显示完整诗词
            text = f'📖 **今日诗词**\n\n{original_poem}\n\n—— {source}'
            await editMessage(call, text, checkin_button)
            return
        
        # 创建诗词填空游戏
        text = f'📝 **诗词填空游戏**\n\n{masked_poem}\n\n—— {source}\n\n请选择正确的字符填入空白处：'
        
        # 创建字符选择按钮
        keyboard = shici_button(char_options)
        # 添加提示和返回按钮
        keyboard.inline_keyboard.append([('💡 查看答案', f'shici_answer-{original_poem}'), ('🔙 返回', 'back_start')])
        
        await editMessage(call, text, keyboard)
        
    except Exception as e:
        print(f"Poetry game error: {e}")
        await callAnswer(call, '❌ 启动诗词游戏失败', True)


@bot.on_callback_query(filters.regex(r'shici-(.+)') & user_in_group_on_filter)
async def handle_shici_choice(_, call):
    """处理诗词选择"""
    try:
        char = call.data.split('-', 1)[1]
        
        # 这里可以添加更复杂的逻辑来验证选择是否正确
        # 现在简单回应选择
        await callAnswer(call, f'您选择了：{char}')
        
        # 可以在这里添加积分奖励逻辑
        text = f'✨ **选择完成**\n\n您选择了字符：**{char}**\n\n感谢参与诗词游戏！'
        await editMessage(call, text, checkin_button)
        
    except Exception as e:
        print(f"Poetry choice error: {e}")
        await callAnswer(call, '❌ 处理选择失败', True)


@bot.on_callback_query(filters.regex(r'shici_answer-(.+)') & user_in_group_on_filter)
async def show_shici_answer(_, call):
    """显示诗词答案"""
    try:
        original_poem = call.data.split('-', 1)[1]
        
        text = f'💡 **诗词答案**\n\n{original_poem}\n\n希望您喜欢这首诗词！'
        await editMessage(call, text, checkin_button)
        
    except Exception as e:
        print(f"Show answer error: {e}")
        await callAnswer(call, '❌ 显示答案失败', True)