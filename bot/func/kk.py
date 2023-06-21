"""
kk - 纯装x
赠与账户，禁用，删除
"""

import logging
from datetime import datetime

import asyncio

from pykeyboard import InlineKeyboard, InlineButton
from pyrogram import filters
from pyrogram.errors import BadRequest
from pyromod.helpers import ikb

from _mysql import sqlhelper
from bot.reply import emby, query
from config import bot, prefixes, judge_user, send_msg_delete, photo, BOT_NAME


# 管理用户
@bot.on_message(filters.command('kk', prefixes))
async def user_info(_, msg):
    try:
        await msg.delete()
    except BadRequest:
        await msg.reply("请先给我删除消息的权限~")
    a = judge_user(msg.from_user.id)
    if a == 1:
        pass
    if a == 3:
        # print(msg)
        if msg.reply_to_message is None:
            try:
                uid = msg.text.split()[1]
                first = await bot.get_chat(uid)
            except (IndexError, KeyError, BadRequest):
                send = await msg.reply('**请先给我一个正确的id！**\n\n用法：/kk [id]\n或者对某人回复kk')
                asyncio.create_task(send_msg_delete(send.chat.id, send.id))
            else:
                text = ''
                ban = ''
                keyboard = InlineKeyboard()
                try:
                    name, lv, ex, us = await query.members_info(uid)
                    if lv == "已禁用":
                        ban += "🌟 解除禁用"
                    else:
                        ban += '💢 禁用账户'
                    text += f"**· 🍉 TG名称** | [{first.first_name}](tg://user?id={uid})\n**· 🍒 TG-ID** | `{uid}`\n" \
                            f"**· 🍓 当前状态** | {lv} \n" \
                            f"**· 🌸 积分数量** | {us}\n**· 💠 账号名称** | {name}\n**· 🚨 到期时间** | **{ex}**"
                    if ex != "无账户信息":
                        dlt = (ex - datetime.now()).days
                        text += f"\n**· 📅 剩余天数** | **{dlt}** 天"
                    keyboard.row(
                        InlineButton(' ✨ 赠送资格', f'gift-{uid}'),
                        InlineButton(ban, f'user_ban-{uid}')
                    )
                    keyboard.row(InlineButton('❌ - 删除账户', f'closeemby-{uid}'))
                except TypeError:
                    text += f'**· 🆔 TG** ：[{first.first_name}](tg://user?id={uid})\n数据库中没有此ID。ta 还没有私聊过我。'
                    keyboard.row(InlineButton('❌ - 删除消息', f'closeit'))
                finally:
                    send = await bot.send_photo(msg.chat.id, photo=photo, caption=text,
                                                reply_markup=keyboard)  # protect_content=True 移除禁止复制
                    asyncio.create_task(send_msg_delete(send.chat.id, send.id))
        else:
            uid = msg.reply_to_message.from_user.id
            first = await bot.get_chat(uid)
            text = ''
            ban = ''
            keyboard = InlineKeyboard()
            try:
                name, lv, ex, us = await query.members_info(uid)
                if lv == "已禁用":
                    ban += "🌟 解除禁用"
                else:
                    ban += '💢 禁用账户'
                text += f"**· 🍉 TG名称** | [{first.first_name}](tg://user?id={uid})\n**· 🍒 TG-ID** | `{uid}`\n" \
                        f"**· 🍓 当前状态** | {lv} \n" \
                        f"**· 🌸 积分数量** | {us}\n**· 💠 账号名称** | {name}\n**· 🚨 到期时间** | **{ex}**"
                if ex != "无账户信息":
                    dlt = (ex - datetime.now()).days
                    text += f"\n**· 📅 剩余天数** | **{dlt}** 天"
                keyboard.row(
                    InlineButton(' ✨ 赠送资格', f'gift-{uid}'),
                    InlineButton(ban, f'user_ban-{uid}')
                )
                keyboard.row(InlineButton('❌ - 删除账户', f'closeemby-{uid}'))
            except TypeError:
                text += f'**· 🆔 TG** ：[{first.first_name}](tg://user?id={uid})\n数据库中没有此ID。ta 还没有私聊过我。'
                keyboard.row(InlineButton('❌ - 删除消息', f'closeit'))
            finally:
                send = await bot.send_message(msg.chat.id, text,
                                              reply_to_message_id=msg.reply_to_message.id, reply_markup=keyboard)
                # protect_content=True,移除禁止复制
                asyncio.create_task(send_msg_delete(send.chat.id, send.id))


# 封禁或者解除
@bot.on_callback_query(filters.regex('user_ban'))
async def gift(_, call):
    a = judge_user(call.from_user.id)
    if a == 1:
        await call.answer("请不要以下犯上 ok？", show_alert=True)
    if a == 3:
        b = int(call.data.split("-")[1])
        first = await bot.get_chat(b)
        embyid, name, lv = sqlhelper.select_one("select embyid,name,lv from emby where tg = %s", b)
        if embyid is None:
            send = await call.message.reply(f'💢 ta 没有注册账户。')
            asyncio.create_task(send_msg_delete(send.chat.id, send.id))
        else:
            if lv != "c":
                await emby.ban_user(embyid, 0)
                sqlhelper.update_one("update emby set lv=%s where tg=%s", ['c', b])
                await call.message.reply(
                    f'🎯 管理员 {call.from_user.first_name} 已禁用[{first.first_name}](tg://user?id={b}) 账户 {name}\n'
                    f'此状态可在下次续期时刷新')
                await bot.send_message(b,
                                       f"🎯 管理员 {call.from_user.first_name} 已禁用 您的账户 {name}\n此状态可在下次续期时刷新")
                logging.info(f"【admin】：管理员 {call.from_user.id} 完成禁用 {b} 账户 {name}")
            elif lv == "c":
                await emby.ban_user(embyid, 1)
                sqlhelper.update_one("update emby set lv=%s where tg=%s", ['b', b])
                await call.message.reply(
                    f'🎯 管理员 {call.from_user.first_name} 已解除禁用[{first.first_name}](tg://user?id={b}) 账户 {name}')
                await bot.send_message(b,
                                       f"🎯 管理员 {call.from_user.first_name} 已解除禁用 您的账户 {name}")
                logging.info(f"【admin】：管理员 {call.from_user.id} 解除禁用 {b} 账户 {name}")


# 赠送资格
@bot.on_callback_query(filters.regex('gift'))
async def gift(_, call):
    a = judge_user(call.from_user.id)
    if a == 1:
        await call.answer("请不要以下犯上 ok？", show_alert=True)
    if a == 3:
        b = int(call.data.split("-")[1])
        first = await bot.get_chat(b)
        # try:
        embyid = sqlhelper.select_one("select embyid from emby where tg = %s", b)[0]
        if embyid is None:
            await emby.start_user(b, 30)
            await bot.send_message(call.message.chat.id,
                                   f"🌟 好的，管理员 {call.from_user.first_name}"
                                   f'已为 [{first.first_name}](tg://user?id={b}) 赠予资格。前往bot进行下一步操作：',
                                   reply_markup=ikb([[("(👉ﾟヮﾟ)👉 点这里", f"t.me/{BOT_NAME}", "url")]]))
            await bot.send_photo(b, photo, f"💫 亲爱的 {first.first_name} \n💘请查收：",
                                 reply_markup=ikb([[("💌 - 点击注册", "create")], [('❌ - 关闭', 'closeit')]]))
            logging.info(f"【admin】：{call.from_user.id} 已发送 注册资格 {first.first_name} - {b} ")
        else:
            send = await call.message.reply(f'💢 ta 已注册账户。',
                                            reply_markup=ikb([[('❌ - 已开启自动删除', 'closeit')]]))
            asyncio.create_task(send_msg_delete(send.chat.id, send.id))


# 删除账户
@bot.on_callback_query(filters.regex('closeemby'))
async def close_emby(_, call):
    a = judge_user(call.from_user.id)
    if a == 1:
        await call.answer("请不要以下犯上 ok？", show_alert=True)
    if a == 3:
        b = int(call.data.split("-")[1])
        first = await bot.get_chat(b)
        embyid, name, lv = sqlhelper.select_one("select embyid,name,lv from emby where tg = %s", b)
        if embyid is None:
            send = await call.message.reply(f'💢 ta 还没有注册账户。')
            asyncio.create_task(send_msg_delete(send.chat.id, send.id))
        else:
            if await emby.emby_del(embyid) is True:
                await call.message.reply(
                    f'🎯 done，管理员 {call.from_user.first_name}\n等级：{lv} - [{first.first_name}](tg://user?id={b}) '
                    f'账户 {name} 已完成删除。')
                await bot.send_message(b,
                                       f"🎯 管理员 {call.from_user.first_name} 已删除 您 的账户 {name}")
                logging.info(f"【admin】：{call.from_user.id} 完成删除 {b} 的账户 {name}")
            else:
                await call.message.reply(f'🎯 done，等级：{lv} - {first.first_name}的账户 {name} 删除失败。')
                logging.info(f"【admin】：{call.from_user.id} 对 {b} 的账户 {name} 删除失败 ")
