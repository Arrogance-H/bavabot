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
    sql_update_request_status,
    sql_get_request_record_by_download_id
)
from bot.sql_helper.sql_emby import sql_get_emby
import pytz
import math

# Beijing timezone for consistent time display
BEIJING_TZ = pytz.timezone('Asia/Shanghai')
RECORDS_PER_PAGE = 5


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
        # 获取记录 - 首先获取所有ME点播请求，然后在代码中处理分页
        if current_filter == "all":
            all_records, _, _, _ = sql_get_all_request_records(page=1, limit=1000)  # Get more records
            # 过滤只显示ME开头的请求
            records = [r for r in all_records if r.download_id.startswith('ME')]
        else:
            all_records, _, _, _ = sql_get_request_records_by_state(download_state=current_filter, page=1, limit=1000)
            # 过滤只显示ME开头的请求
            records = [r for r in all_records if r.download_id.startswith('ME')]

        if not records:
            text = "📋 暂无ME点播请求记录"
            keyboard = get_demand_records_keyboard(1, 1, current_filter)
            return text, keyboard

        # 按点播时间（create_at）排序，最早的在前面
        records.sort(key=lambda x: x.create_at)
        
        total_records = len(records)
        total_pages = max(1, math.ceil(total_records / RECORDS_PER_PAGE))
        
        # 验证当前页是否有效
        if current_page > total_pages:
            current_page = total_pages
        if current_page < 1:
            current_page = 1
        
        # 计算当前页的记录范围
        start_idx = (current_page - 1) * RECORDS_PER_PAGE
        end_idx = start_idx + RECORDS_PER_PAGE
        page_records = records[start_idx:end_idx]
        
        text = f"📋 ME点播请求记录 (第{current_page}/{total_pages}页，共{total_records}条)\n\n"

        for idx, record in enumerate(page_records):
            # 计算全局序号（从1开始）
            global_idx = start_idx + idx + 1
            
            # 格式化北京时间显示
            time_str = format_beijing_time(record.create_at)
            
            # 用户ID信息 - 记录点播用户的Telegram ID
            user_info = f"用户ID: {record.tg}"
            
            # 状态显示
            status_emoji = {
                'pending': '⏳',
                'downloading': '🔄', 
                'completed': '✅'
            }.get(record.download_state, '❓')
            
            text += f"#{global_idx} 🎬 {record.request_name}\n"
            text += f"     {time_str} | {user_info} | {status_emoji}{record.download_state}\n"
            text += f"     请求ID: {record.download_id}\n\n"

        keyboard = get_demand_records_keyboard(current_page, total_pages, current_filter)
        return text, keyboard

    except Exception as e:
        LOGGER.error(f"格式化请求记录失败: {str(e)}")
        return "❌ 获取记录失败", None


def get_demand_records_keyboard(current_page, total_pages, current_filter="all"):
    """生成请求记录的键盘"""
    keyboard = []
    
    # 筛选按钮行
    filter_buttons = [
        ("📋 全部", "all"),
        ("⏳ 待处理", "pending"),
        ("✅ 已入库", "completed")
    ]
    
    # 筛选按钮行
    filter_row = []
    for text, filter_type in filter_buttons:
        callback_data = f"demand_filter_{filter_type}"
        if filter_type == current_filter:
            text = f"• {text} •"  # 当前选中的筛选项
        filter_row.append(InlineKeyboardButton(text, callback_data=callback_data))
    keyboard.append(filter_row)
    
    # 分页按钮行
    page_row = []
    if current_page > 1:
        page_row.append(InlineKeyboardButton("⬅️ 上页", callback_data=f"demand_page_{current_page-1}_{current_filter}"))
    
    if current_page < total_pages:
        page_row.append(InlineKeyboardButton("下页 ➡️", callback_data=f"demand_page_{current_page+1}_{current_filter}"))
    
    if page_row:
        keyboard.append(page_row)
    
    # 刷新和编辑状态按钮行 - 合并到同一行
    action_row = [
        InlineKeyboardButton("🔄 刷新", callback_data=f"demand_refresh_{current_filter}"),
        InlineKeyboardButton("📝 编辑状态", callback_data="demand_edit_status")
    ]
    keyboard.append(action_row)
    
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
            
        elif args[0] == 'notify' and len(args) == 1:
            # 检查已完成的媒体并发送群组通知
            try:
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
                            f"📺 影片已可在Emby中观看！"
                        )
                        
                        # 发送群组通知
                        await bot.send_message(
                            chat_id=group[0],
                            text=notification_text
                        )
                        sent_count += 1
                        LOGGER.info(f"[Demand] 群组通知已发送: {request.request_name} (ID: {request.download_id})")
                        
                        # 发送私聊通知给点播用户
                        try:
                            private_notification_text = (
                                f"🎉 **ME点播入库通知**\n\n"
                                f"🎬 **影片名称**: {request.request_name}\n"
                                f"📊 **点播状态**: 已入库 ✅\n"
                                f"📺 影片已可在Emby中观看！\n\n"
                                f"感谢您使用ME点播服务！"
                            )
                            
                            await bot.send_message(
                                chat_id=request.tg,
                                text=private_notification_text
                            )
                            LOGGER.info(f"[Demand] 私聊通知已发送给用户 {request.tg}: {request.request_name}")
                        except Exception as private_error:
                            LOGGER.error(f"[Demand] 发送私聊通知失败 (用户: {request.tg}): {str(private_error)}")
                        
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
    """处理状态编辑请求 - 新的序号选择方式"""
    try:
        await callAnswer(call, "📝 请发送影片序号")
        await editMessage(call, 
            "📝 编辑ME点播请求状态\n\n"
            "请发送要编辑的影片序号（如：1、2、3...）\n\n"
            "💡 提示：\n"
            "• 序号对应上方列表中的 #数字\n"
            "• 发送序号后可选择新状态\n"
            "• 取消请发送 /cancel")
        
        # 等待用户输入序号
        msg = await callListen(call, 120)
        if msg is False:
            await editMessage(call, "⏰ 操作超时")
            return
            
        if msg.text == '/cancel':
            await msg.delete()
            text, keyboard = format_demand_records(1, "all")
            await editMessage(call, text, buttons=keyboard)
            return
        
        # 解析序号
        try:
            sequence_num = int(msg.text.strip())
            if sequence_num < 1:
                await msg.delete()
                await editMessage(call, "❌ 序号必须为正整数")
                return
        except ValueError:
            await msg.delete()
            await editMessage(call, "❌ 请输入有效的序号数字")
            return
        
        await msg.delete()
        
        # 获取所有ME点播请求并按时间排序
        all_records, _, _, _ = sql_get_all_request_records(page=1, limit=1000)
        me_records = [r for r in all_records if r.download_id.startswith('ME')]
        me_records.sort(key=lambda x: x.create_at)
        
        # 检查序号是否有效
        if sequence_num > len(me_records):
            await editMessage(call, f"❌ 序号超出范围，当前共有 {len(me_records)} 条记录")
            return
        
        # 获取对应的记录
        selected_record = me_records[sequence_num - 1]
        
        # 显示选中的影片和状态选择按钮
        status_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⏳ 待处理", callback_data=f"demand_set_status_{selected_record.download_id}_pending")
            ],
            [
                InlineKeyboardButton("📽️ 已入库(删除)", callback_data=f"demand_set_transferred_{selected_record.download_id}")
            ],
            [
                InlineKeyboardButton("🗑️ 删除请求", callback_data=f"demand_delete_confirm_{selected_record.download_id}"),
                InlineKeyboardButton("❌ 取消", callback_data="demand_edit_status_cancel")
            ]
        ])
        
        current_status_text = {
            'pending': '⏳ 待处理',
            'downloading': '🔄 处理中', 
            'completed': '✅ 已入库'
        }.get(selected_record.download_state, '❓ 未知')
        
        status_text = (
            f"📝 选择新状态\n\n"
            f"🎬 **影片**: {selected_record.request_name}\n"
            f"📊 **当前状态**: {current_status_text}\n"
            f"🆔 **请求ID**: {selected_record.download_id}\n\n"
            f"请选择新的状态："
        )
        
        await editMessage(call, status_text, buttons=status_keyboard)
        
    except Exception as e:
        LOGGER.error(f"处理状态编辑失败: {str(e)}")
        await callAnswer(call, "❌ 编辑状态失败", True)


@bot.on_callback_query(filters.regex(r'^demand_set_status_(.+)_(.+)$') & admins_filter)
async def handle_demand_set_status(_, call):
    """处理状态设置请求"""
    try:
        request_id = call.matches[0].group(1)
        new_status = call.matches[0].group(2)
        
        # 更新状态
        success = sql_update_request_status(request_id, new_status)
        
        if success:
            # 返回主界面
            text, keyboard = format_demand_records(1, "all")
            await editMessage(call, text, buttons=keyboard)
            
            status_name = {
                'pending': '待处理'
            }.get(new_status, new_status)
            
            await callAnswer(call, f"✅ 已更新状态为: {status_name}")
            LOGGER.info(f"管理员 {call.from_user.id} 更新ME点播请求状态: {request_id} -> {new_status}")
        else:
            await editMessage(call, f"❌ 更新失败，请检查请求ID: {request_id}")
            
    except Exception as e:
        LOGGER.error(f"处理状态设置失败: {str(e)}")
        await callAnswer(call, "❌ 设置状态失败", True)


@bot.on_callback_query(filters.regex(r'^demand_set_transferred_(.+)$') & admins_filter)
async def handle_demand_set_transferred(_, call):
    """处理已入库(删除)请求 - 标记为已入库并删除记录"""
    try:
        request_id = call.matches[0].group(1)
        
        # 获取请求详情
        request = sql_get_request_record_by_download_id(request_id)
        
        if not request:
            await editMessage(call, f"❌ 请求不存在: {request_id}")
            return
        
        # 发送群组通知
        try:
            from bot import group, bot
            
            if group and len(group) > 0:
                # 获取用户信息
                user_info = sql_get_emby(tg=request.tg)
                username = user_info.name if user_info else f"用户{request.tg}"
                
                # 构建通知消息
                notification_text = (
                    f"🎉 **ME点播入库通知**\n\n"
                    f"🎬 **影片名称**: {request.request_name}\n"
                    f"📊 **点播状态**: 已入库 📽️\n"
                    f"👤 **ME用户**: {username}\n"
                    f"📺 影片已可在Emby中观看！"
                )
                
                # 发送群组通知
                await bot.send_message(
                    chat_id=group[0],
                    text=notification_text
                )
                LOGGER.info(f"[Demand] 已入库通知已发送: {request.request_name} (ID: {request_id})")
                
                # 发送私聊通知给点播用户
                try:
                    private_notification_text = (
                        f"🎉 **ME点播入库通知**\n\n"
                        f"🎬 **影片名称**: {request.request_name}\n"
                        f"📊 **点播状态**: 已入库 ✅\n"
                        f"📺 影片已可在Emby中观看！\n\n"
                        f"感谢您使用ME点播服务！"
                    )
                    
                    await bot.send_message(
                        chat_id=request.tg,
                        text=private_notification_text
                    )
                    LOGGER.info(f"[Demand] 私聊通知已发送给用户 {request.tg}: {request.request_name}")
                except Exception as private_error:
                    LOGGER.error(f"[Demand] 发送私聊通知失败 (用户: {request.tg}): {str(private_error)}")
                
        except Exception as notify_error:
            LOGGER.error(f"[Demand] 发送已入库通知失败 {request_id}: {str(notify_error)}")
        
        # 删除请求记录
        success = sql_delete_request_record(request_id)
        
        if success:
            # 返回主界面
            text, keyboard = format_demand_records(1, "all")
            await editMessage(call, text, buttons=keyboard)
            await callAnswer(call, "✅ 已标记为已入库并删除记录")
            LOGGER.info(f"管理员 {call.from_user.id} 标记ME点播请求为已入库并删除: {request_id}")
        else:
            await editMessage(call, f"❌ 删除失败，请求ID不存在: {request_id}")
            
    except Exception as e:
        LOGGER.error(f"处理已入库(删除)操作失败: {str(e)}")
        await callAnswer(call, "❌ 操作失败", True)


@bot.on_callback_query(filters.regex(r'^demand_delete_confirm_(.+)$') & admins_filter)
async def handle_demand_delete_confirm(_, call):
    """处理删除确认请求"""
    try:
        request_id = call.matches[0].group(1)
        
        # 获取请求详情以显示确认信息
        request = sql_get_request_record_by_download_id(request_id)
        
        if not request:
            await editMessage(call, f"❌ 请求不存在: {request_id}")
            return
        
        # 显示删除确认界面
        confirm_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🗑️ 确认删除", callback_data=f"demand_delete_execute_{request_id}")
            ],
            [
                InlineKeyboardButton("❌ 取消", callback_data="demand_edit_status_cancel")
            ]
        ])
        
        confirm_text = (
            f"⚠️ **确认删除ME点播请求**\n\n"
            f"🎬 **影片**: {request.request_name}\n"
            f"🆔 **请求ID**: {request.download_id}\n"
            f"👤 **用户ID**: {request.tg}\n\n"
            f"⚠️ **警告**: 删除操作不可恢复！\n"
            f"确定要删除这个请求吗？"
        )
        
        await editMessage(call, confirm_text, buttons=confirm_keyboard)
        await callAnswer(call, "请确认删除操作")
        
    except Exception as e:
        LOGGER.error(f"处理删除确认失败: {str(e)}")
        await callAnswer(call, "❌ 删除确认失败", True)


@bot.on_callback_query(filters.regex(r'^demand_delete_execute_(.+)$') & admins_filter)
async def handle_demand_delete_execute(_, call):
    """执行删除操作"""
    try:
        request_id = call.matches[0].group(1)
        
        # 执行删除
        success = sql_delete_request_record(request_id)
        
        if success:
            # 返回主界面
            text, keyboard = format_demand_records(1, "all")
            await editMessage(call, text, buttons=keyboard)
            await callAnswer(call, "✅ 删除成功")
            LOGGER.info(f"管理员 {call.from_user.id} 删除ME点播请求: {request_id}")
        else:
            await editMessage(call, f"❌ 删除失败，请求ID不存在: {request_id}")
            
    except Exception as e:
        LOGGER.error(f"执行删除操作失败: {str(e)}")
        await callAnswer(call, "❌ 删除失败", True)


@bot.on_callback_query(filters.regex(r'^demand_edit_status_cancel$') & admins_filter)
async def handle_demand_edit_status_cancel(_, call):
    """处理状态编辑取消请求"""
    try:
        text, keyboard = format_demand_records(1, "all")
        await editMessage(call, text, buttons=keyboard)
        await callAnswer(call, "已取消编辑")
        
    except Exception as e:
        LOGGER.error(f"处理编辑取消失败: {str(e)}")
        await callAnswer(call, "❌ 取消失败", True)


# Aliases for backward compatibility with imports
demand_page_callback = handle_demand_page
demand_filter_callback = handle_demand_filter
demand_refresh_callback = handle_demand_refresh
