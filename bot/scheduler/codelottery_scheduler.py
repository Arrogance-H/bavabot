"""
抽奖系统调度器模块
"""
from datetime import datetime
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot import bot, LOGGER, group
from bot.sql_helper.sql_codelottery import (
    sql_get_expired_lotteries,
    sql_draw_lottery,
    sql_get_lottery_participants,
    sql_mark_winner_notified
)


async def auto_draw_expired_lotteries():
    """自动开奖过期的抽奖"""
    try:
        expired_lotteries = sql_get_expired_lotteries()
        
        for lottery in expired_lotteries:
            await process_lottery_draw(lottery)
            
    except Exception as e:
        LOGGER.error(f"【抽奖调度器】自动开奖出错：{e}")


async def process_lottery_draw(lottery):
    """处理单个抽奖的开奖"""
    try:
        # 获取参与者
        participants = sql_get_lottery_participants(lottery.id)
        
        if not participants:
            # 没有参与者，直接结束
            await notify_no_participants(lottery)
            return
        
        # 执行抽奖
        winners = sql_draw_lottery(lottery.id, lottery.lottery_name)
        
        if winners:
            await notify_lottery_results(lottery, participants, winners)
        else:
            await notify_draw_failed(lottery)
            
    except Exception as e:
        LOGGER.error(f"【抽奖调度器】处理抽奖 {lottery.id} 出错：{e}")


async def notify_no_participants(lottery):
    """通知没有参与者的抽奖结果"""
    try:
        message_text = (
            f"🎯 **抽奖结果通知**\n\n"
            f"🎪 抽奖名称：{lottery.lottery_name}\n"
            f"⏰ 开奖时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"👥 参与人数：0\n\n"
            f"😢 很遗憾，本次抽奖没有人参与。"
        )
        
        for group_id in group:
            await bot.send_message(
                chat_id=group_id,
                text=message_text
            )
        
        LOGGER.info(f"【抽奖系统】抽奖 {lottery.lottery_name} 无人参与")
        
    except Exception as e:
        LOGGER.error(f"【抽奖调度器】通知无参与者出错：{e}")


async def notify_lottery_results(lottery, participants, winners):
    """通知抽奖结果"""
    try:
        # 构建结果消息
        result_text = (
            f"🎉 **抽奖结果揭晓！**\n\n"
            f"🎯 抽奖名称：{lottery.lottery_name}\n"
            f"⏰ 开奖时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"👥 参与人数：{len(participants)}\n"
            f"🏆 获奖人数：{len(winners)}\n\n"
            f"🎊 **恭喜以下用户获奖：**\n"
        )
        
        # 添加获奖者信息
        for i, winner in enumerate(winners, 1):
            result_text += f"🥇 第{i}名：[{winner.username}](tg://user?id={winner.tg})\n"
        
        result_text += f"\n📦 奖品：{lottery.lottery_name}\n"
        result_text += "🎈 请获奖者联系管理员领取奖品！"
        
        # 发送到群组
        for group_id in group:
            await bot.send_message(
                chat_id=group_id,
                text=result_text,
                parse_mode="Markdown"
            )
        
        # 私信通知获奖者
        for winner in winners:
            await notify_winner_privately(winner, lottery)
            sql_mark_winner_notified(winner.id)
        
        LOGGER.info(f"【抽奖系统】抽奖 {lottery.lottery_name} 开奖完成，{len(winners)} 人获奖")
        
    except Exception as e:
        LOGGER.error(f"【抽奖调度器】通知抽奖结果出错：{e}")


async def notify_winner_privately(winner, lottery):
    """私信通知获奖者"""
    try:
        winner_text = (
            f"🎉 **恭喜您中奖了！**\n\n"
            f"🎯 抽奖名称：{lottery.lottery_name}\n"
            f"⏰ 开奖时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🎁 奖品：{lottery.lottery_name}\n\n"
            f"📞 请联系管理员领取您的奖品！\n"
            f"⭐ 感谢您的参与，祝您生活愉快！"
        )
        
        try:
            await bot.send_message(
                chat_id=winner.tg,
                text=winner_text
            )
        except Exception:
            # 如果无法私信，可能是用户没有启动机器人
            LOGGER.warning(f"无法私信获奖者 {winner.tg}")
            
    except Exception as e:
        LOGGER.error(f"【抽奖调度器】私信通知获奖者出错：{e}")


async def notify_draw_failed(lottery):
    """通知开奖失败"""
    try:
        message_text = (
            f"❌ **抽奖开奖失败**\n\n"
            f"🎯 抽奖名称：{lottery.lottery_name}\n"
            f"⏰ 时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"⚠️ 开奖过程中发生错误，请联系管理员处理。"
        )
        
        for group_id in group:
            await bot.send_message(
                chat_id=group_id,
                text=message_text
            )
        
        LOGGER.error(f"【抽奖系统】抽奖 {lottery.lottery_name} 开奖失败")
        
    except Exception as e:
        LOGGER.error(f"【抽奖调度器】通知开奖失败出错：{e}")