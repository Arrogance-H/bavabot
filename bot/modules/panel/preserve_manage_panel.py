"""
保号管理独立面板
独立的保号方式管理功能，从admin_panel分离出来
主要功能：保号统计、查询用户、修改保号方式、重置切换权限
"""
import asyncio
from datetime import datetime

from pyrogram import filters

from bot import bot, _open, save_config, bot_photo, LOGGER, bot_name, admins, owner, config
from bot.func_helper.filters import admins_on_filter
from bot.sql_helper import Session
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby
from bot.func_helper.fix_bottons import preserve_manage_ikb, preserve_back_ikb, preserve_retry_query_ikb, \
    preserve_retry_modify_ikb, preserve_retry_reset_ikb
from bot.func_helper.msg_utils import callAnswer, editMessage, sendPhoto, callListen, deleteMessage, sendMessage


@bot.on_callback_query(filters.regex('^preserve_manage$') & admins_on_filter)
async def preserve_manage(_, call):
    """管理员保号方式管理面板"""
    await callAnswer(call, '🛡️ 保号管理')
    
    # Get activity check days with fallback
    activity_days = getattr(config, 'activity_check_days', 21)
    
    text = f'🛡️ **用户保号方式管理**\n\n'
    text += f'**功能说明：**\n'
    text += f'• 查看用户保号方式统计\n'
    text += f'• 修改指定用户的保号方式\n'
    text += f'• 重置用户的切换次数\n\n'
    text += f'**保号方式类型：**\n'
    text += f'• **活跃保号**: 根据观看活跃度判断，{activity_days}天无观看将被封禁\n'
    text += f'• **到期保号**: 根据到期时间判断，到期后自动续期或封禁\n'
    
    await editMessage(call, text, preserve_manage_ikb())
    LOGGER.info(f"【保号管理】管理员 {call.from_user.id} 进入保号管理面板")


@bot.on_callback_query(filters.regex('^preserve_stats$') & admins_on_filter)
async def preserve_stats(_, call):
    """显示保号方式统计"""
    await callAnswer(call, '📊 保号统计')
    
    # 查询所有用户的保号统计
    with Session() as session:
        try:
            total_users = session.query(Emby).filter(Emby.embyid.isnot(None)).count()
            active_users = session.query(Emby).filter(
                Emby.embyid.isnot(None), 
                Emby.preserve_mode == 'active'
            ).count()
            expire_users = session.query(Emby).filter(
                Emby.embyid.isnot(None), 
                Emby.preserve_mode == 'expire'
            ).count()
            switched_users = session.query(Emby).filter(
                Emby.embyid.isnot(None), 
                Emby.preserve_mode_changed >= 1
            ).count()
            
            if total_users == 0:
                text = f'📊 **保号方式统计报告**\n\n'
                text += f'👥 **总用户数**: 0\n\n'
                text += f'ℹ️ 当前数据库中没有用户数据\n\n'
                text += f'📅 **统计时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
            else:
                text = f'📊 **保号方式统计报告**\n\n'
                text += f'👥 **总用户数**: {total_users}\n\n'
                text += f'🛡️ **活跃保号**: {active_users} 人 ({active_users/total_users*100:.1f}%)\n'
                text += f'⏰ **到期保号**: {expire_users} 人 ({expire_users/total_users*100:.1f}%)\n'
                text += f'🔄 **已切换过**: {switched_users} 人 ({switched_users/total_users*100:.1f}%)\n\n'
                text += f'📅 **统计时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
                
        except Exception as e:
            LOGGER.error(f"【保号统计】数据库查询错误: {str(e)}")
            text = f'❌ **统计失败**: 数据库查询出错\n\n{str(e)}'
    
    await editMessage(call, text, preserve_back_ikb())
    LOGGER.info(f"【保号统计】管理员 {call.from_user.id} 查看保号统计")


@bot.on_callback_query(filters.regex('^preserve_user_query$') & admins_on_filter)
async def preserve_user_query(_, call):
    """查询指定用户的保号方式"""
    await callAnswer(call, '🔍 查询用户')
    
    send = await editMessage(call,
        "🔍 **查询用户保号信息**\n\n"
        "请在 120s 内发送要查询的用户 TG ID 或用户名\n"
        "• 支持 @username 或直接输入用户ID\n"
        "• 取消操作请发送 /cancel",
        preserve_back_ikb()
    )
    
    if send is False:
        return
    
    txt = await callListen(call, 120, preserve_back_ikb())
    
    if txt is False:
        return
    elif txt.text == "/cancel":
        await txt.delete()
        return await preserve_manage(_, call)
    
    await txt.delete()
    # 处理用户输入
    user_input = txt.text.strip()
    if user_input.startswith('@'):
        user_input = user_input[1:]  # 移除@符号
    
    # 尝试按用户名或ID查询
    e = None
    if user_input.isdigit():
        # 数字，按TG ID查询
        e = sql_get_emby(tg=int(user_input))
    else:
        # 非数字，按用户名查询 (需要实现username查询)
        with Session() as session:
            e = session.query(Emby).filter(Emby.name.ilike(f'%{user_input}%')).first()
    
    if not e:
        await editMessage(call,
            f"❌ **未找到用户**: {user_input}\n\n"
            f"请检查用户ID或用户名是否正确",
            preserve_retry_query_ikb()
        )
        return
    
    # 获取保号信息
    preserve_mode = getattr(e, 'preserve_mode', 'expire')
    preserve_mode_changed = getattr(e, 'preserve_mode_changed', 0)
    
    mode_name = {
        'active': '活跃保号',
        'expire': '到期保号'
    }
    
    text = f'🔍 **用户保号信息查询结果**\n\n'
    text += f'👤 **用户名**: {e.name}\n'
    text += f'🆔 **TG ID**: {e.tg}\n'
    text += f'📧 **Emby ID**: {e.embyid or "未设置"}\n'
    text += f'🛡️ **保号方式**: {mode_name.get(preserve_mode, "未知")}\n'
    text += f'🔄 **切换状态**: {"已切换过" if preserve_mode_changed >= 1 else "可切换"}\n'
    text += f'📅 **到期时间**: {e.ex or "未设置"}\n'
    text += f'🎭 **用户等级**: {e.lv or "未设置"}\n\n'
    text += f'📝 **备注**: 用户当前保号方式为 {mode_name.get(preserve_mode, "未知")}\n'
    text += f'查询时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
    
    await editMessage(call, text, preserve_back_ikb())
    LOGGER.info(f"【保号查询】查询成功: 用户 {e.tg}, 保号方式 {preserve_mode}")


@bot.on_callback_query(filters.regex('^preserve_user_modify$') & admins_on_filter)
async def preserve_user_modify(_, call):
    """修改用户保号方式"""
    await callAnswer(call, '⚙️ 修改保号方式')
    
    send = await editMessage(call,
        "⚙️ **修改用户保号方式**\n\n"
        "请在 120s 内发送要修改的用户信息，格式为：\n"
        "`用户ID 新保号方式`\n\n"
        "**保号方式选项：**\n"
        "• `active` - 活跃保号\n"
        "• `expire` - 到期保号\n\n"
        "**示例：** `123456789 active`\n"
        "取消操作请发送 /cancel",
        preserve_back_ikb()
    )
    
    if send is False:
        return
    
    txt = await callListen(call, 120, preserve_back_ikb())
    
    if txt is False:
        return
    elif txt.text == "/cancel":
        await txt.delete()
        return await preserve_manage(_, call)
    
    await txt.delete()
    # 解析输入
    parts = txt.text.strip().split()
    if len(parts) != 2:
        await editMessage(call,
            f"❌ **输入格式错误**\n\n"
            f"请使用格式: `用户ID 保号方式`\n"
            f"您输入的是: `{txt.text}`",
            preserve_retry_modify_ikb()
        )
        return
    
    user_id, new_mode = parts
    
    if not user_id.isdigit():
        await editMessage(call,
            f"❌ **用户ID格式错误**\n\n"
            f"用户ID必须是数字\n"
            f"您输入的是: `{user_id}`",
            preserve_retry_modify_ikb()
        )
        return
    
    if new_mode not in ['active', 'expire']:
        await editMessage(call,
            f"❌ **保号方式错误**\n\n"
            f"支持的保号方式: active, expire\n"
            f"您输入的是: `{new_mode}`",
            preserve_retry_modify_ikb()
        )
        return
    
    # 查询用户
    e = sql_get_emby(tg=int(user_id))
    if not e:
        await editMessage(call,
            f"❌ **用户不存在**\n\n"
            f"未找到 TG ID 为 {user_id} 的用户",
            preserve_retry_modify_ikb()
        )
        return
    
    # 更新保号方式
    old_mode = getattr(e, 'preserve_mode', 'active')
    mode_name = {'active': '活跃保号', 'expire': '到期保号'}
    
    if sql_update_emby(Emby.tg == e.tg, preserve_mode=new_mode):
        text = f'✅ **保号方式修改成功**\n\n'
        text += f'👤 **用户**: {e.name} ({e.tg})\n'
        text += f'🔄 **修改内容**: {mode_name.get(old_mode, "未知")} → {mode_name.get(new_mode, "未知")}\n'
        text += f'👮‍♂️ **操作管理员**: {call.from_user.first_name}\n'
        text += f'📅 **修改时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        
        await editMessage(call, text, preserve_back_ikb())
        LOGGER.info(f"【保号修改】管理员 {call.from_user.id} 成功修改用户 {user_id} 保号方式: {old_mode} → {new_mode}")
    else:
        await editMessage(call,
            f"❌ **修改失败**\n\n数据库更新操作失败，请稍后重试",
            preserve_retry_modify_ikb()
        )


@bot.on_callback_query(filters.regex('^preserve_reset_switch$') & admins_on_filter)
async def preserve_reset_switch(_, call):
    """重置用户切换权限"""
    await callAnswer(call, '🔄 重置切换权限')
    
    send = await editMessage(call,
        "🔄 **重置用户切换权限**\n\n"
        "请在 120s 内发送要重置的用户 TG ID\n"
        "• 重置后用户可以重新切换保号方式\n"
        "• 输入用户的 TG ID（纯数字）\n\n"
        "**示例：** `123456789`\n"
        "取消操作请发送 /cancel",
        preserve_back_ikb()
    )
    
    if send is False:
        return
    
    txt = await callListen(call, 120, preserve_back_ikb())
    
    if txt is False:
        return
    elif txt.text == "/cancel":
        await txt.delete()
        return await preserve_manage(_, call)
    
    await txt.delete()
    user_id = txt.text.strip()
    
    if not user_id.isdigit():
        await editMessage(call,
            f"❌ **输入格式错误**\n\n"
            f"请输入纯数字的 TG ID\n"
            f"您输入的是: `{user_id}`",
            preserve_retry_reset_ikb()
        )
        return
    
    # 查询用户
    e = sql_get_emby(tg=int(user_id))
    if not e:
        await editMessage(call,
            f"❌ **用户不存在**\n\n"
            f"未找到 TG ID 为 {user_id} 的用户",
            preserve_retry_reset_ikb()
        )
        return
    
    # 重置切换权限
    current_changed = getattr(e, 'preserve_mode_changed', 0)
    
    if sql_update_emby(Emby.tg == e.tg, preserve_mode_changed=0):
        text = f'✅ **切换权限重置成功**\n\n'
        text += f'👤 **用户**: {e.name} ({e.tg})\n'
        text += f'🔄 **重置内容**: 切换次数 {current_changed} → 0\n'
        text += f'💡 **效果**: 用户现在可以重新切换保号方式\n'
        text += f'👮‍♂️ **操作管理员**: {call.from_user.first_name}\n'
        text += f'📅 **重置时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        
        await editMessage(call, text, preserve_back_ikb())
        LOGGER.info(f"【保号重置】管理员 {call.from_user.id} 成功重置用户 {user_id} 切换权限")
    else:
        await editMessage(call,
            f"❌ **重置失败**\n\n数据库更新操作失败，请稍后重试",
            preserve_retry_reset_ikb()
        )
