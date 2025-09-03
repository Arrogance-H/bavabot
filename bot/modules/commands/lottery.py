"""
抽奖系统命令
"""
import random
from pyrogram import filters
from bot import bot, prefixes, sakura_b, LOGGER
from bot.func_helper.filters import user_in_group_on_filter
from bot.func_helper.msg_utils import sendMessage, deleteMessage
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby
from bot.sql_helper.sql_lottery import (
    sql_get_lottery_record, 
    sql_create_lottery_record, 
    sql_update_lottery_participation,
    sql_get_lottery_stats
)


@bot.on_message(filters.command('lottery', prefixes) & user_in_group_on_filter)
async def lottery_command(_, msg):
    """抽奖命令 - 只允许lv='b'的用户参与"""
    await deleteMessage(msg)
    
    # 获取用户信息
    user = sql_get_emby(msg.from_user.id)
    if not user:
        return await sendMessage(msg, "❌ 您还未注册，请先注册后再参与抽奖", timer=30)
    
    # 检查用户等级 - 只允许lv='b'的用户参与
    if user.lv != 'b':
        level_names = {'a': '白名单用户', 'c': '已禁用用户', 'd': '未注册用户'}
        level_name = level_names.get(user.lv, '未知等级用户')
        return await sendMessage(msg, f"❌ 抱歉，只有普通用户(lv=b)可以参与抽奖\n您当前是：{level_name}", timer=30)
    
    # 获取或创建抽奖记录
    lottery_record = sql_get_lottery_record(msg.from_user.id)
    if not lottery_record:
        lottery_record = sql_create_lottery_record(msg.from_user.id)
        if not lottery_record:
            return await sendMessage(msg, "❌ 系统错误，无法参与抽奖", timer=30)
    
    # 检查是否达到保底条件（连续9次未中奖）
    guaranteed_win = lottery_record.consecutive_losses >= 9
    
    # 计算中奖概率
    if guaranteed_win:
        # 保底必中
        won = True
        win_reason = "保底中奖"
    else:
        # 普通概率（30%中奖率）
        won = random.random() < 0.3
        win_reason = "幸运中奖" if won else "运气不佳"
    
    # 中奖奖励
    reward_amount = 0
    if won:
        # 随机奖励金额（50-200樱花币）
        reward_amount = random.randint(50, 200)
        # 更新用户金币
        sql_update_emby(Emby.tg == msg.from_user.id, iv=user.iv + reward_amount)
    
    # 更新抽奖记录
    updated_record = sql_update_lottery_participation(msg.from_user.id, won)
    
    # 构建回复消息
    user_name = msg.from_user.first_name or "用户"
    
    if won:
        result_msg = (
            f"🎉 **恭喜中奖！** 🎉\n\n"
            f"👤 {user_name}\n"
            f"💰 获得奖励：{reward_amount}{sakura_b}\n"
            f"🏆 中奖原因：{win_reason}\n"
            f"📊 您的抽奖统计：\n"
            f"   • 总参与次数：{updated_record.participation_count}\n"
            f"   • 总中奖次数：{updated_record.wins_count}\n"
            f"   • 当前连胜：重置为0\n\n"
            f"💸 当前余额：{user.iv + reward_amount}{sakura_b}"
        )
    else:
        result_msg = (
            f"😔 **很遗憾，未中奖** \n\n"
            f"👤 {user_name}\n"
            f"📊 您的抽奖统计：\n"
            f"   • 总参与次数：{updated_record.participation_count}\n"
            f"   • 总中奖次数：{updated_record.wins_count}\n"
            f"   • 连续未中奖：{updated_record.consecutive_losses}次\n\n"
            f"💡 提示：连续9次未中奖后，第10次将保底中奖！\n"
            f"💸 当前余额：{user.iv}{sakura_b}"
        )
    
    await sendMessage(msg, result_msg, timer=60)
    LOGGER.info(f"抽奖结果 - 用户:{msg.from_user.id} 结果:{'中奖' if won else '未中奖'} 奖励:{reward_amount}")


@bot.on_message(filters.command('lottery_stats', prefixes) & user_in_group_on_filter)
async def lottery_stats_command(_, msg):
    """查看抽奖统计信息"""
    await deleteMessage(msg)
    
    # 获取用户信息
    user = sql_get_emby(msg.from_user.id)
    if not user:
        return await sendMessage(msg, "❌ 您还未注册", timer=30)
    
    # 获取个人抽奖记录
    personal_record = sql_get_lottery_record(msg.from_user.id)
    
    # 获取全局统计
    global_stats = sql_get_lottery_stats()
    
    if not global_stats:
        return await sendMessage(msg, "❌ 无法获取统计信息", timer=30)
    
    # 构建统计信息
    stats_msg = "📊 **抽奖系统统计** 📊\n\n"
    
    # 个人统计
    if personal_record:
        personal_win_rate = round(personal_record.wins_count / max(personal_record.participation_count, 1) * 100, 2)
        stats_msg += (
            f"👤 **您的统计**：\n"
            f"   • 参与次数：{personal_record.participation_count}\n"
            f"   • 中奖次数：{personal_record.wins_count}\n"
            f"   • 中奖率：{personal_win_rate}%\n"
            f"   • 连续未中奖：{personal_record.consecutive_losses}次\n\n"
        )
    else:
        stats_msg += "👤 **您的统计**：尚未参与抽奖\n\n"
    
    # 全局统计
    stats_msg += (
        f"🌍 **全局统计**：\n"
        f"   • 参与用户数：{global_stats['total_participants']}\n"
        f"   • 总抽奖次数：{global_stats['total_participations']}\n"
        f"   • 总中奖次数：{global_stats['total_wins']}\n"
        f"   • 全局中奖率：{global_stats['win_rate']}%\n\n"
        f"ℹ️ **规则提醒**：\n"
        f"   • 只有普通用户(lv=b)可以参与\n"
        f"   • 基础中奖率：30%\n"
        f"   • 连续9次未中奖后，第10次保底中奖"
    )
    
    await sendMessage(msg, stats_msg, timer=90)