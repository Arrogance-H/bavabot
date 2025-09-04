import asyncio
import os
from datetime import datetime

import requests
from pyrogram import filters
from pyrogram.types import Message

from bot import bot, sakura_b, schedall, save_config, prefixes, _open, owner, LOGGER, auto_update, group
from bot.func_helper.filters import admins_on_filter, user_in_group_on_filter
from bot.func_helper.fix_bottons import sched_buttons, plays_list_button
from bot.func_helper.msg_utils import callAnswer, editMessage, deleteMessage
from bot.func_helper.scheduler import scheduler
from bot.scheduler import *


# 初始化命令 开机检查重启
loop = asyncio.get_event_loop()
loop.call_later(5, lambda: loop.create_task(BotCommands.set_commands(client=bot)))
loop.call_later(5, lambda: loop.create_task(check_restart()))

# 启动定时任务
auto_backup_db = DbBackupUtils.auto_backup_db
user_plays_rank = Uplaysinfo.user_plays_rank
check_low_activity = Uplaysinfo.check_low_activity

# 错误通知函数
async def send_task_error_notification(task_name: str, error_msg: str, manual_command: str = None):
    """发送定时任务错误通知给管理员"""
    try:
        error_text = f'🚨 **定时任务执行失败**\n\n'
        error_text += f'**任务名称**: {task_name}\n'
        error_text += f'**错误信息**: {error_msg}\n'
        error_text += f'**发生时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n'
        
        if manual_command:
            error_text += f'**手动执行命令**: `{manual_command}`\n'
            error_text += f'管理员可以使用上述命令手动执行结算。\n\n'
        
        error_text += f'请检查系统状态并及时处理。\n'
        error_text += f'@管理员 请注意处理'
        
        await bot.send_message(chat_id=group[0], text=error_text)
        LOGGER.error(f'【定时任务错误】{task_name}: {error_msg}')
    except Exception as e:
        LOGGER.error(f'【发送错误通知失败】{task_name}: {str(e)}')

# 创建带错误处理的包装函数
async def user_day_plays_with_error_handling():
    """每日观影结算 - 带错误处理"""
    try:
        await user_plays_rank(1)
        LOGGER.info('【定时任务成功】每日观影结算执行完成')
    except Exception as e:
        error_msg = f'每日观影结算执行失败: {str(e)}'
        await send_task_error_notification(
            task_name='每日观影结算', 
            error_msg=error_msg,
            manual_command='/uranks 1'
        )

async def user_week_plays_with_error_handling():
    """每周观影结算 - 带错误处理"""
    try:
        await user_plays_rank(7)
        LOGGER.info('【定时任务成功】每周观影结算执行完成')
    except Exception as e:
        error_msg = f'每周观影结算执行失败: {str(e)}'
        await send_task_error_notification(
            task_name='每周观影结算', 
            error_msg=error_msg,
            manual_command='/uranks 7'
        )

# 为其他关键任务也添加错误处理
async def check_low_activity_with_error_handling():
    """低活跃度检测 - 带错误处理"""
    try:
        await check_low_activity()
        LOGGER.info('【定时任务成功】低活跃度检测执行完成')
    except Exception as e:
        error_msg = f'低活跃度检测执行失败: {str(e)}'
        await send_task_error_notification(
            task_name='低活跃度检测', 
            error_msg=error_msg,
            manual_command='/low_activity'
        )

async def backup_db_with_error_handling():
    """数据库备份 - 带错误处理"""
    try:
        await auto_backup_db()
        LOGGER.info('【定时任务成功】数据库备份执行完成')
    except Exception as e:
        error_msg = f'数据库备份执行失败: {str(e)}'
        await send_task_error_notification(
            task_name='数据库备份', 
            error_msg=error_msg,
            manual_command='/backup_db'
        )

# 保留原来的函数作为兼容性和手动调用
async def user_day_plays(): await user_plays_rank(1)
async def user_week_plays(): await user_plays_rank(7)


# 写优雅点
# 字典，method相应的操作函数
action_dict = {
    "dayrank": day_ranks,
    "weekrank": week_ranks,
    "dayplayrank": user_day_plays_with_error_handling,  # 使用带错误处理的版本
    "weekplayrank": user_week_plays_with_error_handling,  # 使用带错误处理的版本
    "check_ex": check_expired,
    "low_activity": check_low_activity_with_error_handling,  # 使用带错误处理的版本
    "backup_db": backup_db_with_error_handling,  # 使用带错误处理的版本
}

# 字典，对应的操作函数的参数和id
args_dict = {
    "dayrank": {'hour': 18, 'minute': 30, 'id': 'day_ranks'},
    "weekrank": {'day_of_week': "sun", 'hour': 23, 'minute': 59, 'id': 'week_ranks'},
    "dayplayrank": {'hour': 23, 'minute': 0, 'id': 'user_day_plays'},
    "weekplayrank": {'day_of_week': "sun", 'hour': 23, 'minute': 0, 'id': 'user_week_plays'},
    "check_ex": {'hour': 1, 'minute': 30, 'id': 'check_expired'},
    "low_activity": {'hour': 8, 'minute': 30, 'id': 'check_low_activity'},
    "backup_db": {'hour': 2, 'minute': 30, 'id': 'backup_db'},
}


def set_all_sche():
    for key, value in action_dict.items():
        if getattr(schedall, key):
            action = action_dict[key]
            args = args_dict[key]
            scheduler.add_job(action, 'cron', **args)


set_all_sche()


async def sched_panel(_, msg):
    # await deleteMessage(msg)
    await editMessage(msg,
                      text=f'🎮 **管理定时任务面板**\n\n',
                      buttons=sched_buttons())


@bot.on_callback_query(filters.regex('sched') & admins_on_filter)
async def sched_change_policy(_, call):
    try:
        method = call.data.split('-')[1]
        # 根据method的值来添加或移除相应的任务
        action = action_dict[method]
        args = args_dict[method]
        if getattr(schedall, method):
            scheduler.remove_job(job_id=args['id'], jobstore='default')
        else:
            scheduler.add_job(action, 'cron', **args)
        setattr(schedall, method, not getattr(schedall, method))
        save_config()
        await asyncio.gather(callAnswer(call, f'⭕️ {method} 更改成功'), sched_panel(_, call.message))
    except IndexError:
        await sched_panel(_, call.message)


@bot.on_message(filters.command('check_ex', prefixes) & admins_on_filter)
async def check_ex_admin(_, msg):
    send = await msg.reply("🍥 正在运行 【到期检测】。。。")
    await check_expired()
    await asyncio.gather(msg.delete(), send.edit("✅ 【到期检测结束】"))


# bot数据库手动备份
@bot.on_message(filters.command('backup_db', prefixes) & filters.user(owner))
async def manual_backup_db(_, msg):
    await asyncio.gather(deleteMessage(msg), auto_backup_db())


@bot.on_message(filters.command('days_ranks', prefixes) & admins_on_filter)
async def day_r_ranks(_, msg):
    await asyncio.gather(msg.delete(), day_ranks(pin_mode=False))


@bot.on_message(filters.command('week_ranks', prefixes) & admins_on_filter)
async def week_r_ranks(_, msg):
    await asyncio.gather(msg.delete(), week_ranks(pin_mode=False))


@bot.on_message(filters.command('low_activity', prefixes) & admins_on_filter)
async def run_low_ac(_, msg):
    await deleteMessage(msg)
    send = await msg.reply(f"⭕ 不活跃检测运行ing···")
    await asyncio.gather(check_low_activity(), send.delete())


@bot.on_message(filters.command('uranks', prefixes) & admins_on_filter)
async def shou_dong_uplayrank(_, msg):
    await deleteMessage(msg)
    try:
        days = int(msg.command[1])
        await user_plays_rank(days=days, uplays=False)
    except (IndexError, ValueError):
        await msg.reply(
            f"🔔 请输入 `/uranks 天数`，此运行手动不会影响{sakura_b}的结算（仅定时运行时结算），放心使用。\n"
            f"定时结算状态: {_open.uplays}")

@bot.on_message(filters.command('force_settlement', prefixes) & admins_on_filter)
async def force_settlement_command(_, msg):
    """强制执行结算命令 - 紧急情况下使用"""
    await deleteMessage(msg)
    try:
        # 解析参数
        if len(msg.command) < 2:
            await msg.reply(
                "🔔 **强制结算命令说明**\n\n"
                "用法: `/force_settlement <天数> [confirm]`\n"
                "例如: `/force_settlement 1 confirm` - 强制执行1天结算\n"
                "例如: `/force_settlement 7 confirm` - 强制执行7天结算\n\n"
                "⚠️ **注意**: 此命令会直接影响用户余额，请谨慎使用！\n"
                "只有在定时任务失败时才建议使用此命令。"
            )
            return

        days = int(msg.command[1])
        confirm = len(msg.command) > 2 and msg.command[2].lower() == 'confirm'
        
        if not confirm:
            await msg.reply(
                f"⚠️ **确认强制执行{days}天结算？**\n\n"
                f"此操作将会：\n"
                f"1. 计算过去{days}天的观影排行\n" 
                f"2. 直接为符合条件的用户增加{sakura_b}\n"
                f"3. 发送奖励通知\n\n"
                f"如果确认执行，请使用: `/force_settlement {days} confirm`\n\n"
                f"💡 如果只想查看排行而不结算，请使用: `/uranks {days}`"
            )
            return
        
        # 发送执行中通知
        send = await msg.reply(f"⚡ **正在强制执行{days}天结算...**\n请稍等，执行完成后会有通知。")
        
        try:
            # 强制执行结算
            await user_plays_rank(days=days, uplays=True)
            
            await send.edit(
                f"✅ **强制结算执行成功**\n\n"
                f"已完成{days}天观影结算，用户余额已更新。\n"
                f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"请检查群聊中的结算通知消息确认结果。"
            )
            
            LOGGER.info(f'【手动强制结算】成功执行{days}天结算 - 管理员: {msg.from_user.id}')
            
        except Exception as e:
            error_msg = f"强制结算执行失败: {str(e)}"
            await send.edit(
                f"❌ **强制结算执行失败**\n\n"
                f"错误信息: {error_msg}\n"
                f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"请检查系统状态或联系技术人员。"
            )
            LOGGER.error(f'【手动强制结算】执行失败 - 管理员: {msg.from_user.id}, 错误: {error_msg}')
            
    except (IndexError, ValueError):
        await msg.reply(
            "❌ **参数错误**\n\n"
            "请输入正确的天数，例如: `/force_settlement 1` 或 `/force_settlement 7`"
        )
@bot.on_message(filters.command('settlement_status', prefixes) & admins_on_filter)
async def settlement_status_command(_, msg):
    """查看结算系统状态"""
    await deleteMessage(msg)
    
    try:
        # 获取当前配置状态
        settlement_enabled = _open.uplays
        
        # 获取最近的任务状态
        status_text = f"📊 **用户观影结算系统状态**\n\n"
        status_text += f"🔧 **系统配置**\n"
        status_text += f"- 自动结算: {'✅ 启用' if settlement_enabled else '❌ 禁用'}\n"
        status_text += f"- 货币单位: {sakura_b}\n\n"
        
        status_text += f"⏰ **定时任务安排**\n"
        status_text += f"- 每日结算: {'✅ 启用' if getattr(schedall, 'dayplayrank', False) else '❌ 禁用'} (23:00)\n"
        status_text += f"- 每周结算: {'✅ 启用' if getattr(schedall, 'weekplayrank', False) else '❌ 禁用'} (周日 23:00)\n"
        status_text += f"- 活跃检测: {'✅ 启用' if getattr(schedall, 'low_activity', False) else '❌ 禁用'} (08:30)\n\n"
        
        status_text += f"🛠️ **管理命令**\n"
        status_text += f"- `/uranks <天数>` - 查看排行（不结算）\n"
        status_text += f"- `/force_settlement <天数> confirm` - 强制结算\n"
        status_text += f"- `/settlement_status` - 查看系统状态\n"
        status_text += f"- `/test_settlement_error` - 测试错误通知\n\n"
        
        status_text += f"⚠️ **错误通知系统**: ✅ 已启用\n"
        status_text += f"当定时任务执行失败时，系统会自动发送通知到此群聊。\n\n"
        
        status_text += f"🕐 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        await msg.reply(status_text)
        
    except Exception as e:
        await msg.reply(f"❌ 获取系统状态失败: {str(e)}")
        LOGGER.error(f'【settlement_status】: 获取状态失败 - {str(e)}')

@bot.on_message(filters.command('test_settlement_error', prefixes) & admins_on_filter)  
async def test_settlement_error_notification(_, msg):
    """测试错误通知系统"""
    await deleteMessage(msg)
    
    try:
        await send_task_error_notification(
            task_name='系统测试',
            error_msg='这是一个测试错误通知，用于验证错误通知系统是否正常工作。',
            manual_command='/test_command'
        )
        
        await msg.reply(
            "✅ **错误通知测试已发送**\n\n"
            "请检查群聊中是否收到了测试错误通知消息。\n"
            "如果未收到通知，可能存在以下问题：\n"
            "- 群聊配置错误\n"
            "- 机器人发送消息权限不足\n"
            "- 网络连接问题"
        )
        
        LOGGER.info(f'【test_settlement_error】: 管理员 {msg.from_user.id} 执行了错误通知测试')
        
    except Exception as e:
        await msg.reply(f"❌ 测试失败: {str(e)}")
        LOGGER.error(f'【test_settlement_error】: 测试失败 - {str(e)}')

@bot.on_message(filters.command('sync_favorites', prefixes) & admins_on_filter)
async def sync_favorites_admin(_, msg):
    await deleteMessage(msg)
    await msg.reply("⭕ 正在同步用户收藏记录...")
    await sync_favorites()
    await msg.reply("✅ 用户收藏记录同步完成")

@bot.on_message(filters.command('restart', prefixes) & admins_on_filter)
async def restart_bot(_, msg):
    await deleteMessage(msg)
    send = await msg.reply("Restarting，等待几秒钟。")
    schedall.restart_chat_id = send.chat.id
    schedall.restart_msg_id = send.id
    save_config()
    try:
        # some code here
        LOGGER.info("重启")
        os.execl('/bin/systemctl', 'systemctl', 'restart', 'embyboss')  # 用当前进程执行systemctl命令，重启embyboss服务
    except FileNotFoundError:
        exit(1)


@bot.on_callback_query(filters.regex('uranks') & user_in_group_on_filter)
async def page_uplayrank(_, call):
    j, days = map(int, call.data.split(":")[1].split('_'))
    await callAnswer(call, f'将为您翻到第 {j} 页')
    a, b, c = await Uplaysinfo.users_playback_list(days)
    if not a:
        return await callAnswer(call, f'🍥 获取过去{days}天UserPlays失败了嘤嘤嘤 ~ 手动重试', True)
    button = await plays_list_button(b, j, days)
    text = a[j - 1]
    await editMessage(call, text, buttons=button)


from asyncio import create_subprocess_shell

from asyncio.subprocess import PIPE


async def execute(command, pass_error=True):
    """执行"""
    executor = await create_subprocess_shell(
        command, stdout=PIPE, stderr=PIPE, stdin=PIPE
    )

    stdout, stderr = await executor.communicate()
    if pass_error:
        try:
            result = str(stdout.decode().strip()) + str(stderr.decode().strip())
        except UnicodeDecodeError:
            result = str(stdout.decode("gbk").strip()) + str(stderr.decode("gbk").strip())
    else:
        try:
            result = str(stdout.decode().strip())
        except UnicodeDecodeError:
            result = str(stdout.decode("gbk").strip())
    return result


from sys import executable, argv


@scheduler.SCHEDULER.scheduled_job('cron', hour='12', minute='30', id='update_bot')
async def update_bot(force: bool = False, msg: Message = None, manual: bool = False):
    """
    此为未被测试的代码片段。
    """
    # print("update")
    if not auto_update.status and not manual: return
    commit_url = f"https://api.github.com/repos/{auto_update.git_repo}/commits?per_page=1"
    resp = requests.get(commit_url)
    if resp.status_code == 200:
        latest_commit = resp.json()[0]["sha"]
        if latest_commit != auto_update.commit_sha:
            up_description = resp.json()[0]["commit"]["message"]
            await execute("git fetch --all")
            if force:  # 默认不重置，保留本地更改
                await execute("git reset --hard origin/master")
            await execute("git pull --all")
            # await execute(f"{executable} -m pip install --upgrade -r requirements.txt")
            await execute(f"{executable} -m pip install  -r requirements.txt")
            text = '【AutoUpdate_Bot】运行成功，已更新bot代码。重启bot中...'
            if not msg:
                reply = await bot.send_message(chat_id=group[0], text=text)
                schedall.restart_chat_id = group[0]
                schedall.restart_msg_id = reply.id
            else:
                await msg.edit(text)
            LOGGER.info(text)
            auto_update.commit_sha = latest_commit
            auto_update.up_description = up_description
            save_config()
            os.execl(executable, executable, *argv)
        else:
            message = "【AutoUpdate_Bot】运行成功，未检测到更新，结束"
            await bot.send_message(chat_id=group[0], text=message) if not msg else await msg.edit(message)
            LOGGER.info(message)

    else:
        text = '【AutoUpdate_Bot】失败，请检查 git_repo 是否正确，形如 `berry8838/Sakura_embyboss`'
        await bot.send_message(chat_id=group[0], text=text) if not msg else await msg.edit(text)
        LOGGER.info(text)


@bot.on_message(filters.command('update_bot', prefixes) & admins_on_filter)
async def get_update_bot(_, msg: Message):
    delete_task = msg.delete()
    send_task = bot.send_message(chat_id=msg.chat.id, text='正在更新bot代码，请稍等。。。')
    results = await asyncio.gather(delete_task, send_task)
    # results[1] 是发送消息的结果，从中提取 chat_id 和 message_id
    if len(results) == 2 and isinstance(results[1], Message):
        reply = results[1]
        schedall.restart_chat_id = reply.chat.id
        schedall.restart_msg_id = reply.id
        save_config()
        await update_bot(msg=reply, manual=True)