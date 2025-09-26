"""
管理员ME点播请求管理命令 - 仅限管理员和Owner可访问
demand - 查看和管理ME点播请求，支持状态编辑
限制：只有管理员(owner、admins)可以使用此命令，群组成员无法访问
功能：记录用户ID，使用北京时间显示
"""

from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import bot, prefixes, LOGGER
from bot.func_helper.filters import admins_filter
from bot.func_helper.msg_utils import sendMessage, deleteMessage, editMessage, callAnswer, callListen
from bot.sql_helper.sql_request_record import (
    sql_get_all_request_records,
    sql_get_request_records_by_state, 
    sql_delete_request_record,
    sql_update_request_status
)
from datetime import datetime
import pytz
import math

# Beijing timezone for consistent time display
BEIJING_TZ = pytz.timezone('Asia/Shanghai')
RECORDS_PER_PAGE = 20


def format_beijing_time(utc_time):
    """Convert UTC time to Beijing time for display"""
    if not utc_time:
        return "未知时间"
    
    try:
        # If the time is naive (no timezone), assume it's UTC
        if utc_time.tzinfo is None:
            utc_time = pytz.utc.localize(utc_time)
        
        # Convert to Beijing time
        beijing_time = utc_time.astimezone(BEIJING_TZ)
        return beijing_time.strftime('%m-%d %H:%M')
    except:
        return "未知时间"


def format_demand_records(current_page=1, current_filter="all"):
    """格式化ME点播请求记录显示"""
    try:
        # 获取记录 - 只显示ME点播请求
        if current_filter == "all":
            records, has_prev, has_next, total_records = sql_get_all_request_records(page=current_page, limit=RECORDS_PER_PAGE)
            # 过滤只显示ME开头的请求
            records = [r for r in records if r.download_id.startswith('ME')]
            total_records = len(records) if records else 0
        else:
            records, has_prev, has_next, total_records = sql_get_request_records_by_state(download_state=current_filter, page=current_page, limit=RECORDS_PER_PAGE)
            # 过滤只显示ME开头的请求
            records = [r for r in records if r.download_id.startswith('ME')]
            total_records = len(records) if records else 0

        if not records:
            text = "📋 暂无ME点播请求记录"
            keyboard = get_demand_records_keyboard(1, 1, current_filter)
            return text, keyboard

        total_pages = max(1, math.ceil(total_records / RECORDS_PER_PAGE))
        text = f"📋 ME点播请求记录 (第{current_page}/{total_pages}页，共{total_records}条)\n\n"

        for record in records:
            # 格式化北京时间显示
            time_str = format_beijing_time(record.create_at)
            
            # 用户ID信息 - 记录点播用户的Telegram ID
            user_info = f"用户ID: {record.tg}"
            
            text += f"🎬 {record.request_name}\n"
            text += f"   {time_str} | {user_info}\n"
            text += f"   请求ID: {record.download_id}\n\n"

        keyboard = get_demand_records_keyboard(current_page, total_pages, current_filter)
        return text, keyboard

    except Exception as e:
        LOGGER.error(f"格式化请求记录失败: {str(e)}")
        return "❌ 获取记录失败", None


def get_demand_records_keyboard(current_page, total_pages, current_filter="all"):
    """生成请求记录的键盘"""
    keyboard = []
    
    # 筛选按钮行 - 分为两行显示
    filter_buttons = [
        ("📋 全部", "all"),
        ("⏳ 待处理", "pending"),
        ("🔄 处理中", "downloading"),
        ("✅ 已入库", "completed")
    ]
    
    # 第一行：全部、待处理
    filter_row1 = []
    for text, filter_type in filter_buttons[:2]:
        callback_data = f"demand_filter_{filter_type}"
        if filter_type == current_filter:
            text = f"• {text} •"  # 当前选中的筛选项
        filter_row1.append(InlineKeyboardButton(text, callback_data=callback_data))
    keyboard.append(filter_row1)
    
    # 第二行：处理中、已入库
    filter_row2 = []
    for text, filter_type in filter_buttons[2:]:
        callback_data = f"demand_filter_{filter_type}"
        if filter_type == current_filter:
            text = f"• {text} •"  # 当前选中的筛选项
        filter_row2.append(InlineKeyboardButton(text, callback_data=callback_data))
    keyboard.append(filter_row2)
    
    # 分页按钮行
    page_row = []
    if current_page > 1:
        page_row.append(InlineKeyboardButton("⬅️ 上页", callback_data=f"demand_page_{current_page-1}_{current_filter}"))
    
    page_row.append(InlineKeyboardButton("🔄 刷新", callback_data=f"demand_refresh_{current_filter}"))
    
    if current_page < total_pages:
        page_row.append(InlineKeyboardButton("下页 ➡️", callback_data=f"demand_page_{current_page+1}_{current_filter}"))
    
    if page_row:
        keyboard.append(page_row)
    
    # 状态编辑按钮行
    edit_row = [
        InlineKeyboardButton("📝 编辑状态", callback_data="demand_edit_status")
    ]
    keyboard.append(edit_row)
    
    # 取消按钮行
    cancel_row = [
        InlineKeyboardButton("❌ 取消", callback_data="closeit")
    ]
    keyboard.append(cancel_row)
    
    return InlineKeyboardMarkup(keyboard)


@bot.on_message(filters.command('demand', prefixes) & admins_filter)
async def demand_command(_, msg):
    """
    ME点播请求管理命令 - 仅限管理员和Owner使用
    
    权限限制：只有管理员(owner、admins)可以访问，群组成员无法使用
    功能：查看和管理ME点播请求，记录用户ID，使用北京时间显示
    """
    try:
        await deleteMessage(msg)
        
        # 解析命令参数
        args = msg.command[1:] if len(msg.command) > 1 else []
        
        if len(args) == 0:
            # 显示所有ME点播请求
            text, keyboard = format_demand_records(1, "all")
            await sendMessage(msg, text, send=True, chat_id=msg.chat.id, buttons=keyboard)
            
        elif args[0] in ['pending', 'completed']:
            # 按状态筛选ME点播请求
            filter_type = args[0]
            text, keyboard = format_demand_records(1, filter_type)
            await sendMessage(msg, text, send=True, chat_id=msg.chat.id, buttons=keyboard)
            
        elif args[0] == 'del' and len(args) >= 2:
            # 删除ME点播请求
            download_id = args[1]
            if not download_id.startswith('ME'):
                await sendMessage(msg, f"❌ 只能删除ME点播请求: `{download_id}`", send=True, chat_id=msg.chat.id)
                return
                
            success = sql_delete_request_record(download_id)
            
            if success:
                await sendMessage(msg, f"✅ 删除成功\n\n已删除ME点播请求: `{download_id}`", send=True, chat_id=msg.chat.id)
                LOGGER.info(f"管理员 {msg.from_user.id} 删除ME点播请求记录: {download_id}")
            else:
                await sendMessage(msg, f"❌ 删除失败\n\n请求ID不存在或删除出错: `{download_id}`", send=True, chat_id=msg.chat.id)
        

        
        elif args[0] == 'notify' and len(args) == 1:
            # 检查已完成的媒体并发送群组通知
            try:
                from bot.sql_helper.sql_request_record import sql_get_request_records_by_state
                from bot.sql_helper.sql_emby import sql_get_emby
                from bot import group, bot
                
                LOGGER.info(f"[Demand] 管理员 {msg.from_user.id} 开始检查已完成媒体并发送通知")
                
                # 获取已完成的ME点播请求
                completed_requests, _, _, _ = sql_get_request_records_by_state(download_state='completed', limit=100)
                me_completed = [r for r in completed_requests if r.download_id.startswith('ME')]
                
                if not me_completed:
                    await sendMessage(msg, "📋 暂无已完成的ME点播请求", send=True, chat_id=msg.chat.id)
                    return
                
                # 检查群组配置
                if not group or len(group) == 0:
                    await sendMessage(msg, "⚠️ 群组配置未设置，无法发送通知", send=True, chat_id=msg.chat.id)
                    LOGGER.warning(f"[Demand] 群组配置未设置，无法发送通知")
                    return
                
                await sendMessage(msg, f"📤 开始向群组发送 {len(me_completed)} 个已完成ME点播的通知...", send=True, chat_id=msg.chat.id)
                
                sent_count = 0
                failed_count = 0
                
                for request in me_completed:
                    try:
                        # 获取用户信息
                        user_info = sql_get_emby(tg=request.tg)
                        username = user_info.name if user_info else f"用户{request.tg}"
                        
                        # 构建通知消息
                        notification_text = (
                            f"🎉 **ME点播入库通知**\n\n"
                            f"🎬 **影片名称**: {request.request_name}\n"
                            f"📊 **点播状态**: 已入库 ✅\n"
                            f"👤 **ME用户**: {username}\n"
                            f"📺 影片已可在Emby中观看！\n"
                            f"🕐 **入库时间**: {format_beijing_time(request.update_at)}"
                        )
                        
                        # 发送群组通知
                        await bot.send_message(
                            chat_id=group[0],
                            text=notification_text
                        )
                        sent_count += 1
                        LOGGER.info(f"[Demand] 群组通知已发送: {request.request_name} (ID: {request.download_id})")
                        
                    except Exception as send_error:
                        failed_count += 1
                        LOGGER.error(f"[Demand] 发送群组通知失败 {request.download_id}: {str(send_error)}")
                
                # 发送结果统计
                result_msg = (
                    f"📤 群组通知发送完成\n\n"
                    f"✅ 成功发送: {sent_count}\n"
                    f"❌ 发送失败: {failed_count}\n"
                    f"📋 总计处理: {len(me_completed)}"
                )
                await sendMessage(msg, result_msg, send=True, chat_id=msg.chat.id)
                LOGGER.info(f"[Demand] 群组通知发送完成 - 成功: {sent_count}, 失败: {failed_count}")
                
            except Exception as e:
                error_msg = f"❌ 发送群组通知失败: {str(e)[:100]}"
                await sendMessage(msg, error_msg, send=True, chat_id=msg.chat.id)
                LOGGER.error(f"[Demand] 发送群组通知失败 (用户: {msg.from_user.id}): {str(e)}")
        else:
            # 帮助信息
            help_text = (
                "📋 **ME点播请求管理命令使用说明**\n\n"
                "🔍 **查看请求**:\n"
                "`/demand` - 查看所有ME点播请求\n"
                "`/demand pending` - 查看待处理请求\n"
                "`/demand completed` - 查看已入库请求\n\n"
                "🗑️ **删除请求**:\n"
                "`/demand del 请求ID` - 删除指定ME点播请求\n\n"
                "📝 **编辑状态**:\n"
                "• 点击界面中的'📝 编辑状态'按钮\n"
                "• 可用状态: pending(待处理), downloading(处理中), completed(已入库)\n"
                "• 状态更新为已入库时会自动发送群组通知\n\n"
                "`/demand notify` - 检查已完成媒体并发送群组通知\n\n"
                "💡 **说明**:\n"
                "• **仅限管理员和Owner使用**：只有管理员和Owner可以查看和管理请求，群组成员无法访问\n"
                "• 只显示和管理ME点播系统的请求\n"
                "• 🎬 标识ME点播请求\n"
                "• 显示点播用户的Telegram ID以便追踪\n"
                "• 时间显示为北京时间(UTC+8)\n"
                "• 手动编辑状态为已入库时会自动发送群组通知\n"
                "• 删除和编辑操作不可恢复，请谨慎操作\n"
                "• notify命令会重新发送已完成媒体的群组通知\n"
                "• 管理员可通过编辑状态功能更便捷地管理请求状态"
            )
            await sendMessage(msg, help_text, send=True, chat_id=msg.chat.id)
            
    except Exception as e:
        LOGGER.error(f"处理demand命令时出错 (用户: {msg.from_user.id}): {str(e)}")
        await sendMessage(msg, f"❌ 处理命令时出错: {str(e)[:100]}", send=True, chat_id=msg.chat.id)


@bot.on_callback_query(filters.regex(r'^demand_page_(\d+)_(.+)$') & admins_filter)
async def handle_demand_page(_, call):
    """处理分页请求"""
    try:
        page = int(call.matches[0].group(1))
        filter_type = call.matches[0].group(2)
        
        text, keyboard = format_demand_records(page, filter_type)
        await editMessage(call, text, buttons=keyboard)
        await callAnswer(call, f"已切换到第{page}页")
        
    except Exception as e:
        LOGGER.error(f"处理分页请求失败: {str(e)}")
        await callAnswer(call, "❌ 页面切换失败", True)


@bot.on_callback_query(filters.regex(r'^demand_filter_(.+)$') & admins_filter)
async def handle_demand_filter(_, call):
    """处理筛选请求"""
    try:
        filter_type = call.matches[0].group(1)
        
        text, keyboard = format_demand_records(1, filter_type)
        await editMessage(call, text, buttons=keyboard)
        
        filter_names = {
            "all": "全部",
            "pending": "待处理",
            "downloading": "处理中",
            "completed": "已入库"
        }
        await callAnswer(call, f"已筛选: {filter_names.get(filter_type, filter_type)}")
        
    except Exception as e:
        LOGGER.error(f"处理筛选请求失败: {str(e)}")
        await callAnswer(call, "❌ 筛选失败", True)


@bot.on_callback_query(filters.regex(r'^demand_refresh_(.+)$') & admins_filter)
async def handle_demand_refresh(_, call):
    """处理刷新请求"""
    try:
        filter_type = call.matches[0].group(1)
        
        text, keyboard = format_demand_records(1, filter_type)
        await editMessage(call, text, buttons=keyboard)
        await callAnswer(call, "🔄 已刷新")
        
    except Exception as e:
        LOGGER.error(f"处理刷新请求失败: {str(e)}")
        await callAnswer(call, "❌ 刷新失败", True)


@bot.on_callback_query(filters.regex(r'^demand_edit_status$') & admins_filter)
async def handle_demand_edit_status(_, call):
    """处理状态编辑请求"""
    try:
        await callAnswer(call, "📝 请发送: 请求ID 新状态")
        await editMessage(call, 
            "📝 编辑ME点播请求状态\n\n"
            "请按以下格式发送消息:\n"
            "`请求ID 新状态`\n\n"
            "可用状态: pending, downloading, completed\n\n"
            "示例: `ME20241201abc123 completed`\n"
            "取消请发送 /cancel")
        
        # 等待用户输入
        msg = await callListen(call, 120)
        if msg is False:
            await editMessage(call, "⏰ 操作超时")
            return
            
        if msg.text == '/cancel':
            await msg.delete()
            text, keyboard = format_demand_records(1, "all")
            await editMessage(call, text, buttons=keyboard)
            return
        
        # 解析输入
        parts = msg.text.strip().split()
        if len(parts) != 2:
            await msg.delete()
            await editMessage(call, "❌ 格式错误，请按格式: 请求ID 新状态")
            return
        
        request_id, new_status = parts
        
        # 验证是ME点播请求
        if not request_id.startswith('ME'):
            await msg.delete()
            await editMessage(call, f"❌ 只能编辑ME点播请求: {request_id}")
            return
        
        # 验证状态
        valid_statuses = ['pending', 'downloading', 'completed']
        if new_status not in valid_statuses:
            await msg.delete()
            await editMessage(call, f"❌ 无效状态，可用状态: {', '.join(valid_statuses)}")
            return
        
        # 更新状态
        success = sql_update_request_status(request_id, new_status)
        await msg.delete()
        
        if success:
            # 如果状态更新为已入库，发送群组通知
            if new_status == 'completed':
                try:
                    from bot.sql_helper.sql_request_record import sql_get_request_record_by_download_id
                    from bot.sql_helper.sql_emby import sql_get_emby
                    from bot import group, bot
                    
                    # 获取请求详情
                    request = sql_get_request_record_by_download_id(request_id)
                    if request and group and len(group) > 0:
                        # 获取用户信息
                        user_info = sql_get_emby(tg=request.tg)
                        username = user_info.name if user_info else f"用户{request.tg}"
                        
                        # 构建通知消息
                        notification_text = (
                            f"🎉 **ME点播入库通知**\n\n"
                            f"🎬 **影片名称**: {request.request_name}\n"
                            f"📊 **点播状态**: 已入库 ✅\n"
                            f"👤 **ME用户**: {username}\n"
                            f"📺 影片已可在Emby中观看！\n"
                            f"🕐 **入库时间**: {format_beijing_time(request.update_at)}"
                        )
                        
                        # 发送群组通知
                        await bot.send_message(
                            chat_id=group[0],
                            text=notification_text
                        )
                        LOGGER.info(f"[Demand] 手动状态更新通知已发送: {request.request_name} (ID: {request_id})")
                        
                except Exception as notify_error:
                    LOGGER.error(f"[Demand] 发送状态更新通知失败 {request_id}: {str(notify_error)}")
            
            text, keyboard = format_demand_records(1, "all")
            await editMessage(call, text, buttons=keyboard)
            await callAnswer(call, f"✅ 已更新请求 {request_id} 状态为 {new_status}")
            LOGGER.info(f"管理员 {call.from_user.id} 更新ME点播请求状态: {request_id} -> {new_status}")
        else:
            await editMessage(call, f"❌ 更新失败，请检查请求ID: {request_id}")
        
    except Exception as e:
        LOGGER.error(f"处理状态编辑失败: {str(e)}")
        await callAnswer(call, "❌ 编辑状态失败", True)


# Aliases for backward compatibility with imports
demand_page_callback = handle_demand_page
demand_filter_callback = handle_demand_filter
demand_refresh_callback = handle_demand_refresh