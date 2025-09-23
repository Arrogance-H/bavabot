"""
管理员影视请求管理命令
demand - 查看和管理影视请求
"""

from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import bot, prefixes, LOGGER, sakura_b
from bot.func_helper.filters import admins_on_filter
from bot.func_helper.msg_utils import sendMessage, deleteMessage, editMessage, callAnswer, callListen
from bot.sql_helper.sql_request_record import (
    sql_get_all_request_records, 
    sql_delete_request_record, 
    sql_get_request_records_by_state,
    RequestRecord
)
from bot.sql_helper.sql_emby import sql_get_emby
from bot.func_helper.fix_bottons import ikb
import math


def create_request_list_text(records, page, total_count, filter_type="all"):
    """创建请求列表文本"""
    if not records:
        return f"📋 **影视请求管理** (第{page}页)\n\n❌ 暂无请求记录"
    
    filter_text = {
        "all": "全部请求",
        "pending": "待处理请求", 
        "completed": "已完成请求",
        "failed": "失败请求"
    }.get(filter_type, "全部请求")
    
    text = f"📋 **影视请求管理** - {filter_text} (第{page}页)\n"
    text += f"📊 总计: {total_count} 条记录\n\n"
    
    for i, record in enumerate(records, 1):
        # 状态图标
        status_icon = {
            "pending": "⏳",
            "downloading": "⬇️", 
            "completed": "✅",
            "failed": "❌"
        }.get(record.download_state, "❓")
        
        # 请求类型判断
        request_type = "🎬" if "ME" in record.download_id else "🍿"
        
        text += f"{request_type} **{i + (page-1)*20}.** {record.request_name}\n"
        text += f"   📅 {record.create_at.strftime('%m-%d %H:%M')}"
        text += f" | {status_icon} {record.download_state or 'pending'}"
        text += f" | 💰 {record.cost}\n"
        text += f"   🆔 `{record.download_id}`\n\n"
    
    text += f"📝 使用 `/demand del 请求ID` 删除特定请求\n"
    text += f"🔍 使用 `/demand pending/completed/failed` 按状态筛选"
    
    return text


def create_request_buttons(has_prev, has_next, current_page, filter_type="all"):
    """创建请求列表按钮"""
    buttons = []
    
    # 状态筛选按钮
    filter_row = []
    if filter_type != "all":
        filter_row.append(('📋 全部', f'demand_filter:all:1'))
    if filter_type != "pending":
        filter_row.append(('⏳ 待处理', f'demand_filter:pending:1'))
    if filter_type != "completed":
        filter_row.append(('✅ 已完成', f'demand_filter:completed:1'))
    if filter_type != "failed":
        filter_row.append(('❌ 失败', f'demand_filter:failed:1'))
    
    if filter_row:
        buttons.append(filter_row)
    
    # 分页按钮 
    page_row = []
    if has_prev:
        page_row.append(('⬅️ 上页', f'demand_page:{filter_type}:{current_page-1}'))
    if has_next:
        page_row.append(('下页 ➡️', f'demand_page:{filter_type}:{current_page+1}'))
    
    if page_row:
        buttons.append(page_row)
    
    # 刷新按钮
    buttons.append([('🔄 刷新', f'demand_refresh:{filter_type}:{current_page}')])
    
    return ikb(buttons) if buttons else None


@bot.on_message(filters.command('demand', prefixes) & admins_on_filter)
async def demand_command(_, msg):
    """影视请求管理命令"""
    try:
        await deleteMessage(msg)
        
        # 解析命令参数
        args = msg.command[1:] if len(msg.command) > 1 else []
        
        if len(args) == 0:
            # 显示所有请求
            records, has_prev, has_next, total_count = sql_get_all_request_records(page=1, limit=20)
            text = create_request_list_text(records, 1, total_count, "all")
            buttons = create_request_buttons(has_prev, has_next, 1, "all")
            
            await sendMessage(msg, text, send=True, chat_id=msg.chat.id, 
                            buttons=buttons, parse_mode=ParseMode.MARKDOWN)
            
        elif args[0] in ['pending', 'completed', 'failed']:
            # 按状态筛选
            filter_type = args[0]
            download_state = filter_type if filter_type != 'failed' else 'failed'
            transfer_state = None
            
            records, has_prev, has_next, total_count = sql_get_request_records_by_state(
                download_state=download_state, page=1, limit=20)
            text = create_request_list_text(records, 1, total_count, filter_type)
            buttons = create_request_buttons(has_prev, has_next, 1, filter_type)
            
            await sendMessage(msg, text, send=True, chat_id=msg.chat.id,
                            buttons=buttons, parse_mode=ParseMode.MARKDOWN)
            
        elif args[0] == 'del' and len(args) >= 2:
            # 删除请求
            download_id = args[1]
            success = sql_delete_request_record(download_id)
            
            if success:
                await sendMessage(msg, f"✅ **删除成功**\n\n已删除请求: `{download_id}`",
                                send=True, chat_id=msg.chat.id, parse_mode=ParseMode.MARKDOWN)
                LOGGER.info(f"管理员删除请求记录: {download_id}")
            else:
                await sendMessage(msg, f"❌ **删除失败**\n\n请求ID不存在或删除出错: `{download_id}`",
                                send=True, chat_id=msg.chat.id, parse_mode=ParseMode.MARKDOWN)
        else:
            # 帮助信息
            help_text = (
                "📋 **影视请求管理命令使用说明**\n\n"
                "🔍 **查看请求**:\n"
                "`/demand` - 查看所有请求\n"
                "`/demand pending` - 查看待处理请求\n"
                "`/demand completed` - 查看已完成请求\n"
                "`/demand failed` - 查看失败请求\n\n"
                "🗑️ **删除请求**:\n"
                "`/demand del 请求ID` - 删除指定请求\n\n"
                "💡 **说明**:\n"
                "• 🎬 ME开头的请求来自ME点播系统\n"
                "• 🍿 其他请求来自MoviePilot点播系统\n"
                "• 只能删除已完成或失败的请求\n"
                "• 删除操作不可恢复，请谨慎操作"
            )
            await sendMessage(msg, help_text, send=True, chat_id=msg.chat.id, parse_mode=ParseMode.MARKDOWN)
            
    except Exception as e:
        LOGGER.error(f"处理demand命令时出错: {str(e)}")
        await sendMessage(msg, f"❌ 处理命令时出错: {str(e)[:100]}", send=True, chat_id=msg.chat.id)


@bot.on_callback_query(filters.regex('^demand_page:') & admins_on_filter)
async def demand_page_callback(_, call):
    """分页回调"""
    try:
        _, filter_type, page = call.data.split(':')
        page = int(page)
        
        await callAnswer(call, f'📋 第{page}页')
        
        if filter_type == "all":
            records, has_prev, has_next, total_count = sql_get_all_request_records(page=page, limit=20)
        else:
            download_state = filter_type if filter_type != 'failed' else 'failed'
            records, has_prev, has_next, total_count = sql_get_request_records_by_state(
                download_state=download_state, page=page, limit=20)
        
        text = create_request_list_text(records, page, total_count, filter_type)
        buttons = create_request_buttons(has_prev, has_next, page, filter_type)
        
        await editMessage(call, text, buttons=buttons, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        LOGGER.error(f"处理分页回调时出错: {str(e)}")
        await callAnswer(call, '❌ 处理分页时出错', True)


@bot.on_callback_query(filters.regex('^demand_filter:') & admins_on_filter)
async def demand_filter_callback(_, call):
    """筛选回调"""
    try:
        _, filter_type, page = call.data.split(':')
        page = int(page)
        
        filter_name = {
            "all": "全部请求",
            "pending": "待处理请求",
            "completed": "已完成请求", 
            "failed": "失败请求"
        }.get(filter_type, "全部请求")
        
        await callAnswer(call, f'🔍 {filter_name}')
        
        if filter_type == "all":
            records, has_prev, has_next, total_count = sql_get_all_request_records(page=page, limit=20)
        else:
            download_state = filter_type if filter_type != 'failed' else 'failed'
            records, has_prev, has_next, total_count = sql_get_request_records_by_state(
                download_state=download_state, page=page, limit=20)
        
        text = create_request_list_text(records, page, total_count, filter_type)
        buttons = create_request_buttons(has_prev, has_next, page, filter_type)
        
        await editMessage(call, text, buttons=buttons, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        LOGGER.error(f"处理筛选回调时出错: {str(e)}")
        await callAnswer(call, '❌ 处理筛选时出错', True)


@bot.on_callback_query(filters.regex('^demand_refresh:') & admins_on_filter)
async def demand_refresh_callback(_, call):
    """刷新回调"""
    try:
        _, filter_type, page = call.data.split(':')
        page = int(page)
        
        await callAnswer(call, '🔄 刷新数据')
        
        if filter_type == "all":
            records, has_prev, has_next, total_count = sql_get_all_request_records(page=page, limit=20)
        else:
            download_state = filter_type if filter_type != 'failed' else 'failed'
            records, has_prev, has_next, total_count = sql_get_request_records_by_state(
                download_state=download_state, page=page, limit=20)
        
        text = create_request_list_text(records, page, total_count, filter_type)
        buttons = create_request_buttons(has_prev, has_next, page, filter_type)
        
        await editMessage(call, text, buttons=buttons, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        LOGGER.error(f"处理刷新回调时出错: {str(e)}")
        await callAnswer(call, '❌ 刷新时出错', True)