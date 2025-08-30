"""
抽奖系统

实现抽奖功能，包括：
1. 关键字参与和按钮参与两种模式
2. 指定时间开奖和达到人数开奖
3. 付费参与、仅emby用户参与、所有人参与三种条件
4. 随机抽取获奖者，每人只能获奖一次
"""

import asyncio
import random
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot import bot, prefixes, lottery, sakura_b, LOGGER
from bot.func_helper.filters import user_in_group_on_filter, admins_on_filter
from bot.func_helper.msg_utils import sendMessage, callAnswer, editMessage
from bot.func_helper.utils import judge_admins
from bot.sql_helper.sql_lottery import (
    sql_create_lottery, sql_add_lottery_prize, sql_join_lottery,
    sql_get_lottery_by_id, sql_get_active_lotteries, sql_get_lottery_participants,
    sql_get_lottery_prizes, sql_update_lottery_status, sql_set_lottery_winners,
    sql_update_lottery_message, sql_count_lottery_participants
)
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby


# 内存中存储活跃的抽奖
active_lotteries = {}


class LotteryManager:
    """抽奖管理器"""
    
    @staticmethod
    async def create_lottery_message(lottery_id: int) -> str:
        """创建抽奖消息文本"""
        lottery = sql_get_lottery_by_id(lottery_id)
        if not lottery:
            return "抽奖不存在"
            
        prizes = sql_get_lottery_prizes(lottery_id)
        participants_count = sql_count_lottery_participants(lottery_id)
        
        # 构建奖品信息
        prize_text = ""
        for prize in prizes:
            prize_text += f"🎁 {prize.name} x{prize.quantity}\n"
        
        # 构建参与条件文本
        participation_text = {
            1: f"💰 付费参与 ({lottery.participation_cost} {sakura_b})",
            2: "🎬 仅限Emby用户",
            3: "🎉 所有人可参与"
        }.get(lottery.participation_type, "未知条件")
        
        # 构建开奖条件文本
        draw_condition = ""
        if lottery.draw_type == 1:
            draw_condition = f"⏰ 开奖时间: {lottery.draw_time.strftime('%Y-%m-%d %H:%M:%S')}"
        else:
            draw_condition = f"👥 达到 {lottery.target_participants} 人自动开奖"
            
        # 参与方式文本
        participation_method = {
            1: f"📝 发送关键字 `{lottery.keyword}` 参与",
            2: "🔘 点击下方按钮参与"
        }.get(lottery.lottery_type, "")
        
        message = f"""
🎊 **{lottery.name}**

{lottery.description or ''}

**奖品信息：**
{prize_text}
**参与条件：** {participation_text}
**参与方式：** {participation_method}
**开奖条件：** {draw_condition}

👥 **当前参与人数：** {participants_count}
⏱️ **状态：** {'进行中' if lottery.status == 'active' else lottery.status}
        """.strip()
        
        return message
    
    @staticmethod
    async def create_lottery_keyboard(lottery_id: int):
        """创建抽奖按钮"""
        lottery = sql_get_lottery_by_id(lottery_id)
        if not lottery or lottery.status != 'active':
            return None
            
        keyboard = []
        
        # 如果是按钮参与模式，添加参与按钮
        if lottery.lottery_type == 2:
            keyboard.append([InlineKeyboardButton("🎯 参与抽奖", callback_data=f"join_lottery-{lottery_id}")])
        
        # 管理员操作按钮
        keyboard.append([
            InlineKeyboardButton("📊 查看参与者", callback_data=f"lottery_participants-{lottery_id}"),
            InlineKeyboardButton("🎲 立即开奖", callback_data=f"draw_lottery-{lottery_id}")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    async def check_participation_eligibility(user_id: int, lottery_id: int) -> tuple[bool, str]:
        """检查用户参与资格"""
        lottery = sql_get_lottery_by_id(lottery_id)
        if not lottery:
            return False, "抽奖不存在"
            
        if lottery.status != 'active':
            return False, "抽奖已结束"
            
        # 检查是否已经参与
        participants = sql_get_lottery_participants(lottery_id)
        if any(p.participant_tg == user_id for p in participants):
            return False, "您已经参与过这个抽奖了"
            
        # 检查参与条件
        if lottery.participation_type == 2:  # 仅emby用户
            emby_user = sql_get_emby(tg=user_id)
            if not emby_user or not emby_user.embyid:
                return False, "仅限Emby用户参与，请先注册Emby账号"
                
        elif lottery.participation_type == 1:  # 付费参与
            emby_user = sql_get_emby(tg=user_id)
            if not emby_user:
                return False, "数据库中没有您的信息，请先私聊bot"
            if emby_user.us < lottery.participation_cost:
                return False, f"余额不足，需要 {lottery.participation_cost} {sakura_b}，您当前有 {emby_user.us} {sakura_b}"
                
        return True, "符合参与条件"
    
    @staticmethod
    async def draw_lottery(lottery_id: int) -> tuple[bool, str, list]:
        """执行抽奖"""
        lottery = sql_get_lottery_by_id(lottery_id)
        if not lottery or lottery.status != 'active':
            return False, "抽奖不存在或已结束", []
            
        participants = sql_get_lottery_participants(lottery_id)
        prizes = sql_get_lottery_prizes(lottery_id)
        
        if not participants:
            return False, "没有参与者", []
            
        if not prizes:
            return False, "没有设置奖品", []
            
        # 计算总奖品数量
        total_prizes = sum(prize.quantity for prize in prizes)
        
        if len(participants) < total_prizes:
            # 参与者不足，所有人都中奖
            winners = []
            participant_list = list(participants)
            
            for prize in prizes:
                for _ in range(min(prize.quantity, len(participant_list))):
                    if participant_list:
                        winner = participant_list.pop(0)
                        winners.append((winner.participant_tg, prize.id))
        else:
            # 随机抽取获奖者
            winners = []
            available_participants = list(participants)
            
            for prize in prizes:
                for _ in range(prize.quantity):
                    if available_participants:
                        winner = random.choice(available_participants)
                        available_participants.remove(winner)
                        winners.append((winner.participant_tg, prize.id))
        
        # 更新数据库
        if sql_set_lottery_winners(lottery_id, winners):
            sql_update_lottery_status(lottery_id, 'finished')
            return True, "开奖成功", winners
        else:
            return False, "开奖失败，数据库错误", []


# 创建抽奖命令 (仅管理员)
@bot.on_message(filters.command("lottery_create", prefixes) & admins_on_filter & filters.private)
async def create_lottery_command(_, msg):
    """创建抽奖命令"""
    if not lottery.status:
        return await sendMessage(msg, "抽奖功能已关闭")
        
    await sendMessage(msg, 
        "🎊 **创建抽奖**\n\n"
        "请按以下格式回复：\n"
        "`抽奖名称|抽奖描述|参与方式|开奖方式|参与条件|参数`\n\n"
        "**参与方式：**\n"
        "1 - 关键字参与 (需要设置关键字)\n"
        "2 - 按钮参与\n\n"
        "**开奖方式：**\n"
        "1 - 指定时间 (格式: YYYY-MM-DD HH:MM)\n"
        "2 - 达到人数 (设置目标人数)\n\n"
        "**参与条件：**\n"
        "1 - 付费参与 (设置费用)\n"
        "2 - 仅Emby用户\n"
        "3 - 所有人\n\n"
        "**示例：**\n"
        "`新年抽奖|祝大家新年快乐|2|1|3|2024-01-01 20:00`\n"
        "`签到抽奖|每日签到奖励|1|2|2|签到,50`\n\n"
        "取消请发送 /cancel"
    )


@bot.on_message(filters.command("lottery_prize", prefixes) & admins_on_filter & filters.private) 
async def add_lottery_prize_command(_, msg):
    """添加抽奖奖品命令"""
    await sendMessage(msg,
        "🎁 **添加奖品**\n\n"
        "请按以下格式回复：\n"
        "`抽奖ID|奖品名称|数量|描述|类型`\n\n"
        "**奖品类型：**\n"
        "virtual - 虚拟奖品\n"
        "physical - 实物奖品\n"
        "coins - 积分奖品\n\n"
        "**示例：**\n"
        "`1|一等奖|1|iPhone 15|physical`\n"
        "`1|积分奖励|5|100积分|coins`\n\n"
        "取消请发送 /cancel"
    )


# 关键字参与抽奖
@bot.on_message(user_in_group_on_filter & filters.group)
async def keyword_lottery_participation(_, msg):
    """关键字参与抽奖"""
    if not lottery.status or not msg.text:
        return
        
    # 检查是否有匹配的关键字抽奖
    active_lotteries_list = sql_get_active_lotteries()
    for lottery_event in active_lotteries_list:
        if (lottery_event.lottery_type == 1 and 
            lottery_event.keyword and 
            lottery_event.keyword in msg.text):
            
            # 检查参与资格
            eligible, reason = await LotteryManager.check_participation_eligibility(
                msg.from_user.id, lottery_event.id
            )
            
            if not eligible:
                return await sendMessage(msg, f"❌ {reason}", timer=10)
            
            # 扣除费用(如果是付费参与)
            if lottery_event.participation_type == 1:
                emby_user = sql_get_emby(tg=msg.from_user.id)
                new_balance = emby_user.us - lottery_event.participation_cost
                sql_update_emby(emby_user.tg, us=new_balance)
            
            # 参与抽奖
            if sql_join_lottery(lottery_event.id, msg.from_user.id, msg.from_user.first_name):
                await sendMessage(msg, f"🎉 恭喜！您已成功参与抽奖 **{lottery_event.name}**", timer=10)
                
                # 检查是否达到自动开奖条件
                if lottery_event.draw_type == 2:
                    participant_count = sql_count_lottery_participants(lottery_event.id)
                    if participant_count >= lottery_event.target_participants:
                        # 自动开奖
                        success, message, winners = await LotteryManager.draw_lottery(lottery_event.id)
                        if success:
                            await announce_lottery_results(lottery_event.id, winners, msg.chat.id)
            else:
                await sendMessage(msg, "❌ 参与失败，请稍后重试", timer=10)
            
            break


# 按钮参与抽奖
@bot.on_callback_query(filters.regex("join_lottery") & user_in_group_on_filter)
async def join_lottery_button(_, call):
    """按钮参与抽奖"""
    if not lottery.status:
        return await callAnswer(call, "抽奖功能已关闭", True)
    
    lottery_id = int(call.data.split("-")[1])
    
    # 检查参与资格
    eligible, reason = await LotteryManager.check_participation_eligibility(
        call.from_user.id, lottery_id
    )
    
    if not eligible:
        return await callAnswer(call, f"❌ {reason}", True)
    
    lottery_event = sql_get_lottery_by_id(lottery_id)
    if not lottery_event:
        return await callAnswer(call, "抽奖不存在", True)
    
    # 扣除费用(如果是付费参与)
    if lottery_event.participation_type == 1:
        emby_user = sql_get_emby(tg=call.from_user.id)
        new_balance = emby_user.us - lottery_event.participation_cost
        sql_update_emby(emby_user.tg, us=new_balance)
    
    # 参与抽奖
    if sql_join_lottery(lottery_id, call.from_user.id, call.from_user.first_name):
        await callAnswer(call, f"🎉 恭喜！您已成功参与抽奖", True)
        
        # 更新抽奖消息
        message_text = await LotteryManager.create_lottery_message(lottery_id)
        keyboard = await LotteryManager.create_lottery_keyboard(lottery_id)
        await editMessage(call, message_text, buttons=keyboard)
        
        # 检查是否达到自动开奖条件
        if lottery_event.draw_type == 2:
            participant_count = sql_count_lottery_participants(lottery_id)
            if participant_count >= lottery_event.target_participants:
                # 自动开奖
                success, message, winners = await LotteryManager.draw_lottery(lottery_id)
                if success:
                    await announce_lottery_results(lottery_id, winners, call.message.chat.id)
    else:
        await callAnswer(call, "❌ 参与失败，请稍后重试", True)


# 查看参与者
@bot.on_callback_query(filters.regex("lottery_participants") & admins_on_filter)
async def view_lottery_participants(_, call):
    """查看抽奖参与者"""
    lottery_id = int(call.data.split("-")[1])
    participants = sql_get_lottery_participants(lottery_id)
    
    if not participants:
        return await callAnswer(call, "暂无参与者", True)
    
    participant_text = "👥 **参与者列表：**\n\n"
    for i, participant in enumerate(participants, 1):
        winner_mark = "🏆" if participant.is_winner else ""
        participant_text += f"{i}. {participant.participant_name} {winner_mark}\n"
    
    await callAnswer(call, participant_text[:200] + "..." if len(participant_text) > 200 else participant_text, True)


# 立即开奖
@bot.on_callback_query(filters.regex("draw_lottery") & admins_on_filter)
async def draw_lottery_button(_, call):
    """立即开奖按钮"""
    lottery_id = int(call.data.split("-")[1])
    
    success, message, winners = await LotteryManager.draw_lottery(lottery_id)
    
    if success:
        await callAnswer(call, "🎊 开奖成功！", True)
        await announce_lottery_results(lottery_id, winners, call.message.chat.id)
        
        # 更新消息
        message_text = await LotteryManager.create_lottery_message(lottery_id)
        await editMessage(call, message_text)
    else:
        await callAnswer(call, f"❌ 开奖失败：{message}", True)


async def announce_lottery_results(lottery_id: int, winners: list, chat_id: int):
    """公布抽奖结果"""
    lottery_event = sql_get_lottery_by_id(lottery_id)
    prizes = sql_get_lottery_prizes(lottery_id)
    participants = sql_get_lottery_participants(lottery_id)
    
    if not lottery_event or not winners:
        return
    
    # 构建获奖者信息
    winner_info = {}
    for participant_tg, prize_id in winners:
        participant = next((p for p in participants if p.participant_tg == participant_tg), None)
        prize = next((p for p in prizes if p.id == prize_id), None)
        
        if participant and prize:
            if prize.name not in winner_info:
                winner_info[prize.name] = []
            winner_info[prize.name].append(participant.participant_name)
    
    # 构建结果消息
    result_text = f"🎊 **{lottery_event.name} 开奖结果**\n\n"
    
    for prize_name, winner_names in winner_info.items():
        result_text += f"🎁 **{prize_name}**\n"
        for name in winner_names:
            result_text += f"🏆 {name}\n"
        result_text += "\n"
    
    result_text += f"🎉 恭喜以上获奖者！\n总参与人数: {len(participants)}"
    
    try:
        await bot.send_message(chat_id, result_text)
    except Exception as e:
        LOGGER.error(f"发送开奖结果失败: {e}")


# 定时检查抽奖状态
async def check_lottery_schedules():
    """检查定时开奖"""
    active_lotteries_list = sql_get_active_lotteries()
    current_time = datetime.now()
    
    for lottery_event in active_lotteries_list:
        if (lottery_event.draw_type == 1 and 
            lottery_event.draw_time and 
            current_time >= lottery_event.draw_time):
            
            # 执行开奖
            success, message, winners = await LotteryManager.draw_lottery(lottery_event.id)
            if success and lottery_event.chat_id:
                await announce_lottery_results(lottery_event.id, winners, lottery_event.chat_id)


# 启动时加载活跃抽奖到内存
async def load_active_lotteries():
    """加载活跃抽奖到内存"""
    try:
        lotteries = sql_get_active_lotteries()
        for lottery_event in lotteries:
            active_lotteries[lottery_event.id] = lottery_event
        LOGGER.info(f"加载了 {len(lotteries)} 个活跃抽奖")
    except Exception as e:
        LOGGER.error(f"加载活跃抽奖失败: {e}")