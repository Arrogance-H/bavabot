"""
antichanel - 

Author:susu
Date:2023/12/30
"""
import asyncio

from pyrogram import filters

from bot import bot, prefixes, w_anti_chanel_ids, LOGGER, save_config
from bot.func_helper.filters import admins_on_filter


async def get_user_input(msg):
    await msg.delete()
    gm = msg.sender_chat.title if msg.sender_chat else f'管理员 [{msg.from_user.first_name}](tg://user?id={msg.from_user.id})'
    if msg.reply_to_message is None:
        try:
            a = msg.command[1]
        except (IndexError, KeyError, ValueError, AttributeError):
            return None, gm
    else:
        a = msg.reply_to_message.sender_chat.id
    return a, gm


@bot.on_message(filters.command('unban_chanel', prefixes) & admins_on_filter)
async def un_fukk_pitao(_, msg):
    a, gm = await get_user_input(msg)
    if not a:
        return await msg.reply('使用 /unban_chanel 回复 或 /unban_chanel + [id/用户名] 为皮套解禁')
    # print(a)
    await bot.unban_chat_member(msg.chat.id, a)
    LOGGER.info(f'【AntiChanel】- {gm} 解禁皮套 ——> {a} ')


@bot.on_message(filters.command('white_chanel', prefixes) & admins_on_filter)
async def allow_pitao(_, msg):
    a, gm = await get_user_input(msg)
    if not a:
        return await msg.reply('使用 /white_chanel 回复 或 /white_chanel + [id/用户名] 加入皮套人白名单')
    if a not in w_anti_chanel_ids:
        w_anti_chanel_ids.append(a)
        save_config()
    await asyncio.gather(msg.reply(f'🎁 {gm} 已为 {a} 添加皮套人白名单'), bot.unban_chat_member(msg.chat.id, a))
    LOGGER.info(f'【AntiChanel】- {gm} 豁免皮套 ——> {a}')


@bot.on_message(filters.command('rev_white_chanel', prefixes) & admins_on_filter)
async def remove_pitao(_, msg):
    a, gm = await get_user_input(msg)
    if not a:
        return await msg.reply('使用 /rev_white_chanel 回复 或 /rev_white_chanel + [id/用户名] 移除皮套人白名单')
    if a in w_anti_chanel_ids:
        w_anti_chanel_ids.remove(a)
        save_config()
    await asyncio.gather(msg.reply(f'🕶️ {gm} 已为 {a} 移除皮套人白名单'), bot.ban_chat_member(msg.chat.id, a))
    LOGGER.info(f'【AntiChanel】- {gm} 封禁皮套 ——> {a}')


custom_message_filter = filters.create(
    lambda _, __, message: False if message.forward_from_chat or message.from_user else True)
custom_chat_filter = filters.create(
    lambda _, __,
           message: True if message.sender_chat.id != message.chat.id and message.sender_chat.id not in w_anti_chanel_ids else False)


# message.sender_chat and

# 直接拉黑皮套
@bot.on_message(custom_message_filter & custom_chat_filter & filters.group)
async def fuxx_pitao(_, msg):
    # print(msg)
    try:
        await asyncio.gather(bot.ban_chat_member(msg.chat.id, msg.sender_chat.id),
                             msg.reply(f'🎯 自动狙杀皮套人！{msg.sender_chat.title} - `{msg.sender_chat.id}`'))
        LOGGER.info(f'【AntiChanel】- {msg.sender_chat.title} - {msg.sender_chat.id} 被封禁')
    except:
        pass
