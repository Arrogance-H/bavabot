"""
抽奖系统命令处理模块
"""
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot import bot, LOGGER, config, group, save_config
from bot.func_helper.filters import admins_on_filter, user_in_group_filter
from bot.func_helper.msg_utils import callAnswer, editMessage, sendMessage
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby
from bot.sql_helper.sql_codelottery import (
    sql_create_lottery_round,
    sql_get_active_lottery,
    sql_join_lottery,
    sql_cancel_lottery,
    sql_get_lottery_stats,
    sql_get_lottery_participants,
    sql_check_database_connection
)


@bot.on_message(filters.command('codelottery_start') & admins_on_filter)
async def start_codelottery_command(_, message):
    """管理员开启抽奖命令"""
    try:
        # 检查数据库连接
        if not sql_check_database_connection():
            await message.reply(
                '❌ 数据库连接失败，无法创建抽奖\n'
                '💡 请检查数据库服务状态或联系管理员'
            )
            return
        
        # 检查是否已有活跃抽奖
        active_lottery = sql_get_active_lottery()
        if active_lottery:
            await message.reply(
                f'❌ 当前已有活跃抽奖：\n'
                f'🎯 名称：{active_lottery.lottery_name}\n'
                f'⏰ 结束时间：{active_lottery.end_time.strftime("%Y-%m-%d %H:%M:%S")}\n'
                f'请先停止当前抽奖或等待其结束。'
            )
            return
        
        # 解析命令参数
        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        
        # 设置抽奖参数
        lottery_name = args[0] if args else config.code_lottery.lottery_name
        duration_minutes = int(args[1]) if len(args) > 1 and args[1].isdigit() else config.code_lottery.duration_minutes
        entry_fee = config.code_lottery.entry_fee
        winner_count = config.code_lottery.winner_count
        
        # 创建抽奖轮次
        round_id = sql_create_lottery_round(
            creator_tg=message.from_user.id,
            lottery_name=lottery_name,
            duration_minutes=duration_minutes,
            entry_fee=entry_fee,
            winner_count=winner_count
        )
        
        if not round_id:
            await message.reply(
                '❌ 创建抽奖失败，请稍后重试\n'
                '💡 可能的原因：\n'
                '• 数据库连接问题\n'
                '• 数据库表结构问题\n'
                '• 数据库权限不足\n'
                '请检查日志获取详细错误信息'
            )
            return
        
        # 发送抽奖通知
        lottery_text = (
            f"🎉 **新抽奖活动开启！**\n\n"
            f"🎯 **奖品名称：** {lottery_name}\n"
            f"💰 **参与费用：** {entry_fee} JOY币\n"
            f"🏆 **获奖人数：** {winner_count} 人\n"
            f"⏰ **抽奖时长：** {duration_minutes} 分钟\n"
            f"💡 **保底机制：** 连续参与 {config.code_lottery.guaranteed_win_count} 次未中奖必中下次\n\n"
            f"👇 点击下方按钮参与抽奖！"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎯 参与抽奖", callback_data=f"join_lottery_{round_id}")],
            [InlineKeyboardButton("📊 查看统计", callback_data=f"lottery_stats_{round_id}")]
        ])
        
        # 发送到群组
        for group_id in group:
            await bot.send_message(
                chat_id=group_id,
                text=lottery_text,
                reply_markup=keyboard
            )
        
        await message.reply(f'✅ 抽奖已成功创建！轮次ID: {round_id}')
        LOGGER.info(f"【抽奖系统】管理员 {message.from_user.first_name} 创建了抽奖：{lottery_name}")
        
    except Exception as e:
        await message.reply(f'❌ 创建抽奖时出错：{str(e)}')
        LOGGER.error(f"【抽奖系统】创建抽奖出错：{e}")


@bot.on_message(filters.command('codelottery_stop') & admins_on_filter)
async def stop_codelottery_command(_, message):
    """管理员停止抽奖命令"""
    try:
        active_lottery = sql_get_active_lottery()
        if not active_lottery:
            await message.reply('❌ 当前没有活跃的抽奖。')
            return
        
        # 取消抽奖
        if sql_cancel_lottery(active_lottery.id):
            await message.reply(
                f'✅ 抽奖已停止\n'
                f'🎯 名称：{active_lottery.lottery_name}\n'
                f'⏰ 创建时间：{active_lottery.start_time.strftime("%Y-%m-%d %H:%M:%S")}'
            )
            
            # 通知群组
            for group_id in group:
                await bot.send_message(
                    chat_id=group_id,
                    text=f"📢 抽奖活动「{active_lottery.lottery_name}」已被管理员停止。"
                )
            
            LOGGER.info(f"【抽奖系统】管理员 {message.from_user.first_name} 停止了抽奖：{active_lottery.lottery_name}")
        else:
            await message.reply('❌ 停止抽奖失败。')
            
    except Exception as e:
        await message.reply(f'❌ 停止抽奖时出错：{str(e)}')
        LOGGER.error(f"【抽奖系统】停止抽奖出错：{e}")


@bot.on_message(filters.command('codelottery_draw') & admins_on_filter)
async def manual_codelottery_draw_command(_, message):
    """管理员手动开奖命令"""
    try:
        active_lottery = sql_get_active_lottery()
        if not active_lottery:
            await message.reply('❌ 当前没有活跃的抽奖。')
            return
        
        # 获取参与者数量
        participants = sql_get_lottery_participants(active_lottery.id)
        
        await message.reply(
            f'🎯 准备开奖...\n'
            f'抽奖名称：{active_lottery.lottery_name}\n'
            f'参与人数：{len(participants)}\n'
            f'开奖人数：{active_lottery.winner_count}'
        )
        
        # 执行开奖
        from bot.scheduler.codelottery_scheduler import process_lottery_draw
        await process_lottery_draw(active_lottery)
        
        await message.reply(
            f'✅ 手动开奖完成！\n'
            f'🎯 抽奖名称：{active_lottery.lottery_name}\n'
            f'👥 参与人数：{len(participants)}\n'
            f'📢 开奖结果已发送到群组'
        )
        
        LOGGER.info(f"【抽奖系统】管理员 {message.from_user.first_name} 手动开奖：{active_lottery.lottery_name}")
        
    except Exception as e:
        await message.reply(f'❌ 手动开奖时出错：{str(e)}')
        LOGGER.error(f"【抽奖系统】手动开奖出错：{e}")


@bot.on_message(filters.command('codelottery_stats'))
async def codelottery_stats_command(_, message):
    """查看抽奖统计命令"""
    try:
        # 检查数据库连接
        if not sql_check_database_connection():
            await message.reply(
                '❌ 数据库连接失败，无法查询统计信息\n'
                '💡 请检查数据库服务状态或联系管理员'
            )
            return
            
        user_stats = sql_get_lottery_stats(message.from_user.id)
        
        stats_text = (
            f"🎯 **个人抽奖统计**\n\n"
            f"👤 用户：{message.from_user.first_name}\n"
            f"🎫 参与次数：{user_stats['total_participation']}\n"
            f"🎲 保底次数：{user_stats['guaranteed_count']}/{config.code_lottery.guaranteed_win_count}\n\n"
        )
        
        if user_stats['guaranteed_count'] >= 6:
            stats_text += "💡 提示：您的保底次数即将满足，下次参与中奖概率更高！"
        elif user_stats['guaranteed_count'] >= config.code_lottery.guaranteed_win_count:
            stats_text += "🎉 恭喜：您已满足保底条件，下次参与必中！"
        
        await message.reply(stats_text)
        
    except Exception as e:
        await message.reply(f'❌ 查询统计时出错：{str(e)}')
        LOGGER.error(f"【抽奖系统】查询统计出错：{e}")


@bot.on_message(filters.command('codelottery_dbcheck') & admins_on_filter)
async def codelottery_dbcheck_command(_, message):
    """管理员检查抽奖系统数据库状态"""
    try:
        # 检查数据库连接
        db_status = sql_check_database_connection()
        
        if db_status:
            status_text = "✅ 数据库连接正常\n"
            
            # 尝试获取活跃抽奖
            try:
                active_lottery = sql_get_active_lottery()
                if active_lottery:
                    status_text += f"🎯 当前活跃抽奖：{active_lottery.lottery_name}\n"
                else:
                    status_text += "📋 当前无活跃抽奖\n"
            except Exception as e:
                status_text += f"⚠️ 查询活跃抽奖时出错：{str(e)}\n"
            
            # 检查配置
            status_text += (
                f"\n📊 **系统配置**\n"
                f"• 状态：{'启用' if config.code_lottery.status else '禁用'}\n"
                f"• 仅管理员：{'是' if config.code_lottery.admin_only else '否'}\n"
                f"• 参与费用：{config.code_lottery.entry_fee} JOY币\n"
                f"• 保底次数：{config.code_lottery.guaranteed_win_count}\n"
                f"• 默认时长：{config.code_lottery.duration_minutes}分钟\n"
                f"• 获奖人数：{config.code_lottery.winner_count}\n"
            )
        else:
            status_text = (
                "❌ 数据库连接失败\n"
                "💡 可能的原因：\n"
                "• MySQL服务未启动\n"
                "• 数据库配置错误\n"
                "• 网络连接问题\n"
                "• 数据库权限不足\n"
            )
        
        await message.reply(status_text)
        
    except Exception as e:
        await message.reply(f'❌ 检查数据库状态时出错：{str(e)}')
        LOGGER.error(f"【抽奖系统】数据库状态检查出错：{e}")


@bot.on_callback_query(filters.regex(r'join_lottery_(\d+)'))
async def handle_join_lottery(_, call):
    """处理参与抽奖回调"""
    try:
        round_id = int(call.data.split('_')[2])
        user_id = call.from_user.id
        username = call.from_user.first_name or call.from_user.username or "Unknown"
        
        # 检查用户是否在群组中
        if not await user_in_group_filter(_, call):
            await callAnswer(call, '❌ 只有群组成员才能参与抽奖', True)
            return
        
        # 检查抽奖是否仍然活跃
        active_lottery = sql_get_active_lottery()
        if not active_lottery or active_lottery.id != round_id:
            await callAnswer(call, '❌ 该抽奖已结束或不存在', True)
            return
        
        # 检查抽奖是否已过期
        from datetime import datetime
        if active_lottery.end_time <= datetime.now():
            # 抽奖已过期，执行开奖
            from bot.scheduler.codelottery_scheduler import process_lottery_draw
            await process_lottery_draw(active_lottery)
            await callAnswer(call, '⏰ 抽奖时间已截止，已自动开奖', True)
            return
        
        # 检查用户是否在数据库中有记录
        user_info = sql_get_emby(tg=user_id)
        if not user_info:
            await callAnswer(call, '❌ 请先使用 /start 命令与bot互动后再参与抽奖', True)
            return
        
        # 检查用户等级是否为d
        if user_info.lv != 'd':
            await callAnswer(call, '❌ 只有未注册的用户才能参与抽奖', True)
            return
        
        # 检查用户花币是否足够
        if user_info.iv < active_lottery.entry_fee:
            await callAnswer(call, f'❌ JOY币不足，需要 {active_lottery.entry_fee} JOY币参与', True)
            return
        
        # 参与抽奖
        if sql_join_lottery(round_id, user_id, username):
            # 扣除花币
            sql_update_emby(Emby.tg == user_id, iv=user_info.iv - active_lottery.entry_fee)
            
            await callAnswer(call, '🎉 参与抽奖成功！祝您好运！', True)
            LOGGER.info(f"【抽奖系统】用户 {username} ({user_id}) 参与了抽奖 {round_id}")
        else:
            await callAnswer(call, '❌ 您已经参与过此次抽奖了', True)
        
    except Exception as e:
        await callAnswer(call, f'❌ 参与抽奖时出错：{str(e)}', True)
        LOGGER.error(f"【抽奖系统】参与抽奖出错：{e}")


@bot.on_callback_query(filters.regex(r'lottery_stats_(\d+)'))
async def handle_lottery_stats(_, call):
    """处理查看抽奖统计回调"""
    try:
        round_id = int(call.data.split('_')[2])
        
        # 获取当前抽奖信息
        active_lottery = sql_get_active_lottery()
        if not active_lottery or active_lottery.id != round_id:
            await callAnswer(call, '❌ 该抽奖已结束或不存在', True)
            return
        
        # 检查抽奖是否已过期
        from datetime import datetime
        if active_lottery.end_time <= datetime.now():
            # 抽奖已过期，执行开奖
            from bot.scheduler.codelottery_scheduler import process_lottery_draw
            await process_lottery_draw(active_lottery)
            await callAnswer(call, '⏰ 抽奖时间已截止，已自动开奖', True)
            return
        
        # 获取参与者信息
        participants = sql_get_lottery_participants(round_id)
        
        # 获取用户个人统计
        user_stats = sql_get_lottery_stats(call.from_user.id)
        
        stats_text = (
            f"📊 **抽奖统计信息**\n\n"
            f"🎯 抽奖名称：{active_lottery.lottery_name}\n"
            f"👥 参与人数：{len(participants)}\n"
            f"⏰ 结束时间：{active_lottery.end_time.strftime('%H:%M:%S')}\n\n"
            f"👤 **您的统计：**\n"
            f"🎫 参与次数：{user_stats['total_participation']}\n"
            f"🎲 保底次数：{user_stats['guaranteed_count']}/{config.code_lottery.guaranteed_win_count}"
        )
        
        await callAnswer(call, stats_text, True)
        
    except Exception as e:
        await callAnswer(call, f'❌ 查询统计时出错：{str(e)}', True)
        LOGGER.error(f"【抽奖系统】查询统计出错：{e}")
