"""
启动面板start命令 返回面ban

命令说明:
+ myinfo 个人数据查询命令 - 用户可以查看自己的详细信息
  - 显示Telegram用户信息（ID、用户名）
  - 显示Emby账户状态（账户名、等级、到期时间）
  - 显示用户积分和权限信息
  - 显示播放统计（最近活动、30天播放时长）
  - 管理员查看时提供额外的管理操作按钮
  
+ count  服务器媒体数统计命令
  - 显示Emby服务器上的媒体库统计信息

myinfo命令工作原理:
1. 接收用户命令 -> my_info()函数处理
2. 权限验证 -> 确保用户在群组中且有权限
3. 数据获取 -> cr_kk_ikb()构建信息文本和按钮
4. 信息查询 -> members_info()从数据库获取用户信息
5. 外部查询 -> 从Emby服务器获取播放统计
6. 格式化显示 -> 生成用户友好的信息文本
7. 发送消息 -> 60秒后自动删除保护隐私
"""
import asyncio
from pyrogram import filters

from bot.func_helper.emby import Embyservice
from bot.func_helper.utils import judge_admins, members_info, open_check
from bot.modules.commands.exchange import rgs_code
from bot.sql_helper.sql_emby import sql_add_emby
from bot.func_helper.filters import user_in_group_filter, user_in_group_on_filter
from bot.func_helper.msg_utils import deleteMessage, sendMessage, sendPhoto, callAnswer, editMessage
from bot.func_helper.fix_bottons import group_f, judge_start_ikb, judge_group_ikb, cr_kk_ikb
from bot.modules.extra import user_cha_ip
from bot import bot, prefixes, group, bot_photo, ranks, sakura_b


# 反命令提示
@bot.on_message((filters.command('start', prefixes) | filters.command('count', prefixes)) & filters.chat(group))
async def ui_g_command(_, msg):
    await asyncio.gather(deleteMessage(msg),
                         sendMessage(msg,
                                     f"🤖 亲爱的 [{msg.from_user.first_name}](tg://user?id={msg.from_user.id}) 这是一条私聊命令",
                                     buttons=group_f, timer=60))


# 查看自己的信息
# myinfo命令的入口点 - 用户信息查询命令
@bot.on_message(filters.command('myinfo', prefixes) & user_in_group_on_filter)
async def my_info(_, msg):
    """
    myinfo命令处理函数 - 获取并显示用户个人信息
    
    工作流程：
    1. 删除用户发送的命令消息（保持聊天整洁）
    2. 检查消息是否来自频道（频道消息不处理）
    3. 调用cr_kk_ikb函数获取用户详细信息和操作按钮
    4. 发送格式化的用户信息，60秒后自动删除
    
    参数:
    - _: Pyrogram客户端实例（未使用）
    - msg: 用户发送的消息对象，包含用户ID和其他信息
    """
    # 删除用户的原始命令消息，保持群聊整洁
    await msg.delete()
    
    # 如果消息来自频道而非个人用户，直接返回不处理
    if msg.sender_chat:
        return
    
    # 核心信息获取：调用cr_kk_ikb函数构建用户信息文本和键盘按钮
    # uid: 用户的Telegram ID，用于数据库查询
    # first: 用户的名字，用于显示
    text, keyboard = await cr_kk_ikb(uid=msg.from_user.id, first=msg.from_user.first_name)
    
    # 发送格式化的用户信息，设置60秒自动删除保护隐私
    await sendMessage(msg, text, timer=60)


@bot.on_message(filters.command('count', prefixes) & user_in_group_on_filter & filters.private)
async def count_info(_, msg):
    await deleteMessage(msg)
    text = await Embyservice.get_medias_count()
    await sendMessage(msg, text, timer=60)


# 私聊开启面板
@bot.on_message(filters.command('start', prefixes) & filters.private)
async def p_start(_, msg):
    if not await user_in_group_filter(_, msg):
        return await asyncio.gather(deleteMessage(msg),
                                    sendMessage(msg,
                                                '💢 拜托啦！请先点击下面加入我们的群组和频道，然后再 /start 一下好吗？\n\n'
                                                '⁉️ ps：如果您已在群组中且收到此消息，请联系管理员解除您的权限限制，因为被限制用户无法使用本bot。',
                                                buttons=judge_group_ikb))
    try:
        u = msg.command[1].split('-')[0]
        if u == 'userip':
            name = msg.command[1].split('-')[1]
            if judge_admins(msg.from_user.id):
                return await user_cha_ip(_, msg, name)
            else:
                return await sendMessage(msg, '💢 你不是管理员，无法使用此命令')
        if u in f'{ranks.logo}' or u == str(msg.from_user.id):
            await asyncio.gather(msg.delete(), rgs_code(_, msg, register_code=msg.command[1]))
        else:
            await asyncio.gather(sendMessage(msg, '🤺 你也想和bot击剑吗 ?'), msg.delete())
    except (IndexError, TypeError):
        data = await members_info(tg=msg.from_user.id)
        is_admin = judge_admins(msg.from_user.id)
        if not data:
            sql_add_emby(msg.from_user.id)
            await asyncio.gather(deleteMessage(msg),
                                 sendPhoto(msg, bot_photo,
                                           f"**BAVA Hi~**\n\n"
                                           f"🎉欢迎您 [{msg.from_user.first_name}](tg://user?id={msg.from_user.id}) \n\n"
                                           f"初次使用，录入数据库完成。\n"
                                           f"请点击 /start 重新召唤面板"))
            return
        name, lv, ex, us, embyid, pwd2 = data
        stat, all_user, tem, timing = await open_check()
        text = f"▎__欢迎进入用户面板！{msg.from_user.first_name}__\n\n" \
               f"**· 🆔 用户のID** | `{msg.from_user.id}`\n" \
               f"**· 📊 当前状态** | {lv}\n" \
               f"**· 🍒 积分{sakura_b}** | {us}\n" \
               f"**· ®️ 注册状态** | {stat}\n" \
               f"**· 🎫 总注册限制** | {all_user}\n" \
               f"**· 🎟️ 可注册席位** | {all_user - tem}\n"
        if not embyid:
            await asyncio.gather(deleteMessage(msg),
                                 sendPhoto(msg, bot_photo, caption=text, buttons=judge_start_ikb(is_admin, False)))
        else:
            await asyncio.gather(deleteMessage(msg),
                                 sendPhoto(msg, bot_photo,
                                           f"**BAVA Hi~**\n\n🎉欢迎您 [{msg.from_user.first_name}](tg://user?id={msg.from_user.id})",
                                           buttons=judge_start_ikb(is_admin, True)))


# 返回面板
@bot.on_callback_query(filters.regex('back_start'))
async def b_start(_, call):
    if await user_in_group_filter(_, call):
        is_admin = judge_admins(call.from_user.id)
        await asyncio.gather(callAnswer(call, "⭐ 返回start"),
                             editMessage(call,
                                         text=f"**BAVA Hi~**\n\n🎉欢迎您 [{call.from_user.first_name}](tg://user?id={call.from_user.id})",
                                         buttons=judge_start_ikb(is_admin, account=True)))
    elif not await user_in_group_filter(_, call):
        await asyncio.gather(callAnswer(call, "⭐ 返回start"),
                             editMessage(call, text='💢 拜托啦！请先点击下面加入我们的群组和频道，然后再 /start 一下好吗？\n\n'
                                                    '⁉️ ps：如果您已在群组中且收到此消息，请联系管理员解除您的权限限制，因为被限制用户无法使用本bot。',
                                         buttons=judge_group_ikb))


@bot.on_callback_query(filters.regex('store_all'))
async def store_alls(_, call):
    if not await user_in_group_filter(_, call):
        await asyncio.gather(callAnswer(call, "⭐ 返回start"),
                             deleteMessage(call), sendPhoto(call, bot_photo,
                                                            '💢 拜托啦！请先点击下面加入我们的群组和频道，然后再 /start 一下好吗？',
                                                            judge_group_ikb))
    elif await user_in_group_filter(_, call):
        await callAnswer(call, '⭕ 正在编辑', True)
