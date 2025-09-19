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

from bot import bot, prefixes, sakura_b, group
from bot.func_helper.filters import user_in_group_on_filter
from bot.func_helper.msg_utils import sendMessage, sendPhoto, callAnswer, editMessage
from bot.func_helper.utils import judge_admins, pwd_create
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby

# 存储活跃的抽奖活动
active_lotteries: Dict[str, 'Lottery'] = {}

# 存储抽奖设置会话
lottery_setup_sessions: Dict[int, 'LotterySetup'] = {}


# 自定义过滤器：只处理在抽奖设置会话中的用户消息
async def lottery_setup_filter(_, __, message):
    """只允许正在进行抽奖设置的用户的消息通过"""
    return message.from_user and message.from_user.id in lottery_setup_sessions

lottery_setup_filter = filters.create(lottery_setup_filter)


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
        self.collection_location = ""  # 领奖地点
        
        # 开奖方式配置
        self.draw_type = "manual"  # "manual" 或 "auto"
        self.target_participants = 0  # 自动开奖需要的参与人数
        self.draw_time = None  # 手动开奖时间
        
        # 参与条件配置
        self.participation_type = "all"  # "all", "emby", "d_only"
        self.entry_fee = 0  # 付费抽奖费用
        self.refund_losers = False  # 是否给未中奖者退款50%
        
        # 奖品和参与者
        self.prizes: List[Prize] = []
        self.participants: Dict[int, str] = {}  # {user_id: user_name}
        
        self.created_at = datetime.now()
        self.is_active = False
        self.message_id = None
        self.chat_id = None
        self.group_messages = {}  # {group_id: message_id} 记录在各群组的消息ID


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
        "请输入抽奖名称：\n\n"
        "💡 随时发送 /cancel 可取消设置"
    )
    
    sent_msg = await sendMessage(msg, text)
    if sent_msg and hasattr(sent_msg, 'id'):
        setup.last_message_id = sent_msg.id


@bot.on_message(filters.private & lottery_setup_filter)
async def handle_lottery_setup(_, msg: Message):
    """处理抽奖设置过程中的消息"""
    user_id = msg.from_user.id
    setup = lottery_setup_sessions[user_id]
    text = msg.text or msg.caption or ""
    
    # 检查是否要取消抽奖设置
    if text in ["/cancel", "/取消", "取消"]:
        del lottery_setup_sessions[user_id]
        return await sendMessage(msg, "❌ 抽奖设置已取消")
    
    # 处理图片上传（仅在image步骤）
    if setup.step == "image" and msg.photo:
        # 获取最大尺寸的图片
        photo = msg.photo
        setup.lottery.image_url = photo.file_id  # 使用 file_id 作为图片标识
        
        setup.step = "participation_type"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌍 所有人", "lottery_setup_participation_all")],
            [InlineKeyboardButton("🎬 ME专属", "lottery_setup_participation_emby")],
            [InlineKeyboardButton("🔰 ME补位", "lottery_setup_participation_d_only")]
        ])
        
        return await sendMessage(msg, "✅ 抽奖图片已设置\n\n请选择参与条件：", buttons=keyboard)
    
    
    if setup.step == "name":
        setup.lottery.name = text
        setup.step = "description"
        await sendMessage(msg, "✅ 抽奖名称已设置\n\n请输入抽奖描述（可选，发送 /skip 跳过）：")
    
    elif setup.step == "description":
        if text != "/skip":
            setup.lottery.description = text
        setup.step = "collection_location"
        await sendMessage(msg, "✅ 抽奖描述已设置\n\n请输入领奖地点（可选，发送 /skip 跳过）：")
    
    elif setup.step == "collection_location":
        if text != "/skip":
            setup.lottery.collection_location = text
        setup.step = "image"
        await sendMessage(msg, "✅ 领奖地点已设置\n\n请发送抽奖图片（可发送图片文件或图片URL，发送 /skip 跳过）：")
    
    elif setup.step == "image":
        if text == "/skip":
            setup.lottery.image_url = None
        else:
            # Check if it's a URL
            if text.startswith(('http://', 'https://')):
                setup.lottery.image_url = text
            else:
                return await sendMessage(msg, "❌ 请发送有效的图片URL（以http://或https://开头）或图片文件，或发送 /skip 跳过：")
        
        setup.step = "participation_type"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌍 所有人", "lottery_setup_participation_all")],
            [InlineKeyboardButton("🎬 ME专属", "lottery_setup_participation_emby")],
            [InlineKeyboardButton("🔰 ME补位", "lottery_setup_participation_d_only")]
        ])
        
        image_status = "已设置" if setup.lottery.image_url else "已跳过"
        await sendMessage(msg, f"✅ 抽奖图片{image_status}\n\n请选择参与条件：", buttons=keyboard)
    
    elif setup.step == "entry_fee":
        try:
            fee = int(text)
            if fee < 0:
                return await sendMessage(msg, "❌ 费用不能为负数，请重新输入：")
            setup.lottery.entry_fee = fee
            setup.step = "refund_losers"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ 启用退款", "lottery_setup_refund_yes")],
                [InlineKeyboardButton("❌ 不退款", "lottery_setup_refund_no")]
            ])
            
            await sendMessage(msg, f"✅ 参与费用已设置为 {fee} {sakura_b}\n\n是否给未中奖者退还50%费用？", buttons=keyboard)
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
        setup.step = "entry_fee_choice"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 设置参与费用", "lottery_setup_fee_yes")],
            [InlineKeyboardButton("🆓 免费参与", "lottery_setup_fee_no")]
        ])
        
        await editMessage(call, "✅ 已设置为所有人可参与\n\n是否需要设置参与费用？", buttons=keyboard)
    
    elif data == "lottery_setup_participation_emby":
        setup.lottery.participation_type = "emby"
        setup.step = "entry_fee_choice"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 设置费用", "lottery_setup_fee_yes")],
            [InlineKeyboardButton("🆓 免费参与", "lottery_setup_fee_no")]
        ])
        
        await editMessage(call, "✅ 已设置为仅Emby用户可参与\n\n是否需要设置参与费用？", buttons=keyboard)
    
    elif data == "lottery_setup_participation_d_only":
        setup.lottery.participation_type = "d_only"
        setup.step = "entry_fee_choice"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 设置费用", "lottery_setup_fee_yes")],
            [InlineKeyboardButton("🆓 免费参与", "lottery_setup_fee_no")]
        ])
        
        await editMessage(call, "✅ 已设置为仅新用户可参与\n\n是否需要设置参与费用？", buttons=keyboard)
    
    elif data == "lottery_setup_fee_yes":
        setup.step = "entry_fee"
        await editMessage(call, "💰 请输入参与费用（单位：" + sakura_b + "）：")
    
    elif data == "lottery_setup_fee_no":
        setup.lottery.entry_fee = 0
        setup.lottery.refund_losers = False  # 免费抽奖不需要退款
        setup.step = "draw_type"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("👤 手动开奖", "lottery_setup_draw_manual")],
            [InlineKeyboardButton("🤖 自动开奖", "lottery_setup_draw_auto")]
        ])
        
        await editMessage(call, "✅ 已设置为免费参与\n\n请选择开奖方式：", buttons=keyboard)
    
    elif data == "lottery_setup_refund_yes":
        setup.lottery.refund_losers = True
        setup.step = "draw_type"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("👤 手动开奖", "lottery_setup_draw_manual")],
            [InlineKeyboardButton("🤖 自动开奖", "lottery_setup_draw_auto")]
        ])
        
        await editMessage(call, "✅ 已启用未中奖者50%退款\n\n请选择开奖方式：", buttons=keyboard)
    
    elif data == "lottery_setup_refund_no":
        setup.lottery.refund_losers = False
        setup.step = "draw_type"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("👤 手动开奖", "lottery_setup_draw_manual")],
            [InlineKeyboardButton("🤖 自动开奖", "lottery_setup_draw_auto")]
        ])
        
        await editMessage(call, "✅ 已设置为不退款\n\n请选择开奖方式：", buttons=keyboard)
    
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
        [InlineKeyboardButton("🎯 开奖", f"lottery_draw_{lottery.id}"), InlineKeyboardButton("🎟️ 参与抽奖", f"lottery_join_{lottery.id}")]
    ])
    
    # 发送给创建者确认
    if lottery.image_url:
        await sendPhoto(msg, photo=lottery.image_url, caption=f"✅ 抽奖创建成功！\n\n{text}", buttons=keyboard)
    else:
        await sendMessage(msg, f"✅ 抽奖创建成功！\n\n{text}", buttons=keyboard)
    
    # 自动转发到所有授权群组
    success_groups = []
    failed_groups = []
    
    for group_id in group:
        try:
            if lottery.image_url:
                sent_msg = await sendPhoto(msg, photo=lottery.image_url, caption=text, buttons=keyboard, send=True, chat_id=group_id)
            else:
                sent_msg = await sendMessage(msg, text, buttons=keyboard, send=True, chat_id=group_id)
            if sent_msg and hasattr(sent_msg, 'id'):
                # 记录消息ID以便后续管理
                if not hasattr(lottery, 'group_messages'):
                    lottery.group_messages = {}
                lottery.group_messages[group_id] = sent_msg.id
                success_groups.append(group_id)
        except Exception as e:
            failed_groups.append(f"{group_id} (错误: {str(e)})")
    
    # 发送转发结果通知
    if success_groups:
        success_msg = f"🎉 抽奖已自动转发到 {len(success_groups)} 个群组"
        if failed_groups:
            success_msg += f"\n⚠️ {len(failed_groups)} 个群组转发失败"
        await sendMessage(msg, success_msg)
    else:
        await sendMessage(msg, "❌ 自动转发失败，请手动复制抽奖消息到群组")


def format_lottery_message(lottery: Lottery) -> str:
    """格式化抽奖消息"""
    participation_type_text = {
        "all": "🌍 所有人",
        "emby": "🎬 ME用户",
        "d_only": "🔰 ME未注册用户"
    }
    
    draw_type_text = {
        "manual": "👤 手动开奖",
        "auto": f"🤖 自动开奖（{lottery.target_participants}人）"
    }
    
    prizes_text = "\n".join([f"• {prize.name} x{prize.quantity}" for prize in lottery.prizes])
    
    # 构建参与条件文本
    participation_text = participation_type_text[lottery.participation_type]
    if lottery.entry_fee > 0:
        participation_text += f"\n💰 支付（{lottery.entry_fee} {sakura_b}）"
        if lottery.refund_losers:
            participation_text += f"\n💸 未中奖退还50%（{lottery.entry_fee // 2} {sakura_b}）"
    
    text = f"""🎟️ {lottery.name}

📝 {lottery.description}

🎁 奖品列表：
{prizes_text}

👥 参与条件：\n{participation_text}\n
🎯 开奖方式：{draw_type_text[lottery.draw_type]}"""

    if lottery.collection_location:
        text += f"\n📍 领奖联系人: \n{lottery.collection_location}"

    text += f"""

👨‍💼 创建者：{lottery.creator_name}
📅 创建时间：{lottery.created_at.strftime('%Y-%m-%d %H:%M:%S')}

💫 当前参与人数： {len(lottery.participants)}"""
    
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
    
    # 获取用户信息用于条件检查
    e = sql_get_emby(tg=user_id)
    
    # 检查参与条件
    if lottery.participation_type == "emby":
        if not e or e.lv not in ['a', 'b']:
            return await callAnswer(call, "❌ 您需要有ME账号才能参与此抽奖", True)
    
    elif lottery.participation_type == "d_only":
        if not e or e.lv != 'd':
            return await callAnswer(call, "❌ 此抽奖限未注册用户参与", True)
    
    # 检查付费条件
    if lottery.entry_fee > 0:
        if not e or e.iv < lottery.entry_fee:
            return await callAnswer(call, f"❌ 余额不足，需要 {lottery.entry_fee} {sakura_b}", True)
        
        # 扣除费用
        sql_update_emby(Emby.tg == user_id, iv=e.iv - lottery.entry_fee)
    
    # 添加参与者
    lottery.participants[user_id] = user_name
    
    # 发送参与确认消息，1分钟后自动删除
    confirmation_text = f"✅ 成功参与抽奖！当前参与人数：{len(lottery.participants)}"
    await callAnswer(call, confirmation_text, True)
    
    # 发送临时确认消息并设置自动删除
    try:
        temp_msg = await bot.send_message(call.from_user.id, confirmation_text)
        # 1分钟后删除消息
        asyncio.create_task(delete_message_after_delay(call.from_user.id, temp_msg.id, 60))
    except Exception:
        pass  # 如果无法发送私信则忽略
    
    # 检查是否需要自动开奖
    if (lottery.draw_type == "auto" and 
        len(lottery.participants) >= lottery.target_participants):
        await auto_draw_lottery(lottery, call.message.chat.id, call.message.id)
    else:
        # 更新消息，保持按钮可见
        text = format_lottery_message(lottery)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎯 开奖", f"lottery_draw_{lottery.id}"), InlineKeyboardButton("🎟️ 参与抽奖", f"lottery_join_{lottery.id}")]
        ])
        
        if lottery.image_url:
            # 如果有图片，需要删除原消息并发送新的图片消息
            try:
                await bot.delete_messages(call.message.chat.id, call.message.id)
                if lottery.image_url:
                    await sendPhoto(call, photo=lottery.image_url, caption=text, buttons=keyboard, send=True, chat_id=call.message.chat.id)
                else:
                    await sendMessage(call, text, buttons=keyboard, send=True, chat_id=call.message.chat.id)
            except Exception:
                # 如果删除失败，尝试编辑消息
                await editMessage(call, text, buttons=keyboard)
        else:
            await editMessage(call, text, buttons=keyboard)


async def delete_message_after_delay(chat_id: int, message_id: int, delay: int):
    """延迟删除消息"""
    await asyncio.sleep(delay)
    try:
        await bot.delete_messages(chat_id, message_id)
    except Exception:
        pass  # 忽略删除失败的情况



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
            winners[prize.name].append((winner_id, winner_name))
    
    # 生成开奖结果
    result_text = f"""🎉 {lottery.name} - 开奖结果

🎊 恭喜以下获奖者：

"""
    
    for prize_name, winner_list in winners.items():
        result_text += f"🏆 **{prize_name}**\n"
        for winner_id, winner_name in winner_list:
            result_text += f"    • {winner_name} (ID: {winner_id})\n"
        result_text += "\n"
    
    result_text += f"📊 本次抽奖统计：\n"
    result_text += f"📈 参与人数：{len(lottery.participants)}\n"
    result_text += f"🏆 获奖人数：{sum(len(w) for w in winners.values())}\n"
    result_text += f"👨‍💼 创建者：{lottery.creator_name}"
    
    # 处理未中奖者退款
    if lottery.entry_fee > 0 and lottery.refund_losers:
        # 获取所有中奖者ID
        winner_ids = set()
        for winner_list in winners.values():
            for winner_id, _ in winner_list:
                winner_ids.add(winner_id)
        
        # 给未中奖者退还50%费用
        refund_amount = lottery.entry_fee // 2
        refunded_count = 0
        
        for participant_id in lottery.participants.keys():
            if participant_id not in winner_ids:
                try:
                    e = sql_get_emby(tg=participant_id)
                    if e:
                        sql_update_emby(Emby.tg == participant_id, iv=e.iv + refund_amount)
                        # 发送退款通知
                        await bot.send_message(
                            participant_id, 
                            f"💸 抽奖 '{lottery.name}' 很遗憾您未中奖，已退还50%参与费用 {refund_amount} {sakura_b}。"
                        )
                        refunded_count += 1
                except Exception:
                    pass  # 忽略退款失败的情况
        
        if refunded_count > 0:
            result_text += f"\n💸 已为 {refunded_count} 位未中奖者退还50%费用"
    
    # 发送私信给中奖者
    for prize_name, winner_list in winners.items():
        for winner_id, winner_name in winner_list:
            try:
                private_msg = f"""🎉 恭喜中奖！

🎟️ 抽奖名称： {lottery.name}
🏆 中奖内容： {prize_name}"""
                
                if lottery.collection_location:
                    private_msg += f"\n📍 领奖联系： {lottery.collection_location}"
                
                private_msg += f"\n\n请及时联系管理员领取奖品！"
                
                await bot.send_message(winner_id, private_msg)
            except Exception:
                # 如果无法发送私信则忽略
                pass
    
    # 更新所有群组中的消息
    if hasattr(lottery, 'group_messages'):
        for group_id, msg_id in lottery.group_messages.items():
            try:
                if lottery.image_url:
                    # 先删除原消息，再发送新的结果消息
                    await bot.delete_messages(group_id, msg_id)
                    await bot.send_message(group_id, result_text)
                else:
                    await bot.edit_message_text(
                        chat_id=group_id,
                        message_id=msg_id,
                        text=result_text
                    )
            except Exception:
                # 如果无法编辑某个群组的消息，尝试发送新消息
                try:
                    await bot.send_message(group_id, result_text)
                except Exception:
                    pass  # 忽略发送失败
    
    # 移除抽奖
    del active_lotteries[lottery.id]
    
    # 发送结果到原始消息位置
    try:
        if lottery.image_url:
            # 先删除原消息，再发送结果
            await bot.delete_messages(chat_id, message_id)
            await bot.send_message(chat_id, result_text)
        else:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=result_text
            )
    except Exception:
        await bot.send_message(chat_id, result_text)


@bot.on_message(filters.command("terminate_lottery", prefixes) & filters.private)
async def terminate_lottery_command(_, msg: Message):
    """终止抽奖命令"""
    if not judge_admins(msg.from_user.id):
        return await sendMessage(msg, "❌ 只有管理员才能终止抽奖活动")
    
    if not active_lotteries:
        return await sendMessage(msg, "❌ 当前没有活跃的抽奖活动")
    
    # 显示当前活跃的抽奖列表
    keyboard_rows = []
    for lottery_id, lottery in active_lotteries.items():
        button_text = f"🎲 {lottery.name}"
        if len(button_text) > 60:  # 限制按钮文本长度
            button_text = button_text[:57] + "..."
        keyboard_rows.append([InlineKeyboardButton(button_text, f"terminate_lottery_{lottery_id}")])
    
    keyboard = InlineKeyboardMarkup(keyboard_rows)
    
    text = f"🎯 选择要终止的抽奖活动：\n\n当前活跃抽奖数量：{len(active_lotteries)}"
    await sendMessage(msg, text, buttons=keyboard)


@bot.on_callback_query(filters.regex("terminate_lottery_"))
async def handle_terminate_lottery(_, call: CallbackQuery):
    """处理终止抽奖回调"""
    if not judge_admins(call.from_user.id):
        return await callAnswer(call, "❌ 只有管理员才能终止抽奖", True)
    
    lottery_id = call.data.split("_")[-1]
    
    if lottery_id not in active_lotteries:
        return await callAnswer(call, "❌ 抽奖不存在或已结束", True)
    
    lottery = active_lotteries[lottery_id]
    
    # 检查权限（创建者或管理员）
    if call.from_user.id != lottery.creator_id and not judge_admins(call.from_user.id):
        return await callAnswer(call, "❌ 只有创建者或管理员才能终止抽奖", True)
    
    # 生成终止消息
    termination_text = f"""❌ 抽奖已被终止

🎟️ 抽奖名称： {lottery.name}
👨‍💼 创建者： {lottery.creator_name}
👥 参与人数： {len(lottery.participants)}
🔚 终止者： {call.from_user.first_name or '管理员'}
📅 终止时间： {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

此抽奖活动已被管理员终止，所有参与费用将被退还。"""
    
    # 退还参与费用
    if lottery.entry_fee > 0:
        for participant_id in lottery.participants.keys():
            try:
                e = sql_get_emby(tg=participant_id)
                if e:
                    sql_update_emby(Emby.tg == participant_id, iv=e.iv + lottery.entry_fee)
                    # 发送退款通知
                    await bot.send_message(
                        participant_id, 
                        f"💰 抽奖 '{lottery.name}' 已被终止，您的参与费用 {lottery.entry_fee} {sakura_b} 已退还。"
                    )
            except Exception:
                pass  # 忽略退款失败的情况
    
    # 更新所有群组中的消息
    if hasattr(lottery, 'group_messages'):
        for group_id, msg_id in lottery.group_messages.items():
            try:
                if lottery.image_url:
                    # 先删除原消息，再发送终止消息
                    await bot.delete_messages(group_id, msg_id)
                    await bot.send_message(group_id, termination_text)
                else:
                    await bot.edit_message_text(
                        chat_id=group_id,
                        message_id=msg_id,
                        text=termination_text
                    )
            except Exception:
                try:
                    await bot.send_message(group_id, termination_text)
                except Exception:
                    pass
    
    # 移除抽奖
    del active_lotteries[lottery_id]
    
    await editMessage(call, f"✅ 抽奖 '{lottery.name}' 已成功终止")


# Lottery module ends here
