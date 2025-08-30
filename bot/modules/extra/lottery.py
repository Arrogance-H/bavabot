"""
lottery - 抽奖功能模块

Author: AI Assistant
Date: 2024
"""

import asyncio
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pyrogram import filters
from pyrogram.types import (
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    CallbackQuery,
    Message
)

from bot import bot, prefixes, sakura_b
from bot.func_helper.filters import user_in_group_on_filter
from bot.func_helper.msg_utils import sendMessage, sendPhoto, callAnswer, editMessage
from bot.func_helper.utils import judge_admins, pwd_create
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby

# 存储活跃的抽奖活动
active_lotteries: Dict[str, 'Lottery'] = {}

# 存储抽奖设置会话
lottery_setup_sessions: Dict[int, 'LotterySetup'] = {}


class Prize:
    """奖品类"""
    def __init__(self, name: str, quantity: int = 1):
        self.name = name
        self.quantity = quantity
        self.remaining = quantity


class Lottery:
    """抽奖活动类"""
    def __init__(self, creator_id: int, creator_name: str):
        self.id = None
        self.creator_id = creator_id
        self.creator_name = creator_name
        self.name = "未命名抽奖"
        self.description = ""
        self.image_url = None
        
        # 参与方式配置
        self.keyword = None  # 关键词参与
        self.allow_button = True  # 允许按钮参与
        
        # 开奖方式配置
        self.draw_type = "manual"  # "manual" 或 "auto"
        self.target_participants = 0  # 自动开奖需要的参与人数
        self.draw_time = None  # 手动开奖时间
        
        # 参与条件配置
        self.participation_type = "all"  # "all", "emby", "paid"
        self.entry_fee = 0  # 付费抽奖费用
        
        # 奖品和参与者
        self.prizes: List[Prize] = []
        self.participants: Dict[int, str] = {}  # {user_id: user_name}
        
        self.created_at = datetime.now()
        self.is_active = False
        self.message_id = None
        self.chat_id = None


class LotterySetup:
    """抽奖设置会话类"""
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.lottery = Lottery(user_id, "")
        self.step = "name"  # 当前设置步骤
        self.last_message_id = None


@bot.on_message(filters.command("lottery", prefixes) & filters.private)
async def start_lottery_setup(_, msg: Message):
    """开始抽奖设置"""
    if not judge_admins(msg.from_user.id):
        return await sendMessage(msg, "❌ 只有管理员才能创建抽奖活动")
    
    user_id = msg.from_user.id
    user_name = msg.from_user.first_name or "管理员"
    
    # 创建新的设置会话
    setup = LotterySetup(user_id)
    setup.lottery.creator_name = user_name
    lottery_setup_sessions[user_id] = setup
    
    text = (
        "🎲 **抽奖设置向导**\n\n"
        "请输入抽奖名称："
    )
    
    sent_msg = await sendMessage(msg, text)
    setup.last_message_id = sent_msg.id


@bot.on_message(filters.private & ~filters.command("lottery", prefixes))
async def handle_lottery_setup(_, msg: Message):
    """处理抽奖设置过程中的消息"""
    user_id = msg.from_user.id
    
    if user_id not in lottery_setup_sessions:
        return
    
    setup = lottery_setup_sessions[user_id]
    text = msg.text
    
    if setup.step == "name":
        setup.lottery.name = text
        setup.step = "description"
        await sendMessage(msg, "✅ 抽奖名称已设置\n\n请输入抽奖描述（可选，发送 /skip 跳过）：")
    
    elif setup.step == "description":
        if text != "/skip":
            setup.lottery.description = text
        setup.step = "keyword"
        await sendMessage(msg, "✅ 抽奖描述已设置\n\n请输入参与关键词（可选，发送 /skip 跳过）：")
    
    elif setup.step == "keyword":
        if text != "/skip":
            setup.lottery.keyword = text
        setup.step = "participation_type"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌍 所有人", "lottery_setup_participation_all")],
            [InlineKeyboardButton("🎬 Emby用户", "lottery_setup_participation_emby")],
            [InlineKeyboardButton("💰 付费抽奖", "lottery_setup_participation_paid")]
        ])
        
        await sendMessage(msg, "✅ 参与关键词已设置\n\n请选择参与条件：", buttons=keyboard)
    
    elif setup.step == "entry_fee":
        try:
            fee = int(text)
            if fee < 0:
                return await sendMessage(msg, "❌ 费用不能为负数，请重新输入：")
            setup.lottery.entry_fee = fee
            setup.step = "draw_type"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("👤 手动开奖", "lottery_setup_draw_manual")],
                [InlineKeyboardButton("🤖 自动开奖", "lottery_setup_draw_auto")]
            ])
            
            await sendMessage(msg, f"✅ 参与费用已设置为 {fee} {sakura_b}\n\n请选择开奖方式：", buttons=keyboard)
        except ValueError:
            await sendMessage(msg, "❌ 请输入有效的数字：")
    
    elif setup.step == "target_participants":
        try:
            target = int(text)
            if target < 1:
                return await sendMessage(msg, "❌ 参与人数必须大于0，请重新输入：")
            setup.lottery.target_participants = target
            setup.step = "prizes"
            await sendMessage(msg, "✅ 自动开奖人数已设置\n\n请输入奖品信息，格式：奖品名称 数量\n例如：iPhone 1\n输入 /done 完成设置")
        except ValueError:
            await sendMessage(msg, "❌ 请输入有效的数字：")
    
    elif setup.step == "prizes":
        if text == "/done":
            if not setup.lottery.prizes:
                return await sendMessage(msg, "❌ 至少需要设置一个奖品，请继续输入：")
            await finish_lottery_setup(msg, setup)
        else:
            parts = text.split()
            if len(parts) < 2:
                return await sendMessage(msg, "❌ 格式错误，请使用：奖品名称 数量")
            
            try:
                prize_name = " ".join(parts[:-1])
                quantity = int(parts[-1])
                if quantity < 1:
                    return await sendMessage(msg, "❌ 奖品数量必须大于0")
                
                setup.lottery.prizes.append(Prize(prize_name, quantity))
                await sendMessage(msg, f"✅ 已添加奖品：{prize_name} x{quantity}\n\n继续添加奖品或输入 /done 完成设置")
            except ValueError:
                await sendMessage(msg, "❌ 数量必须是数字，请重新输入：")


@bot.on_callback_query(filters.regex("lottery_setup_"))
async def handle_lottery_setup_callback(_, call: CallbackQuery):
    """处理抽奖设置回调"""
    user_id = call.from_user.id
    
    if user_id not in lottery_setup_sessions:
        return await callAnswer(call, "❌ 设置会话已过期", True)
    
    setup = lottery_setup_sessions[user_id]
    data = call.data
    
    if data == "lottery_setup_participation_all":
        setup.lottery.participation_type = "all"
        setup.step = "draw_type"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("👤 手动开奖", "lottery_setup_draw_manual")],
            [InlineKeyboardButton("🤖 自动开奖", "lottery_setup_draw_auto")]
        ])
        
        await editMessage(call, "✅ 已设置为所有人可参与\n\n请选择开奖方式：", buttons=keyboard)
    
    elif data == "lottery_setup_participation_emby":
        setup.lottery.participation_type = "emby"
        setup.step = "draw_type"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("👤 手动开奖", "lottery_setup_draw_manual")],
            [InlineKeyboardButton("🤖 自动开奖", "lottery_setup_draw_auto")]
        ])
        
        await editMessage(call, "✅ 已设置为仅Emby用户可参与\n\n请选择开奖方式：", buttons=keyboard)
    
    elif data == "lottery_setup_participation_paid":
        setup.lottery.participation_type = "paid"
        setup.step = "entry_fee"
        await editMessage(call, "✅ 已设置为付费抽奖\n\n请输入参与费用（单位：" + sakura_b + "）：")
    
    elif data == "lottery_setup_draw_manual":
        setup.lottery.draw_type = "manual"
        setup.step = "prizes"
        await editMessage(call, "✅ 已设置为手动开奖\n\n请输入奖品信息，格式：奖品名称 数量\n例如：iPhone 1\n输入 /done 完成设置")
    
    elif data == "lottery_setup_draw_auto":
        setup.lottery.draw_type = "auto"
        setup.step = "target_participants"
        await editMessage(call, "✅ 已设置为自动开奖\n\n请输入触发开奖的参与人数：")


async def finish_lottery_setup(msg: Message, setup: LotterySetup):
    """完成抽奖设置并发布"""
    lottery = setup.lottery
    lottery.id = await pwd_create(8)
    lottery.is_active = True
    
    # 保存抽奖
    active_lotteries[lottery.id] = lottery
    
    # 清理设置会话
    del lottery_setup_sessions[msg.from_user.id]
    
    # 生成抽奖信息
    text = format_lottery_message(lottery)
    
    # 生成参与按钮
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 参与抽奖", f"lottery_join_{lottery.id}")],
        [InlineKeyboardButton("📊 查看详情", f"lottery_info_{lottery.id}")],
        [InlineKeyboardButton("🎯 开奖", f"lottery_draw_{lottery.id}")]
    ])
    
    await sendMessage(msg, f"✅ 抽奖创建成功！\n\n{text}", buttons=keyboard)
    await sendMessage(msg, "💡 提示：复制此消息到群组中即可开始抽奖")


def format_lottery_message(lottery: Lottery) -> str:
    """格式化抽奖消息"""
    participation_type_text = {
        "all": "🌍 所有人",
        "emby": "🎬 Emby用户",
        "paid": f"💰 付费（{lottery.entry_fee} {sakura_b}）"
    }
    
    draw_type_text = {
        "manual": "👤 手动开奖",
        "auto": f"🤖 自动开奖（{lottery.target_participants}人）"
    }
    
    prizes_text = "\n".join([f"• {prize.name} x{prize.quantity}" for prize in lottery.prizes])
    
    text = f"""🎲 **{lottery.name}**

📝 {lottery.description}

🎁 **奖品列表：**
{prizes_text}

👥 **参与条件：** {participation_type_text[lottery.participation_type]}
🎯 **开奖方式：** {draw_type_text[lottery.draw_type]}

👨‍💼 **创建者：** {lottery.creator_name}
📅 **创建时间：** {lottery.created_at.strftime('%Y-%m-%d %H:%M:%S')}

💫 **当前参与人数：** {len(lottery.participants)}"""

    if lottery.keyword:
        text += f"\n🔑 **参与关键词：** {lottery.keyword}"
    
    return text


@bot.on_callback_query(filters.regex("lottery_join_"))
async def join_lottery(_, call: CallbackQuery):
    """参与抽奖"""
    lottery_id = call.data.split("_")[-1]
    
    if lottery_id not in active_lotteries:
        return await callAnswer(call, "❌ 抽奖不存在或已结束", True)
    
    lottery = active_lotteries[lottery_id]
    user_id = call.from_user.id
    user_name = call.from_user.first_name or "匿名用户"
    
    # 检查是否已参与
    if user_id in lottery.participants:
        return await callAnswer(call, "❌ 您已经参与过此抽奖了", True)
    
    # 检查参与条件
    if lottery.participation_type == "emby":
        e = sql_get_emby(tg=user_id)
        if not e:
            return await callAnswer(call, "❌ 您需要有Emby账号才能参与此抽奖", True)
    
    elif lottery.participation_type == "paid":
        e = sql_get_emby(tg=user_id)
        if not e or e.iv < lottery.entry_fee:
            return await callAnswer(call, f"❌ 余额不足，需要 {lottery.entry_fee} {sakura_b}", True)
        
        # 扣除费用
        sql_update_emby(sql_get_emby(tg=user_id).tg == user_id, iv=e.iv - lottery.entry_fee)
    
    # 添加参与者
    lottery.participants[user_id] = user_name
    
    await callAnswer(call, f"✅ 成功参与抽奖！当前参与人数：{len(lottery.participants)}", True)
    
    # 检查是否需要自动开奖
    if (lottery.draw_type == "auto" and 
        len(lottery.participants) >= lottery.target_participants):
        await auto_draw_lottery(lottery, call.message.chat.id, call.message.id)
    else:
        # 更新消息
        text = format_lottery_message(lottery)
        await editMessage(call, text)


@bot.on_callback_query(filters.regex("lottery_info_"))
async def lottery_info(_, call: CallbackQuery):
    """查看抽奖详情"""
    lottery_id = call.data.split("_")[-1]
    
    if lottery_id not in active_lotteries:
        return await callAnswer(call, "❌ 抽奖不存在或已结束", True)
    
    lottery = active_lotteries[lottery_id]
    
    participants_text = "\n".join([f"• {name}" for name in lottery.participants.values()])
    if not participants_text:
        participants_text = "暂无参与者"
    
    text = f"""📊 **抽奖详情**

🎲 **名称：** {lottery.name}
👥 **参与者列表：**
{participants_text}

📈 **当前参与人数：** {len(lottery.participants)}
🎁 **奖品总数：** {sum(prize.quantity for prize in lottery.prizes)}"""
    
    await callAnswer(call, text, True)


@bot.on_callback_query(filters.regex("lottery_draw_"))
async def manual_draw_lottery(_, call: CallbackQuery):
    """手动开奖"""
    lottery_id = call.data.split("_")[-1]
    
    if lottery_id not in active_lotteries:
        return await callAnswer(call, "❌ 抽奖不存在或已结束", True)
    
    lottery = active_lotteries[lottery_id]
    
    # 检查权限
    if call.from_user.id != lottery.creator_id and not judge_admins(call.from_user.id):
        return await callAnswer(call, "❌ 只有创建者或管理员才能开奖", True)
    
    if not lottery.participants:
        return await callAnswer(call, "❌ 没有参与者，无法开奖", True)
    
    await draw_lottery(lottery, call.message.chat.id, call.message.id)


async def auto_draw_lottery(lottery: Lottery, chat_id: int, message_id: int):
    """自动开奖"""
    await draw_lottery(lottery, chat_id, message_id)


async def draw_lottery(lottery: Lottery, chat_id: int, message_id: int):
    """执行开奖"""
    if not lottery.participants:
        return
    
    winners = {}
    participant_list = list(lottery.participants.items())
    
    # 为每个奖品随机选择获奖者
    for prize in lottery.prizes:
        for _ in range(min(prize.quantity, len(participant_list))):
            if not participant_list:
                break
            
            winner_id, winner_name = random.choice(participant_list)
            participant_list.remove((winner_id, winner_name))
            
            if prize.name not in winners:
                winners[prize.name] = []
            winners[prize.name].append(winner_name)
    
    # 生成开奖结果
    result_text = f"""🎉 **{lottery.name} - 开奖结果**

🎊 恭喜以下获奖者：

"""
    
    for prize_name, winner_list in winners.items():
        result_text += f"🏆 **{prize_name}**\n"
        for winner in winner_list:
            result_text += f"    • {winner}\n"
        result_text += "\n"
    
    result_text += f"📊 **本次抽奖统计：**\n"
    result_text += f"   参与人数：{len(lottery.participants)}\n"
    result_text += f"   获奖人数：{sum(len(w) for w in winners.values())}\n"
    result_text += f"   创建者：{lottery.creator_name}"
    
    # 移除抽奖
    del active_lotteries[lottery.id]
    
    # 发送结果
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=result_text
        )
    except Exception:
        await bot.send_message(chat_id, result_text)


# 关键词参与抽奖
@bot.on_message(filters.text & filters.group & user_in_group_on_filter)
async def keyword_lottery_participation(_, msg: Message):
    """通过关键词参与抽奖"""
    if not msg.text:
        return
    
    text = msg.text.strip()
    user_id = msg.from_user.id
    user_name = msg.from_user.first_name or "匿名用户"
    
    # 检查是否有匹配的抽奖关键词
    for lottery_id, lottery in active_lotteries.items():
        if lottery.keyword and text == lottery.keyword:
            # 检查是否已参与
            if user_id in lottery.participants:
                continue
            
            # 检查参与条件
            if lottery.participation_type == "emby":
                e = sql_get_emby(tg=user_id)
                if not e:
                    await msg.reply("❌ 您需要有Emby账号才能参与此抽奖")
                    continue
            
            elif lottery.participation_type == "paid":
                e = sql_get_emby(tg=user_id)
                if not e or e.iv < lottery.entry_fee:
                    await msg.reply(f"❌ 余额不足，需要 {lottery.entry_fee} {sakura_b}")
                    continue
                
                # 扣除费用
                sql_update_emby(sql_get_emby(tg=user_id).tg == user_id, iv=e.iv - lottery.entry_fee)
            
            # 添加参与者
            lottery.participants[user_id] = user_name
            
            await msg.reply(f"✅ 成功参与抽奖「{lottery.name}」！当前参与人数：{len(lottery.participants)}")
            
            # 检查是否需要自动开奖
            if (lottery.draw_type == "auto" and 
                len(lottery.participants) >= lottery.target_participants):
                await auto_draw_lottery(lottery, msg.chat.id, msg.id)
            
            break