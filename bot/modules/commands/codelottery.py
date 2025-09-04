"""
抽奖系统命令 (CodeLottery System)
"""
import random
import datetime
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import bot, prefixes, sakura_b, LOGGER, config
from bot.func_helper.filters import user_in_group_on_filter, admins_filter
from bot.func_helper.msg_utils import sendMessage, deleteMessage
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby
from bot.sql_helper.sql_codelottery import (
    sql_get_codelottery_user,
    sql_create_codelottery_user,
    sql_get_active_lottery_round,
    sql_create_lottery_round,
    sql_join_lottery_round,
    sql_get_lottery_participants,
    sql_complete_lottery_round,
    sql_get_lottery_statistics,
    sql_get_user_in_round
)


@bot.on_message(filters.command('codelottery_start', prefixes) & admins_filter)
async def start_codelottery_command(_, msg):
    """管理员开启抽奖命令"""
    await deleteMessage(msg)
    
    # 检查抽奖系统是否开启
    if not config.code_lottery.status:
        return await sendMessage(msg, "❌ 抽奖系统未开启，请在配置文件中开启", timer=30)
    
    # 检查是否已有活跃的抽奖
    active_round = sql_get_active_lottery_round()
    if active_round:
        return await sendMessage(msg, f"❌ 已有进行中的抽奖：第{active_round.round_number}次抽奖", timer=30)
    
    # 获取下一个轮次号
    stats = sql_get_lottery_statistics()
    next_round = (stats['total_rounds'] if stats else 0) + 1
    
    # 创建新的抽奖轮次
    new_round = sql_create_lottery_round(
        round_number=next_round,
        lottery_name=config.code_lottery.lottery_name,
        duration_minutes=config.code_lottery.duration_minutes,
        entry_fee=config.code_lottery.entry_fee,
        winner_count=config.code_lottery.winner_count,
        created_by=msg.from_user.id
    )
    
    if not new_round:
        return await sendMessage(msg, "❌ 创建抽奖失败，请稍后重试", timer=30)
    
    # 创建参与按钮
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 参与抽奖", callback_data=f"join_codelottery_{new_round.id}")]
    ])
    
    # 发送抽奖信息
    lottery_msg = (
        f"🎉 **{config.code_lottery.lottery_name}** 🎉\n\n"
        f"📅 第 **{next_round}** 次开启抽奖\n"
        f"⏰ 抽奖时间：**{config.code_lottery.duration_minutes}** 分钟\n"
        f"💰 参与费用：**{config.code_lottery.entry_fee}** {sakura_b}\n"
        f"🏆 获奖人数：**{config.code_lottery.winner_count}** 人\n"
        f"🔑 参与条件：仅限未注册用户\n\n"
        f"📊 当前参与人数：**0** 人\n"
        f"⏱️ 结束时间：**{new_round.end_time.strftime('%H:%M:%S')}**\n\n"
        f"💡 **重要提示**：\n"
        f"• 每人只能参与一次\n"
        f"• 参与费用将自动扣除\n"
        f"• 累计参与{config.code_lottery.guaranteed_win_count}次后必定中奖\n"
        f"• 时间到期后自动开奖"
    )
    
    await sendMessage(msg, lottery_msg, reply_markup=keyboard, timer=0)
    LOGGER.info(f"管理员{msg.from_user.id}开启第{next_round}次抽奖，持续{config.code_lottery.duration_minutes}分钟")


@bot.on_callback_query(filters.regex(r'^join_codelottery_(\d+)$'))
async def join_codelottery_callback(_, callback_query):
    """用户参与抽奖回调"""
    await callback_query.answer()
    
    round_id = int(callback_query.matches[0].group(1))
    user_id = callback_query.from_user.id
    nickname = callback_query.from_user.first_name or f"用户{user_id}"
    
    # 检查抽奖系统是否开启
    if not config.code_lottery.status:
        return await callback_query.edit_message_text("❌ 抽奖系统已关闭")
    
    # 获取用户信息
    user = sql_get_emby(user_id)
    if not user:
        return await callback_query.edit_message_text("❌ 您还未注册，请先注册后再参与抽奖")
    
    # 检查用户等级 - 只允许lv='c'的用户参与
    if user.lv != 'c':
        level_names = {'a': '白名单用户', 'b': '普通用户', 'd': '未注册用户'}
        level_name = level_names.get(user.lv, '未知等级用户')
        return await callback_query.edit_message_text(f"⚠️ 您已有账号！")
    
    # 检查用户余额
    if user.iv < config.code_lottery.entry_fee:
        return await callback_query.edit_message_text(
            f"❌ 余额不足，需要 {config.code_lottery.entry_fee}{sakura_b}\n"
            f"您当前余额：{user.iv}{sakura_b}"
        )
    
    # 获取或创建用户抽奖记录
    lottery_user = sql_get_codelottery_user(user_id)
    if not lottery_user:
        lottery_user = sql_create_codelottery_user(user_id)
    
    # 检查保底中奖条件
    guaranteed_win = lottery_user and lottery_user.total_participations >= config.code_lottery.guaranteed_win_count - 1
    
    # 参与抽奖
    participant, result_msg = sql_join_lottery_round(round_id, user_id, nickname)
    
    if not participant:
        return await callback_query.edit_message_text(f"❌ {result_msg}")
    
    # 扣除参与费用
    sql_update_emby(Emby.tg == user_id, iv=user.iv - config.code_lottery.entry_fee)
    
    # 获取当前参与人数和轮次信息
    participants = sql_get_lottery_participants(round_id)
    current_count = len(participants)
    round_obj = sql_get_active_lottery_round()
    
    if round_obj:
        # 计算剩余时间
        import datetime
        now = datetime.datetime.now()
        if now < round_obj.end_time:
            remaining_time = round_obj.end_time - now
            remaining_minutes = int(remaining_time.total_seconds() // 60)
            remaining_seconds = int(remaining_time.total_seconds() % 60)
            time_remaining = f"{remaining_minutes}分{remaining_seconds}秒"
        else:
            time_remaining = "已结束"
        
        updated_msg = (
            f"🎉 **{round_obj.lottery_name}** 🎉\n\n"
            f"📅 第 **{round_obj.round_number}** 次开启抽奖\n"
            f"⏰ 抽奖时间：**{round_obj.duration_minutes}** 分钟\n"
            f"💰 参与费用：**{round_obj.entry_fee}** {sakura_b}\n"
            f"🏆 获奖人数：**{round_obj.winner_count}** 人\n"
            f"🔑 参与条件：仅限未注册用户\n\n"
            f"📊 当前参与人数：**{current_count}** 人\n"
            f"⏱️ 剩余时间：**{time_remaining}**\n\n"
            f"💡 **重要提示**：\n"
            f"• 每人只能参与一次\n"
            f"• 参与费用将自动扣除\n"
            f"• 累计参与{config.code_lottery.guaranteed_win_count}次后必定中奖\n"
            f"• 时间到期后自动开奖"
        )
        
        # 如果抽奖还没结束，继续显示参与按钮
        if now < round_obj.end_time:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎲 参与抽奖", callback_data=f"join_codelottery_{round_id}")]
            ])
            await callback_query.edit_message_text(updated_msg, reply_markup=keyboard)
        else:
            await callback_query.edit_message_text(updated_msg + "\n\n⏰ **抽奖已结束，等待开奖中...**")
    
    # 私信通知参与者
    participation_msg = (
        f"✅ **参与抽奖成功** ✅\n\n"
        f"🎲 抽奖名称：{round_obj.lottery_name if round_obj else '抽奖'}\n"
        f"📅 轮次：第{round_obj.round_number if round_obj else 'N'}次\n"
        f"💰 扣除费用：{config.code_lottery.entry_fee}{sakura_b}\n"
        f"💸 当前余额：{user.iv - config.code_lottery.entry_fee}{sakura_b}\n"
        f"📊 您的累计参与次数：{lottery_user.total_participations if lottery_user else 1}\n\n"
    )
    
    if guaranteed_win:
        participation_msg += "🎊 **恭喜！您已达到保底条件，本次必定中奖！**"
    
    try:
        await bot.send_message(user_id, participation_msg)
    except:
        pass  # 用户可能没有私聊机器人
    
    LOGGER.info(f"用户{user_id}参与第{round_id}轮抽奖，当前人数：{current_count}")


@bot.on_message(filters.command('codelottery_stop', prefixes) & admins_filter)
async def stop_codelottery_command(_, msg):
    """管理员停止抽奖命令"""
    await deleteMessage(msg)
    
    active_round = sql_get_active_lottery_round()
    if not active_round:
        return await sendMessage(msg, "❌ 当前没有进行中的抽奖", timer=30)
    
    # 获取参与者列表
    participants = sql_get_lottery_participants(active_round.id)
    
    if len(participants) == 0:
        # 没有参与者，直接取消
        sql_complete_lottery_round(active_round.id, [])
        return await sendMessage(msg, f"✅ 已取消第{active_round.round_number}次抽奖（无参与者）", timer=30)
    else:
        return await sendMessage(msg, 
                                f"❌ 第{active_round.round_number}次抽奖已有{len(participants)}人参与，无法取消\n"
                                f"请等待满员自动开奖或联系技术人员处理", timer=30)


@bot.on_message(filters.command('codelottery_stats', prefixes) & user_in_group_on_filter)
async def codelottery_stats_command(_, msg):
    """查看抽奖统计信息"""
    await deleteMessage(msg)
    
    # 获取用户信息
    user = sql_get_emby(msg.from_user.id)
    if not user:
        return await sendMessage(msg, "❌ 您还未注册", timer=30)
    
    # 获取个人抽奖记录
    personal_record = sql_get_codelottery_user(msg.from_user.id)
    
    # 获取全局统计
    global_stats = sql_get_lottery_statistics()
    
    if not global_stats:
        return await sendMessage(msg, "❌ 无法获取统计信息", timer=30)
    
    # 构建统计信息
    stats_msg = "📊 **抽奖系统统计** 📊\n\n"
    
    # 个人统计
    if personal_record:
        personal_win_rate = round(personal_record.total_wins / max(personal_record.total_participations, 1) * 100, 2)
        guaranteed_progress = personal_record.total_participations % config.code_lottery.guaranteed_win_count
        next_guaranteed = config.code_lottery.guaranteed_win_count - guaranteed_progress
        
        stats_msg += (
            f"👤 **您的统计**：\n"
            f"   • 总参与次数：{personal_record.total_participations}\n"
            f"   • 距离保底还需：{next_guaranteed}次\n\n"
        )
    else:
        stats_msg += "👤 **您的统计**：尚未参与抽奖\n\n"
    
    # 全局统计
    active_round = global_stats.get('active_round')
    if active_round:
        participants = sql_get_lottery_participants(active_round.id)
        import datetime
        now = datetime.datetime.now()
        if now < active_round.end_time:
            remaining_time = active_round.end_time - now
            remaining_minutes = int(remaining_time.total_seconds() // 60)
            remaining_seconds = int(remaining_time.total_seconds() % 60)
            time_remaining = f"{remaining_minutes}分{remaining_seconds}秒"
        else:
            time_remaining = "已结束"
        
        stats_msg += (
            f"🎲 **当前抽奖**：第{active_round.round_number}次\n"
            f"   • 参与人数：{len(participants)}人\n"
            f"   • 剩余时间：{time_remaining}\n"
            f"   • 参与费用：{active_round.entry_fee}{sakura_b}\n\n"
        )
    
    stats_msg += (
        f"🌍 **全局统计**：\n"
        f"   • 参与用户数：{global_stats['total_users']}\n"
        f"   • 总抽奖轮次：{global_stats['total_rounds']}\n"
        f"   • 总参与次数：{global_stats['total_participations']}\n"
        f"   • 总获奖次数：{global_stats['total_wins']}\n\n"
        f"ℹ️ **规则提醒**：\n"
        f"   • 仅限未注册用户参与\n"
        f"   • 参与费用：{config.code_lottery.entry_fee}{sakura_b}\n"
        f"   • 累计参与{config.code_lottery.guaranteed_win_count}次后必定中奖\n"
        f"   • 每轮抽奖每人只能参与一次"
    )
    
    await sendMessage(msg, stats_msg, timer=90)