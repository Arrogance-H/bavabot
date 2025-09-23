"""
管理员ME点播请求管理命令
demand - 查看和管理ME点播请求，支持状态编辑
"""

from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import bot, prefixes, LOGGER
from bot.func_helper.filters import admins_on_filter
from bot.func_helper.msg_utils import sendMessage, deleteMessage, editMessage, callAnswer, callListen
from bot.sql_helper.sql_request_record import (
    sql_get_all_request_records,
    sql_get_request_records_by_state, 
    sql_delete_request_record,
    sql_update_request_status
)
from datetime import datetime
import math

RECORDS_PER_PAGE = 20


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
            # 格式化时间显示
            try:
                time_str = record.create_at.strftime('%m-%d %H:%M')
            except:
                time_str = "未知时间"
            
            # ME点播固定费用
            cost_info = "费用: 10币"
            
            text += f"🎬 {record.request_name}\n"
            text += f"   {time_str} | {cost_info}\n"
            text += f"   ID: {record.download_id}\n\n"

        keyboard = get_demand_records_keyboard(current_page, total_pages, current_filter)
        return text, keyboard

    except Exception as e:
        LOGGER.error(f"格式化请求记录失败: {str(e)}")
        return "❌ 获取记录失败", None


def get_demand_records_keyboard(current_page, total_pages, current_filter="all"):
    """生成请求记录的键盘"""
    keyboard = []
    
    # 筛选按钮行
    filter_row = []
    filter_buttons = [
        ("📋 全部", "all"),
        ("⏳ 待处理", "pending"),
        ("✅ 已完成", "completed"),
        ("❌ 失败", "failed")
    ]
    
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


@bot.on_message(filters.command('demand', prefixes) & admins_on_filter)
async def demand_command(_, msg):
    """ME点播请求管理命令"""
    try:
        await deleteMessage(msg)
        
        # 解析命令参数
        args = msg.command[1:] if len(msg.command) > 1 else []
        
        if len(args) == 0:
            # 显示所有ME点播请求
            text, keyboard = format_demand_records(1, "all")
            await sendMessage(msg, text, send=True, chat_id=msg.chat.id, buttons=keyboard)
            
        elif args[0] in ['pending', 'completed', 'failed']:
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
                LOGGER.info(f"管理员删除ME点播请求记录: {download_id}")
            else:
                await sendMessage(msg, f"❌ 删除失败\n\n请求ID不存在或删除出错: `{download_id}`", send=True, chat_id=msg.chat.id)
        else:
            # 帮助信息
            help_text = (
                "📋 **ME点播请求管理命令使用说明**\n\n"
                "🔍 **查看请求**:\n"
                "`/demand` - 查看所有ME点播请求\n"
                "`/demand pending` - 查看待处理请求\n"
                "`/demand completed` - 查看已完成请求\n"
                "`/demand failed` - 查看失败请求\n\n"
                "🗑️ **删除请求**:\n"
                "`/demand del 请求ID` - 删除指定ME点播请求\n\n"
                "📝 **编辑状态**:\n"
                "• 点击界面中的'📝 编辑状态'按钮\n"
                "• 可用状态: pending, downloading, completed, failed\n\n"
                "💡 **说明**:\n"
                "• 只显示和管理ME点播系统的请求\n"
                "• 🎬 标识ME点播请求，固定费用10币\n"
                "• 删除和编辑操作不可恢复，请谨慎操作"
            )
            await sendMessage(msg, help_text, send=True, chat_id=msg.chat.id)
            
    except Exception as e:
        LOGGER.error(f"处理demand命令时出错: {str(e)}")
        await sendMessage(msg, f"❌ 处理命令时出错: {str(e)[:100]}", send=True, chat_id=msg.chat.id)


@bot.on_callback_query(filters.regex(r'^demand_page_(\d+)_(.+)$') & admins_on_filter)
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


@bot.on_callback_query(filters.regex(r'^demand_filter_(.+)$') & admins_on_filter)
async def handle_demand_filter(_, call):
    """处理筛选请求"""
    try:
        filter_type = call.matches[0].group(1)
        
        text, keyboard = format_demand_records(1, filter_type)
        await editMessage(call, text, buttons=keyboard)
        
        filter_names = {
            "all": "全部",
            "pending": "待处理",
            "completed": "已完成",
            "failed": "失败"
        }
        await callAnswer(call, f"已筛选: {filter_names.get(filter_type, filter_type)}")
        
    except Exception as e:
        LOGGER.error(f"处理筛选请求失败: {str(e)}")
        await callAnswer(call, "❌ 筛选失败", True)


@bot.on_callback_query(filters.regex(r'^demand_refresh_(.+)$') & admins_on_filter)
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


@bot.on_callback_query(filters.regex(r'^demand_edit_status$') & admins_on_filter)
async def handle_demand_edit_status(_, call):
    """处理状态编辑请求"""
    try:
        await callAnswer(call, "📝 请发送: 请求ID 新状态")
        await editMessage(call, 
            "📝 编辑ME点播请求状态\n\n"
            "请按以下格式发送消息:\n"
            "`请求ID 新状态`\n\n"
            "可用状态: pending, downloading, completed, failed\n\n"
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
        valid_statuses = ['pending', 'downloading', 'completed', 'failed']
        if new_status not in valid_statuses:
            await msg.delete()
            await editMessage(call, f"❌ 无效状态，可用状态: {', '.join(valid_statuses)}")
            return
        
        # 更新状态
        success = sql_update_request_status(request_id, new_status)
        await msg.delete()
        
        if success:
            text, keyboard = format_demand_records(1, "all")
            await editMessage(call, text, buttons=keyboard)
            await callAnswer(call, f"✅ 已更新请求 {request_id} 状态为 {new_status}")
            LOGGER.info(f"管理员更新ME点播请求状态: {request_id} -> {new_status}")
        else:
            await editMessage(call, f"❌ 更新失败，请检查请求ID: {request_id}")
        
    except Exception as e:
        LOGGER.error(f"处理状态编辑失败: {str(e)}")
        await callAnswer(call, "❌ 编辑状态失败", True)


# Aliases for backward compatibility with imports
demand_page_callback = handle_demand_page
demand_filter_callback = handle_demand_filter
demand_refresh_callback = handle_demand_refresh