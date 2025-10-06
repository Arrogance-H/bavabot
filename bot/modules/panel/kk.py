"""
kk - 纯装x
赠与账户，禁用，删除
"""
import pyrogram
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.errors import BadRequest
from bot import bot, prefixes, owner, admins, LOGGER, extra_emby_libs, config
from bot.func_helper.emby import emby
from bot.func_helper.filters import admins_on_filter
from bot.func_helper.fix_bottons import cr_kk_ikb, gog_rester_ikb
from bot.func_helper.msg_utils import deleteMessage, sendMessage, editMessage
from bot.func_helper.utils import judge_admins, cr_link_two, tem_deluser
from bot.sql_helper.sql_emby import sql_add_emby, sql_get_emby, sql_update_emby, Emby


# 管理用户
@bot.on_message(filters.command('kk', prefixes) & admins_on_filter)
async def user_info(_, msg):
    await deleteMessage(msg)
    if msg.reply_to_message is None:
        try:
            uid = int(msg.command[1])
            if not msg.sender_chat:
                if msg.from_user.id != owner and uid == owner:
                    return await sendMessage(msg,
                                             f"⭕ [{msg.from_user.first_name}](tg://user?id={msg.from_user.id})！不可以偷窥主人",
                                             timer=60)
            else:
                pass
            first = await bot.get_chat(uid)
        except (IndexError, KeyError, ValueError):
            return await sendMessage(msg, '**请先给我一个tg_id！**\n\n用法：/kk [tg_id]\n或者对某人回复kk', timer=60)
        except BadRequest:
            return await sendMessage(msg, f'{msg.command[1]} - 🎂抱歉，此id未登记bot，或者id错误', timer=60)
        except AttributeError:
            pass
        else:
            sql_add_emby(uid)
            text, keyboard = await cr_kk_ikb(uid, first.first_name)
            await sendMessage(msg, text=text, buttons=keyboard)  # protect_content=True 移除禁止复制

    else:
        uid = msg.reply_to_message.from_user.id
        try:
            if msg.from_user.id != owner and uid == owner:
                return await msg.reply(
                    f"⭕ [{msg.from_user.first_name}](tg://user?id={msg.from_user.id})！不可以偷窥主人")
        except AttributeError:
            pass

        sql_add_emby(uid)
        text, keyboard = await cr_kk_ikb(uid, msg.reply_to_message.from_user.first_name)
        await sendMessage(msg, text=text, buttons=keyboard)


# 封禁或者解除
@bot.on_callback_query(filters.regex('user_ban') & admins_on_filter)
async def kk_user_ban(_, call):
    if not judge_admins(call.from_user.id):
        return await call.answer("请不要以下犯上 ok？", show_alert=True)

    await call.answer("✅ ok")
    b = int(call.data.split("-")[1])
    if b in admins and b != call.from_user.id:
        return await editMessage(call,
                                 f"⚠️ 打咩，no，机器人不可以对bot管理员出手喔，请[自己](tg://user?id={call.from_user.id})解决",
                                 timer=60)

    first = await bot.get_chat(b)
    e = sql_get_emby(tg=b)
    if e.embyid is None:
        await editMessage(call, f'💢 ta 没有注册账户。', timer=60)
    else:
        text = f'🎯 管理员 [{call.from_user.first_name}](tg://user?id={call.from_user.id}) 对 [{first.first_name}](tg://user?id={b}) - {e.name} 的'
        if e.lv != "c":
            if await emby.emby_change_policy(emby_id=e.embyid, disable=True) is True:
                if sql_update_emby(Emby.tg == b, lv='c') is True:
                    text += f'封禁完成，此状态可在下次续期时刷新'
                    LOGGER.info(text)
                else:
                    text += '封禁失败，已执行，但数据库写入错误'
                    LOGGER.error(text)
            else:
                text += f'封禁失败，请检查emby服务器。响应错误'
                LOGGER.error(text)
        elif e.lv == "c":
            if await emby.emby_change_policy(emby_id=e.embyid):
                if sql_update_emby(Emby.tg == b, lv='b'):
                    text += '解禁完成'
                    LOGGER.info(text)
                else:
                    text += '解禁失败，服务器已执行，数据库写入错误'
                    LOGGER.error(text)
            else:
                text += '解封失败，请检查emby服务器。响应错误'
                LOGGER.error(text)
        await editMessage(call, text)
        await bot.send_message(b, text)


# 开通额外媒体库
@bot.on_callback_query(filters.regex('embyextralib_unblock') & admins_on_filter)
async def user_embyextralib_unblock(_, call):
    if not judge_admins(call.from_user.id):
        return await call.answer("请不要以下犯上 ok？", show_alert=True)
    await call.answer(f'🎬 正在为TA开启显示ing')
    tgid = int(call.data.split("-")[1])
    e = sql_get_emby(tg=tgid)
    if e.embyid is None:
        await editMessage(call, f'💢 ta 没有注册账户。', timer=60)
    embyid = e.embyid
    success, rep = await emby.user(emby_id=embyid)
    currentblock = []
    if success:
        try:
            currentblock = list(set(rep["Policy"]["BlockedMediaFolders"] + ['播放列表']))
            # 保留不同的元素
            currentblock = [x for x in currentblock if x not in extra_emby_libs] + [x for x in extra_emby_libs if
                                                                                    x not in currentblock]
        except KeyError:
            currentblock = ["播放列表"]
        re = await emby.emby_block(emby_id=embyid, stats=0, block=currentblock)
        if re is True:
            await editMessage(call, f'🌟 好的，管理员 [{call.from_user.first_name}](tg://user?id={call.from_user.id})\n'
                                    f'已开启了 [TA](tg://user?id={tgid}) 的额外媒体库权限\n{extra_emby_libs}')
        else:
            await editMessage(call,
                              f'🌧️ Error！管理员 [{call.from_user.first_name}](tg://user?id={call.from_user.id})\n操作失败请检查设置！')


# 隐藏额外媒体库
@bot.on_callback_query(filters.regex('embyextralib_block') & admins_on_filter)
async def user_embyextralib_block(_, call):
    if not judge_admins(call.from_user.id):
        return await call.answer("请不要以下犯上 ok？", show_alert=True)
    await call.answer(f'🎬 正在为TA关闭显示ing')
    tgid = int(call.data.split("-")[1])
    e = sql_get_emby(tg=tgid)
    if e.embyid is None:
        await editMessage(call, f'💢 ta 没有注册账户。', timer=60)
    embyid = e.embyid
    success, rep = await emby.user(emby_id=embyid)
    currentblock = []
    if success:
        try:
            currentblock = list(set(rep["Policy"]["BlockedMediaFolders"] + ['播放列表']))
            currentblock = list(set(currentblock + extra_emby_libs))
        except KeyError:
            currentblock = ["播放列表"] + extra_emby_libs
        re = await emby.emby_block(emby_id=embyid, stats=0, block=currentblock)
        if re is True:
            await editMessage(call, f'🌟 好的，管理员 [{call.from_user.first_name}](tg://user?id={call.from_user.id})\n'
                                    f'已关闭了 [TA](tg://user?id={tgid}) 的额外媒体库权限\n{extra_emby_libs}')
        else:
            await editMessage(call,
                              f'🌧️ Error！管理员 [{call.from_user.first_name}](tg://user?id={call.from_user.id})\n操作失败请检查设置！')


# 赠送资格
@bot.on_callback_query(filters.regex('gift') & admins_on_filter)
async def gift(_, call):
    if not judge_admins(call.from_user.id):
        return await call.answer("请不要以下犯上 ok？", show_alert=True)

    await call.answer("✅ ok")
    b = int(call.data.split("-")[1])
    if b in admins and b != call.from_user.id:
        return await editMessage(call,
                                 f"⚠️ 打咩，no，机器人不可以对bot管理员出手喔，请[自己](tg://user?id={call.from_user.id})解决")

    first = await bot.get_chat(b)
    e = sql_get_emby(tg=b)
    if e.embyid is None:
        link = await cr_link_two(tg=call.from_user.id, for_tg=b, days=config.kk_gift_days)
        await editMessage(call, f"🌟 好的，管理员 [{call.from_user.first_name}](tg://user?id={call.from_user.id})\n"
                                f'已为 [{first.first_name}](tg://user?id={b}) 赠予资格。前往bot进行下一步操作：',
                          buttons=gog_rester_ikb(link))
        LOGGER.info(f"【admin】：{call.from_user.id} 已发送 注册资格 {first.first_name} - {b} ")
    else:
        await editMessage(call, f'💢 [ta](tg://user?id={b}) 已注册账户。')


# 删除账户
@bot.on_callback_query(filters.regex('closeemby') & admins_on_filter)
async def close_emby(_, call):
    if not judge_admins(call.from_user.id):
        return await call.answer("请不要以下犯上 ok？", show_alert=True)

    await call.answer("✅ ok")
    b = int(call.data.split("-")[1])
    if b in admins and b != call.from_user.id:
        return await editMessage(call,
                                 f"⚠️ 打咩，no，机器人不可以对bot管理员出手喔，请[自己](tg://user?id={call.from_user.id})解决",
                                 timer=60)

    first = await bot.get_chat(b)
    e = sql_get_emby(tg=b)
    if e.embyid is None:
        return await editMessage(call, f'💢 ta 还没有注册账户。', timer=60)

    if await emby.emby_del(emby_id=e.embyid):
        sql_update_emby(Emby.embyid == e.embyid, embyid=None, name=None, pwd=None, pwd2=None, lv='d', cr=None, ex=None)
        tem_deluser()
        await editMessage(call,
                          f'🎯 done，管理员 [{call.from_user.first_name}](tg://user?id={call.from_user.id})\n等级：{e.lv} - [{first.first_name}](tg://user?id={b}) '
                          f'账户 {e.name} 已完成删除。')
        await bot.send_message(b,
                               f"🎯 管理员 [{call.from_user.first_name}](tg://user?id={call.from_user.id}) 已删除 您 的账户 {e.name}")
        LOGGER.info(f"【admin】：{call.from_user.id} 完成删除 {b} 的账户 {e.name}")
    else:
        await editMessage(call, f'🎯 done，等级：{e.lv} - {first.first_name}的账户 {e.name} 删除失败。')
        LOGGER.info(f"【admin】：{call.from_user.id} 对 {b} 的账户 {e.name} 删除失败 ")


@bot.on_callback_query(filters.regex('fuckoff') & admins_on_filter)
async def fuck_off_m(_, call):
    if not judge_admins(call.from_user.id):
        return await call.answer("请不要以下犯上 ok？", show_alert=True)

    await call.answer("✅ ok")
    user_id = int(call.data.split("-")[1])
    if user_id in admins and user_id != call.from_user.id:
        return await editMessage(call,
                                 f"⚠️ 打咩，no，机器人不可以对bot管理员出手喔，请[自己](tg://user?id={call.from_user.id})解决",
                                 timer=60)
    try:
        user = await bot.get_chat(user_id)
        await call.message.chat.ban_member(user_id)  # 默认退群了就删号    fix：call 没有对象chat
        await editMessage(call,
                          f'🎯 done，管理员 [{call.from_user.first_name}](tg://user?id={call.from_user.id}) 已移除 [{user.first_name}](tg://user?id={user_id})[{user_id}]')
        LOGGER.info(
            f"【admin】：{call.from_user.id} 已从群组 {call.message.chat.id} 封禁 {user.first_name} - {user.id}")
    except pyrogram.errors.ChatAdminRequired:
        await editMessage(call,
                          f"⚠️ 请赋予我踢出成员的权限 [{call.from_user.first_name}](tg://user?id={call.from_user.id})")
    except pyrogram.errors.UserAdminInvalid:
        await editMessage(call,
                          f"⚠️ 打咩，no，机器人不可以对群组管理员出手喔，请[自己](tg://user?id={call.from_user.id})解决")


# 管理员切换用户保号方式
@bot.on_callback_query(filters.regex('kk_preserve_switch') & admins_on_filter)
async def kk_preserve_switch(_, call):
    """在kk面板中切换用户保号方式"""
    if not judge_admins(call.from_user.id):
        return await call.answer("请不要以下犯上 ok？", show_alert=True)

    await call.answer("🛡️ 正在切换保号方式...")
    user_id = int(call.data.split("-")[1])
    
    # 获取用户信息
    e = sql_get_emby(tg=user_id)
    if not e or not e.embyid:
        return await editMessage(call, f'💢 用户没有账户，无法切换保号方式。', timer=60)
    
    # 检查是否为白名单或M尊享用户，这些用户无需保号
    if e.lv in ['a', 'm']:
        return await editMessage(call, f'⚠️ 该用户为白名单或M尊享用户，无需保号，无法切换保号方式。', timer=60)
    
    # 获取当前保号方式并切换
    current_mode = getattr(e, 'preserve_mode', 'active')
    new_mode = 'expire' if current_mode == 'active' else 'active'
    mode_name = {'active': '活跃保号', 'expire': '到期保号'}
    
    # 准备更新的字段
    update_fields = {'preserve_mode': new_mode}
    
    # 根据切换类型设置相应的时间参数
    switch_date = datetime.now()
    time_info = ""
    if new_mode == 'expire':
        # 活跃保号 → 到期保号：设置30天后到期
        new_expiry = switch_date + timedelta(days=30)
        update_fields['ex'] = new_expiry
        time_info = f"到期时间已重置为 {new_expiry.strftime('%Y-%m-%d %H:%M:%S')}"
    else:
        # 到期保号 → 活跃保号：活跃检测将从切换日开始计算
        time_info = f"活跃检测从 {switch_date.strftime('%Y-%m-%d')} 重新开始计算"
    
    # 更新数据库
    if sql_update_emby(Emby.tg == user_id, **update_fields):
        try:
            target_user = await bot.get_chat(user_id)
            target_name = target_user.first_name
        except:
            target_name = f"ID:{user_id}"
            
        success_text = f'🛡️ **保号方式切换成功**\n\n' \
                      f'👤 **目标用户**: [{target_name}](tg://user?id={user_id})\n' \
                      f'🔄 **变更**: {mode_name[current_mode]} → {mode_name[new_mode]}\n' \
                      f'🕐 **时间重置**: {time_info}\n' \
                      f'👮 **操作员**: [{call.from_user.first_name}](tg://user?id={call.from_user.id})'
        
        # 更新kk面板显示
        text, keyboard = await cr_kk_ikb(user_id, target_name)
        await editMessage(call, text, buttons=keyboard)
        
        # 通知目标用户
        try:
            await bot.send_message(user_id, 
                f'🛡️ **保号方式已更新**\n\n'
                f'管理员 [{call.from_user.first_name}](tg://user?id={call.from_user.id}) '
                f'已将您的保号方式从 **{mode_name[current_mode]}** 切换到 **{mode_name[new_mode]}**\n\n'
                f'🕐 {time_info}\n\n'
                f'📋 **保号方式说明：**\n'
                f'• **活跃保号**: 根据观看活跃度判断，{config.activity_check_days}天无观看将被封禁\n'
                f'• **到期保号**: 根据到期时间判断，到期后自动续期或封禁'
            )
        except:
            pass  # 如果无法发送通知给用户，继续执行
            
        LOGGER.info(f"【kk保号切换】管理员 {call.from_user.id} 将用户 {user_id} 的保号方式从 {current_mode} 改为 {new_mode}, {time_info}")
    else:
        await editMessage(call, 
            f'❌ **切换失败**\n\n数据库更新出错，请稍后重试。', 
            timer=60
        )
