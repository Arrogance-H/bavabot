"""
管理员ME点播请求管理命令 - 仅限管理员和Owner可访问
demand - 查看和管理ME点播请求，支持状态编辑
限制：只有管理员(owner、admins)可以使用此命令，群组成员无法访问
功能：记录用户ID，使用北京时间显示
"""

from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import bot, prefixes, LOGGER, sakura_b
from bot.func_helper.filters import admins_filter
from bot.func_helper.msg_utils import sendMessage, deleteMessage, editMessage, callAnswer, callListen
from bot.sql_helper.sql_request_record import (
    sql_get_all_request_records,
    sql_get_request_records_by_state, 
    sql_delete_request_record,
    sql_update_request_status,
    sql_get_request_record_by_download_id
)
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby
import pytz
import math

# Beijing timezone for consistent time display
BEIJING_TZ = pytz.timezone('Asia/Shanghai')
RECORDS_PER_PAGE = 5
COIN_DEDUCTION_PLAYABLE = 10  # JOY coins deducted when marking as playable


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


def get_user_demand_statistics():
    """获取按用户分组的点播统计"""
    try:
        all_records, _, _, _ = sql_get_all_request_records(page=1, limit=1000)
        me_records = [r for r in all_records if r.download_id.startswith('ME')]
        
        # 按用户分组统计
        user_stats = {}
        for record in me_records:
            tg_id = record.tg
            if tg_id not in user_stats:
                user_stats[tg_id] = {
                    'count': 0,
                    'records': []
                }
            user_stats[tg_id]['count'] += 1
            user_stats[tg_id]['records'].append(record)
        
        return user_stats
    except Exception as e:
        LOGGER.error(f"获取用户点播统计失败: {str(e)}")
        return {}


async def format_user_list(current_page=1):
    """格式化用户列表显示"""
    try:
        user_stats = get_user_demand_statistics()
        
        if not user_stats:
            text = "📋 暂无点播用户记录"
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("❌ 取消", callback_data="closeit")]])
            return text, keyboard
        
        # 按点播数量排序
        sorted_users = sorted(user_stats.items(), key=lambda x: x[1]['count'], reverse=True)
        
        total_users = len(sorted_users)
        total_pages = max(1, math.ceil(total_users / RECORDS_PER_PAGE))
        
        if current_page > total_pages:
            current_page = total_pages
        if current_page < 1:
            current_page = 1
        
        start_idx = (current_page - 1) * RECORDS_PER_PAGE
        end_idx = start_idx + RECORDS_PER_PAGE
        page_users = sorted_users[start_idx:end_idx]
        
        text = f"📊 点播用户统计 (第{current_page}/{total_pages}页，共{total_users}位用户)\n\n"
        
        keyboard_buttons = []
        for tg_id, stats in page_users:
            user_info = sql_get_emby(tg=tg_id)
            lv_dict = {
                'm': 'M尊享',
                'a': '白名单',
                'b': '普通用户',
                'c': '已禁用',
                'd': '未注册'
            }
            user_level = lv_dict.get(user_info.lv, '未知') if user_info else '未注册'
            
            # 获取TG昵称
            try:
                tg_user = await bot.get_users(tg_id)
                user_name = tg_user.first_name if tg_user.first_name else f"用户{tg_id}"
            except:
                user_name = f"用户{tg_id}"
            
            text += f"👤 {user_name} | 🎖️{user_level}\n"
            text += f"   📊 {stats['count']}条点播记录\n\n"
            
            # 添加按钮查看该用户的详细记录
            keyboard_buttons.append([InlineKeyboardButton(
                f"{user_name} ({stats['count']}条)",
                callback_data=f"demand_user_{tg_id}_1"
            )])
        
        # 分页按钮
        page_row = []
        if current_page > 1:
            page_row.append(InlineKeyboardButton("⬅️ 上页", callback_data=f"demand_userlist_{current_page-1}"))
        if current_page < total_pages:
            page_row.append(InlineKeyboardButton("下页 ➡️", callback_data=f"demand_userlist_{current_page+1}"))
        
        if page_row:
            keyboard_buttons.append(page_row)
        
        # 查看所有点播按钮
        keyboard_buttons.append([
            InlineKeyboardButton("📋 查看所有点播", callback_data="demand_view_all")
        ])
        
        # 取消按钮
        keyboard_buttons.append([
            InlineKeyboardButton("❌ 取消", callback_data="closeit")
        ])
        
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        return text, keyboard
        
    except Exception as e:
        LOGGER.error(f"格式化用户列表失败: {str(e)}")
        return "❌ 获取用户列表失败", None


async def format_user_demands(tg_id, current_page=1):
    """格式化单个用户的点播记录"""
    try:
        all_records, _, _, _ = sql_get_all_request_records(page=1, limit=1000)
        user_records = [r for r in all_records if r.download_id.startswith('ME') and r.tg == tg_id]
        
        if not user_records:
            text = "📋 该用户暂无点播记录"
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 返回用户列表", callback_data="demand_view_by_user"),
                InlineKeyboardButton("❌ 取消", callback_data="closeit")
            ]])
            return text, keyboard
        
        # 按时间排序
        user_records.sort(key=lambda x: x.create_at)
        
        total_records = len(user_records)
        total_pages = max(1, math.ceil(total_records / RECORDS_PER_PAGE))
        
        if current_page > total_pages:
            current_page = total_pages
        if current_page < 1:
            current_page = 1
        
        start_idx = (current_page - 1) * RECORDS_PER_PAGE
        end_idx = start_idx + RECORDS_PER_PAGE
        page_records = user_records[start_idx:end_idx]
        
        # 获取用户信息
        user_info = sql_get_emby(tg=tg_id)
        lv_dict = {
            'm': 'M尊享',
            'a': '白名单',
            'b': '普通用户',
            'c': '已禁用',
            'd': '未注册'
        }
        user_level = lv_dict.get(user_info.lv, '未知') if user_info else '未注册'
        
        # 获取TG昵称
        try:
            tg_user = await bot.get_users(tg_id)
            user_name = tg_user.first_name if tg_user.first_name else f"用户{tg_id}"
        except:
            user_name = f"用户{tg_id}"
        
        text = f"👤 {user_name} | 🎖️{user_level}\n"
        text += f"📊 共{total_records}条点播记录 (第{current_page}/{total_pages}页)\n\n"
        
        for idx, record in enumerate(page_records):
            global_idx = start_idx + idx + 1
            time_str = format_beijing_time(record.create_at)
            
            status_dict = {
                'pending': '⏳ 待处理',
                'downloading': '🔄 处理中',
                'completed': '✅ 已入库',
                'playable': '📽️ 可播放'
            }
            status = status_dict.get(record.download_state, '❓ 未知')
            
            text += f"#{global_idx} 🎬 {record.request_name}\n"
            text += f"     {time_str} | {status}\n"
            text += f"     请求ID: {record.download_id}\n\n"
        
        # 键盘
        keyboard_buttons = []
        
        # 分页按钮
        page_row = []
        if current_page > 1:
            page_row.append(InlineKeyboardButton("⬅️ 上页", callback_data=f"demand_user_{tg_id}_{current_page-1}"))
        if current_page < total_pages:
            page_row.append(InlineKeyboardButton("下页 ➡️", callback_data=f"demand_user_{tg_id}_{current_page+1}"))
        
        if page_row:
            keyboard_buttons.append(page_row)
        
        # 编辑状态按钮
        keyboard_buttons.append([
            InlineKeyboardButton("📝 编辑状态", callback_data=f"demand_user_edit_{tg_id}_{current_page}")
        ])
        
        # 返回按钮
        keyboard_buttons.append([
            InlineKeyboardButton("🔙 返回用户列表", callback_data="demand_view_by_user"),
            InlineKeyboardButton("❌ 取消", callback_data="closeit")
        ])
        
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        return text, keyboard
        
    except Exception as e:
        LOGGER.error(f"格式化用户点播记录失败: {str(e)}")
        return "❌ 获取用户记录失败", None


async def format_demand_records(current_page=1, current_filter="all"):
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
            
            # 获取用户等级信息
            user_info = sql_get_emby(tg=record.tg)
            lv_dict = {
                'm': 'M尊享',
                'a': '白名单',
                'b': '普通用户',
                'c': '已禁用',
                'd': '未注册'
            }
            user_level = lv_dict.get(user_info.lv, '未知') if user_info else '未注册'
            
            # 获取TG昵称
            try:
                tg_user = await bot.get_users(record.tg)
                user_name = tg_user.first_name if tg_user.first_name else f"用户{record.tg}"
            except:
                user_name = f"用户{record.tg}"
            
            # 用户信息显示 - 包含用户名和等级
            user_display = f"{user_name} | 🎖️{user_level}"
            
            text += f"#{global_idx} 🎬 {record.request_name}\n"
            text += f"     {time_str} | {user_display}\n"
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
        ("✅ 已入库", "completed"),
        ("📽️ 可播放", "playable")
    ]
    
    # 筛选按钮行（分两行显示）
    filter_row1 = []
    filter_row2 = []
    for idx, (text, filter_type) in enumerate(filter_buttons):
        callback_data = f"demand_filter_{filter_type}"
        if filter_type == current_filter:
            text = f"• {text} •"  # 当前选中的筛选项
        button = InlineKeyboardButton(text, callback_data=callback_data)
        if idx < 2:
            filter_row1.append(button)
        else:
            filter_row2.append(button)
    
    keyboard.append(filter_row1)
    keyboard.append(filter_row2)
    
    # 分页按钮行
    page_row = []
    if current_page > 1:
        page_row.append(InlineKeyboardButton("⬅️ 上页", callback_data=f"demand_page_{current_page-1}_{current_filter}"))
    
    if current_page < total_pages:
        page_row.append(InlineKeyboardButton("下页 ➡️", callback_data=f"demand_page_{current_page+1}_{current_filter}"))
    
    if page_row:
        keyboard.append(page_row)
    
    # 刷新和编辑状态按钮行
    action_row = [
        InlineKeyboardButton("🔄 刷新", callback_data=f"demand_refresh_{current_filter}"),
        InlineKeyboardButton("📝 编辑状态", callback_data="demand_edit_status")
    ]
    keyboard.append(action_row)
    
    # 按用户查看按钮
    user_view_row = [
        InlineKeyboardButton("👥 按用户查看", callback_data="demand_view_by_user")
    ]
    keyboard.append(user_view_row)
    
    # 取消按钮行
    cancel_row = [
        InlineKeyboardButton("❌ 取消", callback_data="closeit")
    ]
    keyboard.append(cancel_row)
    
    return InlineKeyboardMarkup(keyboard)


@bot.on_message(filters.command('demand', prefixes) & admins_filter)
async def demand_command(_, msg):
    """
    ME点播用户列表命令 - 仅限管理员和Owner使用
    
    权限限制：只有管理员(owner、admins)可以访问，群组成员无法使用
    功能：显示按用户分组的点播统计，点击用户可查看详细记录并编辑状态
    """
    try:
        await deleteMessage(msg)
        
        # 直接显示用户列表
        text, keyboard = await format_user_list(1)
        await sendMessage(msg, text, send=True, chat_id=msg.chat.id, buttons=keyboard)
            
    except Exception as e:
        LOGGER.error(f"处理demand命令时出错 (用户: {msg.from_user.id}): {str(e)}")
        await sendMessage(msg, f"❌ 处理命令时出错: {str(e)[:100]}", send=True, chat_id=msg.chat.id)


@bot.on_callback_query(filters.regex(r'^demand_page_(\d+)_(.+)$') & admins_filter)
async def handle_demand_page(_, call):
    """处理分页请求"""
    try:
        page = int(call.matches[0].group(1))
        filter_type = call.matches[0].group(2)
        
        text, keyboard = await format_demand_records(page, filter_type)
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
        
        text, keyboard = await format_demand_records(1, filter_type)
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
        
        text, keyboard = await format_demand_records(1, filter_type)
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
            text, keyboard = await format_demand_records(1, "all")
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
                InlineKeyboardButton("📽️ 可播放(扣币)", callback_data=f"demand_set_playable_{selected_record.download_id}")
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
            'completed': '✅ 已入库',
            'playable': '📽️ 可播放'
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


@bot.on_callback_query(filters.regex(r'^demand_set_playable_(.+)$') & admins_filter)
async def handle_demand_set_playable(_, call):
    """处理设置为可播放状态 - 扣除10 JOY币并通知用户"""
    try:
        request_id = call.matches[0].group(1)
        
        # 获取请求详情
        request = sql_get_request_record_by_download_id(request_id)
        
        if not request:
            await editMessage(call, f"❌ 请求不存在: {request_id}")
            return
        
        # 获取用户信息
        user_info = sql_get_emby(tg=request.tg)
        
        if not user_info:
            await editMessage(call, f"❌ 用户不存在: {request.tg}")
            return
        
        # 检查用户是否有足够的JOY币
        current_coins = user_info.iv
        if current_coins < COIN_DEDUCTION_PLAYABLE:
            await editMessage(call, 
                f"❌ 用户{user_info.name}的{sakura_b}不足\n\n"
                f"当前{sakura_b}: {current_coins}\n"
                f"需要扣除: {COIN_DEDUCTION_PLAYABLE}{sakura_b}\n\n"
                f"是否仍要标记为可播放？",
                buttons=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ 确认标记", callback_data=f"demand_playable_force_{request_id}")],
                    [InlineKeyboardButton("❌ 取消", callback_data="demand_edit_status_cancel")]
                ])
            )
            return
        
        # 扣除JOY币
        new_coins = current_coins - COIN_DEDUCTION_PLAYABLE
        success = sql_update_emby(Emby.tg == request.tg, iv=new_coins)
        
        if not success:
            await editMessage(call, f"❌ 扣除{sakura_b}失败")
            return
        
        # 更新状态为可播放
        status_success = sql_update_request_status(request_id, 'playable')
        
        if not status_success:
            # 如果状态更新失败，回退币扣除
            sql_update_emby(Emby.tg == request.tg, iv=current_coins)
            await editMessage(call, f"❌ 更新状态失败")
            return
        
        # 发送私聊通知给点播用户
        try:
            private_notification_text = (
                f"📽️ **点播惩罚通知**\n\n"
                f"🎬 **影片名称**: {request.request_name}\n"
                f"📺 该影片已可播放！\n\n"
                f"💰 **惩罚**: 已扣除 {COIN_DEDUCTION_PLAYABLE}{sakura_b}\n"
                f"💳 **当前余额**: {new_coins}{sakura_b}\n\n"
                f"下次注意哟，祝您观影愉快😀！"
            )
            
            await bot.send_message(
                chat_id=request.tg,
                text=private_notification_text
            )
            LOGGER.info(f"[Demand] 可播放通知已发送给用户 {request.tg}: {request.request_name}, 扣除{COIN_DEDUCTION_PLAYABLE}{sakura_b}")
        except Exception as private_error:
            LOGGER.error(f"[Demand] 发送可播放通知失败 (用户: {request.tg}): {str(private_error)}")
        
        # 删除请求记录
        delete_success = sql_delete_request_record(request_id)
        
        if not delete_success:
            LOGGER.error(f"[Demand] 删除点播请求记录失败: {request_id}")
        
        # 返回主界面
        text, keyboard = await format_demand_records(1, "all")
        await editMessage(call, text, buttons=keyboard)
        await callAnswer(call, f"✅ 已标记为可播放并删除记录，扣除{COIN_DEDUCTION_PLAYABLE}{sakura_b}")
        LOGGER.info(f"管理员 {call.from_user.id} 标记点播请求为可播放并删除: {request_id}, 用户: {request.tg}, 扣除{COIN_DEDUCTION_PLAYABLE}{sakura_b}")
        
    except Exception as e:
        LOGGER.error(f"处理可播放状态失败: {str(e)}")
        await callAnswer(call, "❌ 操作失败", True)


@bot.on_callback_query(filters.regex(r'^demand_playable_force_(.+)$') & admins_filter)
async def handle_demand_playable_force(_, call):
    """强制标记为可播放（即使币不足）"""
    try:
        request_id = call.matches[0].group(1)
        
        # 获取请求详情
        request = sql_get_request_record_by_download_id(request_id)
        
        if not request:
            await editMessage(call, f"❌ 请求不存在: {request_id}")
            return
        
        # 获取用户信息
        user_info = sql_get_emby(tg=request.tg)
        
        if not user_info:
            await editMessage(call, f"❌ 用户不存在: {request.tg}")
            return
        
        # 扣除JOY币（可能为负）
        current_coins = user_info.iv
        new_coins = current_coins - COIN_DEDUCTION_PLAYABLE
        success = sql_update_emby(Emby.tg == request.tg, iv=new_coins)
        
        if not success:
            await editMessage(call, f"❌ 扣除{sakura_b}失败")
            return
        
        # 更新状态为可播放
        status_success = sql_update_request_status(request_id, 'playable')
        
        if not status_success:
            # 如果状态更新失败，回退币扣除
            sql_update_emby(Emby.tg == request.tg, iv=current_coins)
            await editMessage(call, f"❌ 更新状态失败")
            return
        
        # 发送私聊通知给点播用户
        try:
            private_notification_text = (
                f"📽️ **点播惩罚通知**\n\n"
                f"🎬 **影片名称**: {request.request_name}\n"
                f"📺 该影片为可播放状态！\n\n"
                f"💰 **惩罚**: 已扣除 {COIN_DEDUCTION_PLAYABLE}{sakura_b}\n"
                f"💳 **当前余额**: {new_coins}{sakura_b}"
            )
            
            await bot.send_message(
                chat_id=request.tg,
                text=private_notification_text
            )
            LOGGER.info(f"[Demand] 可播放通知已发送给用户 {request.tg}: {request.request_name}, 扣除{COIN_DEDUCTION_PLAYABLE}{sakura_b}")
        except Exception as private_error:
            LOGGER.error(f"[Demand] 发送可播放通知失败 (用户: {request.tg}): {str(private_error)}")
        
        # 删除请求记录
        delete_success = sql_delete_request_record(request_id)
        
        if not delete_success:
            LOGGER.error(f"[Demand] 删除点播请求记录失败: {request_id}")
        
        # 返回主界面
        text, keyboard = await format_demand_records(1, "all")
        await editMessage(call, text, buttons=keyboard)
        await callAnswer(call, f"✅ 已标记为可播放并删除记录，扣除{COIN_DEDUCTION_PLAYABLE}{sakura_b}")
        LOGGER.info(f"管理员 {call.from_user.id} 强制标记点播请求为可播放并删除: {request_id}, 用户: {request.tg}, 扣除{COIN_DEDUCTION_PLAYABLE}{sakura_b}")
        
    except Exception as e:
        LOGGER.error(f"强制标记可播放状态失败: {str(e)}")
        await callAnswer(call, "❌ 操作失败", True)


@bot.on_callback_query(filters.regex(r'^demand_view_by_user$') & admins_filter)
async def handle_demand_view_by_user(_, call):
    """处理按用户查看请求"""
    try:
        text, keyboard = await format_user_list(1)
        await editMessage(call, text, buttons=keyboard)
        await callAnswer(call, "👥 按用户查看")
        
    except Exception as e:
        LOGGER.error(f"处理按用户查看失败: {str(e)}")
        await callAnswer(call, "❌ 查看失败", True)


@bot.on_callback_query(filters.regex(r'^demand_view_all$') & admins_filter)
async def handle_demand_view_all(_, call):
    """处理查看所有点播请求"""
    try:
        text, keyboard = await format_demand_records(1, "all")
        await editMessage(call, text, buttons=keyboard)
        await callAnswer(call, "📋 已切换到查看所有点播")
        
    except Exception as e:
        LOGGER.error(f"处理查看所有点播失败: {str(e)}")
        await callAnswer(call, "❌ 查看失败", True)


@bot.on_callback_query(filters.regex(r'^demand_userlist_(\d+)$') & admins_filter)
async def handle_demand_userlist_page(_, call):
    """处理用户列表分页"""
    try:
        page = int(call.matches[0].group(1))
        
        text, keyboard = await format_user_list(page)
        await editMessage(call, text, buttons=keyboard)
        await callAnswer(call, f"已切换到第{page}页")
        
    except Exception as e:
        LOGGER.error(f"处理用户列表分页失败: {str(e)}")
        await callAnswer(call, "❌ 分页失败", True)


@bot.on_callback_query(filters.regex(r'^demand_user_(\d+)_(\d+)$') & admins_filter)
async def handle_demand_user_records(_, call):
    """处理查看单个用户的点播记录"""
    try:
        tg_id = int(call.matches[0].group(1))
        page = int(call.matches[0].group(2))
        
        text, keyboard = await format_user_demands(tg_id, page)
        await editMessage(call, text, buttons=keyboard)
        await callAnswer(call, "查看用户点播记录")
        
    except Exception as e:
        LOGGER.error(f"处理用户点播记录失败: {str(e)}")
        await callAnswer(call, "❌ 查看失败", True)


@bot.on_callback_query(filters.regex(r'^demand_user_edit_(\d+)_(\d+)$') & admins_filter)
async def handle_demand_user_edit_status(_, call):
    """处理从用户视图编辑状态请求"""
    try:
        tg_id = int(call.matches[0].group(1))
        current_page = int(call.matches[0].group(2))
        
        await callAnswer(call, "📝 请发送影片序号")
        await editMessage(call, 
            "📝 编辑该用户的点播请求状态\n\n"
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
            text, keyboard = await format_user_demands(tg_id, current_page)
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
        
        # 获取该用户的所有ME点播请求并按时间排序
        all_records, _, _, _ = sql_get_all_request_records(page=1, limit=1000)
        user_records = [r for r in all_records if r.download_id.startswith('ME') and r.tg == tg_id]
        user_records.sort(key=lambda x: x.create_at)
        
        # 检查序号是否有效
        if sequence_num > len(user_records):
            await editMessage(call, f"❌ 序号超出范围，该用户共有 {len(user_records)} 条记录")
            return
        
        # 获取对应的记录
        selected_record = user_records[sequence_num - 1]
        
        # 显示选中的影片和状态选择按钮
        status_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⏳ 待处理", callback_data=f"demand_user_set_status_{selected_record.download_id}_{tg_id}_{current_page}_pending")
            ],
            [
                InlineKeyboardButton("📽️ 可播放(扣币)", callback_data=f"demand_user_set_playable_{selected_record.download_id}_{tg_id}_{current_page}")
            ],
            [
                InlineKeyboardButton("📽️ 已入库(删除)", callback_data=f"demand_user_set_transferred_{selected_record.download_id}_{tg_id}_{current_page}")
            ],
            [
                InlineKeyboardButton("🗑️ 删除请求", callback_data=f"demand_user_delete_confirm_{selected_record.download_id}_{tg_id}_{current_page}"),
                InlineKeyboardButton("❌ 取消", callback_data=f"demand_user_edit_cancel_{tg_id}_{current_page}")
            ]
        ])
        
        current_status_text = {
            'pending': '⏳ 待处理',
            'downloading': '🔄 处理中', 
            'completed': '✅ 已入库',
            'playable': '📽️ 可播放'
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
        LOGGER.error(f"处理用户视图状态编辑失败: {str(e)}")
        await callAnswer(call, "❌ 编辑状态失败", True)


@bot.on_callback_query(filters.regex(r'^demand_user_set_status_(.+)_(\d+)_(\d+)_(.+)$') & admins_filter)
async def handle_demand_user_set_status(_, call):
    """处理从用户视图设置状态请求"""
    try:
        request_id = call.matches[0].group(1)
        tg_id = int(call.matches[0].group(2))
        current_page = int(call.matches[0].group(3))
        new_status = call.matches[0].group(4)
        
        # 更新状态
        success = sql_update_request_status(request_id, new_status)
        
        if success:
            # 返回用户视图
            text, keyboard = await format_user_demands(tg_id, current_page)
            await editMessage(call, text, buttons=keyboard)
            
            status_name = {
                'pending': '待处理'
            }.get(new_status, new_status)
            
            await callAnswer(call, f"✅ 已更新状态为: {status_name}")
            LOGGER.info(f"管理员 {call.from_user.id} 在用户视图更新点播请求状态: {request_id} -> {new_status}")
        else:
            await editMessage(call, f"❌ 更新失败，请检查请求ID: {request_id}")
            
    except Exception as e:
        LOGGER.error(f"处理用户视图状态设置失败: {str(e)}")
        await callAnswer(call, "❌ 设置状态失败", True)


@bot.on_callback_query(filters.regex(r'^demand_user_set_playable_(.+)_(\d+)_(\d+)$') & admins_filter)
async def handle_demand_user_set_playable(_, call):
    """处理从用户视图设置为可播放状态 - 扣除JOY币并通知用户"""
    try:
        request_id = call.matches[0].group(1)
        tg_id = int(call.matches[0].group(2))
        current_page = int(call.matches[0].group(3))
        
        # 获取请求详情
        request = sql_get_request_record_by_download_id(request_id)
        
        if not request:
            await editMessage(call, f"❌ 请求不存在: {request_id}")
            return
        
        # 获取用户信息
        user_info = sql_get_emby(tg=request.tg)
        
        if not user_info:
            await editMessage(call, f"❌ 用户不存在: {request.tg}")
            return
        
        # 检查用户是否有足够的JOY币
        current_coins = user_info.iv
        if current_coins < COIN_DEDUCTION_PLAYABLE:
            await editMessage(call, 
                f"❌ 用户{user_info.name}的{sakura_b}不足\n\n"
                f"当前{sakura_b}: {current_coins}\n"
                f"需要扣除: {COIN_DEDUCTION_PLAYABLE}{sakura_b}\n\n"
                f"是否仍要标记为可播放？",
                buttons=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ 确认标记", callback_data=f"demand_user_playable_force_{request_id}_{tg_id}_{current_page}")],
                    [InlineKeyboardButton("❌ 取消", callback_data=f"demand_user_edit_cancel_{tg_id}_{current_page}")]
                ])
            )
            return
        
        # 扣除JOY币
        new_coins = current_coins - COIN_DEDUCTION_PLAYABLE
        success = sql_update_emby(Emby.tg == request.tg, iv=new_coins)
        
        if not success:
            await editMessage(call, f"❌ 扣除{sakura_b}失败")
            return
        
        # 更新状态为可播放
        status_success = sql_update_request_status(request_id, 'playable')
        
        if not status_success:
            # 如果状态更新失败，回退币扣除
            sql_update_emby(Emby.tg == request.tg, iv=current_coins)
            await editMessage(call, f"❌ 更新状态失败")
            return
        
        # 发送私聊通知给点播用户
        try:
            private_notification_text = (
                f"📽️ **点播可播放通知**\n\n"
                f"🎬 **影片名称**: {request.request_name}\n"
                f"📺 该影片已标记为可播放状态！\n\n"
                f"💰 **扣费提醒**: 已扣除 {COIN_DEDUCTION_PLAYABLE}{sakura_b}\n"
                f"💳 **当前余额**: {new_coins}{sakura_b}\n\n"
                f"影片已可在Emby中观看，祝您观影愉快😀！"
            )
            
            await bot.send_message(
                chat_id=request.tg,
                text=private_notification_text
            )
            LOGGER.info(f"[Demand] 可播放通知已发送给用户 {request.tg}: {request.request_name}, 扣除{COIN_DEDUCTION_PLAYABLE}{sakura_b}")
        except Exception as private_error:
            LOGGER.error(f"[Demand] 发送可播放通知失败 (用户: {request.tg}): {str(private_error)}")
        
        # 删除请求记录
        delete_success = sql_delete_request_record(request_id)
        
        if not delete_success:
            LOGGER.error(f"[Demand] 删除点播请求记录失败: {request_id}")
        
        # 返回用户视图
        text, keyboard = await format_user_demands(tg_id, current_page)
        await editMessage(call, text, buttons=keyboard)
        await callAnswer(call, f"✅ 已标记为可播放并删除记录，扣除{COIN_DEDUCTION_PLAYABLE}{sakura_b}")
        LOGGER.info(f"管理员 {call.from_user.id} 在用户视图标记点播请求为可播放并删除: {request_id}, 用户: {request.tg}, 扣除{COIN_DEDUCTION_PLAYABLE}{sakura_b}")
        
    except Exception as e:
        LOGGER.error(f"处理用户视图可播放状态失败: {str(e)}")
        await callAnswer(call, "❌ 操作失败", True)


@bot.on_callback_query(filters.regex(r'^demand_user_playable_force_(.+)_(\d+)_(\d+)$') & admins_filter)
async def handle_demand_user_playable_force(_, call):
    """从用户视图强制标记为可播放（即使币不足）"""
    try:
        request_id = call.matches[0].group(1)
        tg_id = int(call.matches[0].group(2))
        current_page = int(call.matches[0].group(3))
        
        # 获取请求详情
        request = sql_get_request_record_by_download_id(request_id)
        
        if not request:
            await editMessage(call, f"❌ 请求不存在: {request_id}")
            return
        
        # 获取用户信息
        user_info = sql_get_emby(tg=request.tg)
        
        if not user_info:
            await editMessage(call, f"❌ 用户不存在: {request.tg}")
            return
        
        # 扣除JOY币（可能为负）
        current_coins = user_info.iv
        new_coins = current_coins - COIN_DEDUCTION_PLAYABLE
        success = sql_update_emby(Emby.tg == request.tg, iv=new_coins)
        
        if not success:
            await editMessage(call, f"❌ 扣除{sakura_b}失败")
            return
        
        # 更新状态为可播放
        status_success = sql_update_request_status(request_id, 'playable')
        
        if not status_success:
            # 如果状态更新失败，回退币扣除
            sql_update_emby(Emby.tg == request.tg, iv=current_coins)
            await editMessage(call, f"❌ 更新状态失败")
            return
        
        # 发送私聊通知给点播用户
        try:
            private_notification_text = (
                f"📽️ **点播可播放通知**\n\n"
                f"🎬 **影片名称**: {request.request_name}\n"
                f"📺 该影片已标记为可播放状态！\n\n"
                f"💰 **扣费提醒**: 已扣除 {COIN_DEDUCTION_PLAYABLE}{sakura_b}\n"
                f"💳 **当前余额**: {new_coins}{sakura_b}\n\n"
                f"影片已可在Emby中观看，祝您观影愉快😀！"
            )
            
            await bot.send_message(
                chat_id=request.tg,
                text=private_notification_text
            )
            LOGGER.info(f"[Demand] 可播放通知已发送给用户 {request.tg}: {request.request_name}, 扣除{COIN_DEDUCTION_PLAYABLE}{sakura_b}")
        except Exception as private_error:
            LOGGER.error(f"[Demand] 发送可播放通知失败 (用户: {request.tg}): {str(private_error)}")
        
        # 删除请求记录
        delete_success = sql_delete_request_record(request_id)
        
        if not delete_success:
            LOGGER.error(f"[Demand] 删除点播请求记录失败: {request_id}")
        
        # 返回用户视图
        text, keyboard = await format_user_demands(tg_id, current_page)
        await editMessage(call, text, buttons=keyboard)
        await callAnswer(call, f"✅ 已标记为可播放并删除记录，扣除{COIN_DEDUCTION_PLAYABLE}{sakura_b}")
        LOGGER.info(f"管理员 {call.from_user.id} 在用户视图强制标记点播请求为可播放并删除: {request_id}, 用户: {request.tg}, 扣除{COIN_DEDUCTION_PLAYABLE}{sakura_b}")
        
    except Exception as e:
        LOGGER.error(f"强制标记可播放状态失败: {str(e)}")
        await callAnswer(call, "❌ 操作失败", True)


@bot.on_callback_query(filters.regex(r'^demand_user_set_transferred_(.+)_(\d+)_(\d+)$') & admins_filter)
async def handle_demand_user_set_transferred(_, call):
    """处理从用户视图已入库(删除)请求 - 标记为已入库并删除记录"""
    try:
        request_id = call.matches[0].group(1)
        tg_id = int(call.matches[0].group(2))
        current_page = int(call.matches[0].group(3))
        
        # 获取请求详情
        request = sql_get_request_record_by_download_id(request_id)
        
        if not request:
            await editMessage(call, f"❌ 请求不存在: {request_id}")
            return
        
        # 发送私聊通知给点播用户
        try:
            private_notification_text = (
                f"🎉 **ME点播入库通知**\n\n"
                f"🎬 **影片名称**: {request.request_name}\n"
                f"📺 影片已可在Emby中观看！\n\n"
                f"祝您观影愉快😀！"
            )
            
            await bot.send_message(
                chat_id=request.tg,
                text=private_notification_text
            )
            LOGGER.info(f"[Demand] 私聊通知已发送给用户 {request.tg}: {request.request_name}")
        except Exception as private_error:
            LOGGER.error(f"[Demand] 发送私聊通知失败 (用户: {request.tg}): {str(private_error)}")
        
        # 删除请求记录
        success = sql_delete_request_record(request_id)
        
        if success:
            # 返回用户视图
            text, keyboard = await format_user_demands(tg_id, current_page)
            await editMessage(call, text, buttons=keyboard)
            await callAnswer(call, "✅ 已标记为已入库并删除记录")
            LOGGER.info(f"管理员 {call.from_user.id} 在用户视图标记点播请求为已入库并删除: {request_id}")
        else:
            await editMessage(call, f"❌ 删除失败，请求ID不存在: {request_id}")
            
    except Exception as e:
        LOGGER.error(f"处理用户视图已入库(删除)操作失败: {str(e)}")
        await callAnswer(call, "❌ 操作失败", True)


@bot.on_callback_query(filters.regex(r'^demand_user_delete_confirm_(.+)_(\d+)_(\d+)$') & admins_filter)
async def handle_demand_user_delete_confirm(_, call):
    """处理从用户视图删除确认请求"""
    try:
        request_id = call.matches[0].group(1)
        tg_id = int(call.matches[0].group(2))
        current_page = int(call.matches[0].group(3))
        
        # 获取请求详情以显示确认信息
        request = sql_get_request_record_by_download_id(request_id)
        
        if not request:
            await editMessage(call, f"❌ 请求不存在: {request_id}")
            return
        
        # 显示删除确认界面
        confirm_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🗑️ 确认删除", callback_data=f"demand_user_delete_execute_{request_id}_{tg_id}_{current_page}")
            ],
            [
                InlineKeyboardButton("❌ 取消", callback_data=f"demand_user_edit_cancel_{tg_id}_{current_page}")
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
        LOGGER.error(f"处理用户视图删除确认失败: {str(e)}")
        await callAnswer(call, "❌ 删除确认失败", True)


@bot.on_callback_query(filters.regex(r'^demand_user_delete_execute_(.+)_(\d+)_(\d+)$') & admins_filter)
async def handle_demand_user_delete_execute(_, call):
    """执行从用户视图删除操作"""
    try:
        request_id = call.matches[0].group(1)
        tg_id = int(call.matches[0].group(2))
        current_page = int(call.matches[0].group(3))
        
        # 执行删除
        success = sql_delete_request_record(request_id)
        
        if success:
            # 返回用户视图
            text, keyboard = await format_user_demands(tg_id, current_page)
            await editMessage(call, text, buttons=keyboard)
            await callAnswer(call, "✅ 删除成功")
            LOGGER.info(f"管理员 {call.from_user.id} 在用户视图删除点播请求: {request_id}")
        else:
            await editMessage(call, f"❌ 删除失败，请求ID不存在: {request_id}")
            
    except Exception as e:
        LOGGER.error(f"执行用户视图删除操作失败: {str(e)}")
        await callAnswer(call, "❌ 删除失败", True)


@bot.on_callback_query(filters.regex(r'^demand_user_edit_cancel_(\d+)_(\d+)$') & admins_filter)
async def handle_demand_user_edit_cancel(_, call):
    """处理从用户视图状态编辑取消请求"""
    try:
        tg_id = int(call.matches[0].group(1))
        current_page = int(call.matches[0].group(2))
        
        text, keyboard = await format_user_demands(tg_id, current_page)
        await editMessage(call, text, buttons=keyboard)
        await callAnswer(call, "已取消编辑")
        
    except Exception as e:
        LOGGER.error(f"处理用户视图编辑取消失败: {str(e)}")
        await callAnswer(call, "❌ 取消失败", True)


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
            text, keyboard = await format_demand_records(1, "all")
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
        
        # 发送私聊通知给点播用户
        try:
            from bot import bot
            
            private_notification_text = (
                f"🎉 **ME点播入库通知**\n\n"
                f"🎬 **影片名称**: {request.request_name}\n"
                f"📺 影片已可在Emby中观看！\n\n"
                f"祝您观影愉快😀！"
            )
            
            await bot.send_message(
                chat_id=request.tg,
                text=private_notification_text
            )
            LOGGER.info(f"[Demand] 私聊通知已发送给用户 {request.tg}: {request.request_name}")
        except Exception as private_error:
            LOGGER.error(f"[Demand] 发送私聊通知失败 (用户: {request.tg}): {str(private_error)}")
        
        # 删除请求记录
        success = sql_delete_request_record(request_id)
        
        if success:
            # 返回主界面
            text, keyboard = await format_demand_records(1, "all")
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
            text, keyboard = await format_demand_records(1, "all")
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
        text, keyboard = await format_demand_records(1, "all")
        await editMessage(call, text, buttons=keyboard)
        await callAnswer(call, "已取消编辑")
        
    except Exception as e:
        LOGGER.error(f"处理编辑取消失败: {str(e)}")
        await callAnswer(call, "❌ 取消失败", True)


# Aliases for backward compatibility with imports
demand_page_callback = handle_demand_page
demand_filter_callback = handle_demand_filter
demand_refresh_callback = handle_demand_refresh
