"""
用户抽奖命令
User Lottery Commands

Author: GitHub Copilot
Date: 2024
"""

import asyncio
from datetime import datetime
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot import bot, prefixes, sakura_b, LOGGER, config
from bot.func_helper.filters import user_in_group_on_filter
from bot.func_helper.msg_utils import sendMessage, editMessage, callAnswer, sendPhoto
from bot.func_helper.fix_bottons import ikb
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby
from bot.sql_helper.sql_lottery import (
    sql_get_active_lotteries, sql_get_lottery, sql_join_lottery,
    sql_check_user_participated, sql_get_lottery_prizes,
    sql_get_lottery_participants, sql_get_lottery_winners
)


def create_lottery_list_buttons(lotteries):
    """创建抽奖列表按钮"""
    buttons = []
    for lottery in lotteries:
        status_emoji = "🎯" if lottery.status == "active" else "✅"
        cost_text = f"({lottery.cost}{sakura_b})" if not lottery.is_free else "(免费)"
        
        buttons.append([
            InlineKeyboardButton(
                f"{status_emoji} {lottery.title} {cost_text}",
                callback_data=f"lottery_view_{lottery.id}"
            )
        ])
    
    if not buttons:
        buttons.append([InlineKeyboardButton("暂无活跃抽奖", callback_data="lottery_none")])
    
    buttons.append([InlineKeyboardButton("🔄 刷新", callback_data="lottery_list")])
    return InlineKeyboardMarkup(buttons)


def create_lottery_detail_buttons(lottery_id: int, user_tg: int):
    """创建抽奖详情按钮"""
    buttons = []
    
    # 检查用户是否已参与
    participated = sql_check_user_participated(lottery_id, user_tg)
    
    if not participated:
        buttons.append([InlineKeyboardButton("🎟️ 参与抽奖", callback_data=f"lottery_join_{lottery_id}")])
    else:
        buttons.append([InlineKeyboardButton("✅ 已参与", callback_data="lottery_participated")])
    
    buttons.extend([
        [InlineKeyboardButton("👥 参与者列表", callback_data=f"lottery_participants_{lottery_id}")],
        [InlineKeyboardButton("🎁 奖品列表", callback_data=f"lottery_prizes_{lottery_id}")],
        [InlineKeyboardButton("🔙 返回列表", callback_data="lottery_list")]
    ])
    
    return InlineKeyboardMarkup(buttons)


@bot.on_message(filters.command('lottery', prefixes) & user_in_group_on_filter)
async def lottery_list(_, msg):
    """查看抽奖列表"""
    await msg.delete()
    
    if not config.lottery.status:
        return await sendMessage(msg, "❌ 抽奖系统暂未开启")
    
    user = sql_get_emby(msg.from_user.id)
    if not user:
        return await sendMessage(msg, "❌ 您还未注册，请先注册后再参与抽奖")
    
    lotteries = sql_get_active_lotteries()
    
    text = "🎲 **当前抽奖列表**\\n\\n"
    if lotteries:
        text += f"共有 {len(lotteries)} 个活跃抽奖\\n"
        text += "点击下方按钮查看详情和参与抽奖"
    else:
        text += "暂无活跃的抽奖活动\\n请关注群内公告获取最新抽奖信息"
    
    await sendMessage(
        msg,
        text,
        buttons=create_lottery_list_buttons(lotteries)
    )


@bot.on_callback_query(filters.regex(r'^lottery_list$'))
async def lottery_list_callback(_, call):
    """抽奖列表回调"""
    if not config.lottery.status:
        return await callAnswer(call, "❌ 抽奖系统暂未开启", show_alert=True)
    
    lotteries = sql_get_active_lotteries()
    
    text = "🎲 **当前抽奖列表**\\n\\n"
    if lotteries:
        text += f"共有 {len(lotteries)} 个活跃抽奖\\n"
        text += "点击下方按钮查看详情和参与抽奖"
    else:
        text += "暂无活跃的抽奖活动\\n请关注群内公告获取最新抽奖信息"
    
    await editMessage(
        call,
        text,
        buttons=create_lottery_list_buttons(lotteries)
    )


@bot.on_callback_query(filters.regex(r'^lottery_view_(\\d+)$'))
async def lottery_view_callback(_, call):
    """查看抽奖详情"""
    lottery_id = int(call.data.split('_')[2])
    
    lottery = sql_get_lottery(lottery_id)
    if not lottery:
        return await callAnswer(call, "❌ 抽奖不存在", show_alert=True)
    
    user = sql_get_emby(call.from_user.id)
    if not user:
        return await callAnswer(call, "❌ 您还未注册，请先注册", show_alert=True)
    
    # 构建详情文本
    text = f"🎲 **{lottery.title}**\\n\\n"
    
    if lottery.description:
        text += f"📝 **描述：**\\n{lottery.description}\\n\\n"
    
    # 参与信息
    cost_text = f"{lottery.cost}{sakura_b}" if not lottery.is_free else "免费"
    text += f"💰 **参与费用：** {cost_text}\\n"
    
    if lottery.require_emby:
        text += f"📱 **要求：** 需要拥有emby账号\\n"
    
    # 开奖信息
    if lottery.draw_type == "time":
        draw_time_str = lottery.draw_time.strftime("%Y-%m-%d %H:%M:%S") if lottery.draw_time else "待定"
        text += f"⏰ **开奖时间：** {draw_time_str}\\n"
    elif lottery.draw_type == "count":
        text += f"👥 **开奖条件：** 达到 {lottery.target_participants} 人参与\\n"
    
    # 参与统计
    text += f"📊 **当前参与：** {lottery.total_participants} 人"
    if lottery.max_participants:
        text += f" / {lottery.max_participants} 人"
    text += "\\n"
    
    # 状态
    status_text = {
        'active': '🟢 进行中',
        'drawn': '✅ 已开奖',
        'cancelled': '❌ 已取消'
    }.get(lottery.status, lottery.status)
    text += f"📈 **状态：** {status_text}\\n"
    
    # 检查用户参与状态
    participated = sql_check_user_participated(lottery_id, call.from_user.id)
    if participated:
        text += "\\n✅ **您已参与此抽奖**"
    
    buttons = create_lottery_detail_buttons(lottery_id, call.from_user.id)
    
    # 如果有图片，发送图片消息
    if lottery.image_url:
        await editMessage(call, text, buttons=buttons)
    else:
        await editMessage(call, text, buttons=buttons)


@bot.on_callback_query(filters.regex(r'^lottery_join_(\\d+)$'))
async def lottery_join_callback(_, call):
    """参与抽奖回调"""
    lottery_id = int(call.data.split('_')[2])
    
    lottery = sql_get_lottery(lottery_id)
    if not lottery:
        return await callAnswer(call, "❌ 抽奖不存在", show_alert=True)
    
    if lottery.status != 'active':
        return await callAnswer(call, "❌ 抽奖已结束", show_alert=True)
    
    user = sql_get_emby(call.from_user.id)
    if not user:
        return await callAnswer(call, "❌ 您还未注册，请先注册", show_alert=True)
    
    # 检查emby账号要求
    if lottery.require_emby and not user.embyid:
        return await callAnswer(call, "❌ 此抽奖需要拥有emby账号", show_alert=True)
    
    # 检查是否已参与
    if sql_check_user_participated(lottery_id, call.from_user.id):
        return await callAnswer(call, "❌ 您已经参与过此抽奖", show_alert=True)
    
    # 检查人数限制
    if lottery.max_participants and lottery.total_participants >= lottery.max_participants:
        return await callAnswer(call, "❌ 抽奖参与人数已满", show_alert=True)
    
    # 检查费用
    cost_paid = 0
    if not lottery.is_free:
        if user.iv < lottery.cost:
            return await callAnswer(call, f"❌ {sakura_b}不足，需要 {lottery.cost}{sakura_b}", show_alert=True)
        
        # 扣除费用
        new_balance = user.iv - lottery.cost
        if not sql_update_emby(Emby.tg == call.from_user.id, iv=new_balance):
            return await callAnswer(call, "❌ 扣费失败，请重试", show_alert=True)
        
        cost_paid = lottery.cost
    
    # 参与抽奖
    user_name = call.from_user.first_name or f"User{call.from_user.id}"
    if sql_join_lottery(lottery_id, call.from_user.id, user_name, cost_paid):
        await callAnswer(call, "🎉 参与抽奖成功！", show_alert=True)
        
        # 刷新抽奖详情
        await lottery_view_callback(_, call)
        
        LOGGER.info(f"用户 {user_name}({call.from_user.id}) 参与抽奖 {lottery.title}({lottery_id})")
    else:
        # 如果参与失败，退还费用
        if cost_paid > 0:
            sql_update_emby(Emby.tg == call.from_user.id, iv=user.iv)
        await callAnswer(call, "❌ 参与抽奖失败，请重试", show_alert=True)


@bot.on_callback_query(filters.regex(r'^lottery_participants_(\\d+)$'))
async def lottery_participants_callback(_, call):
    """查看参与者列表"""
    lottery_id = int(call.data.split('_')[2])
    
    lottery = sql_get_lottery(lottery_id)
    if not lottery:
        return await callAnswer(call, "❌ 抽奖不存在", show_alert=True)
    
    participants = sql_get_lottery_participants(lottery_id)
    
    text = f"👥 **{lottery.title} - 参与者列表**\\n\\n"
    
    if participants:
        text += f"共有 {len(participants)} 人参与：\\n\\n"
        for i, p in enumerate(participants, 1):
            join_time = p.join_time.strftime("%m-%d %H:%M")
            cost_text = f" ({p.cost_paid}{sakura_b})" if p.cost_paid > 0 else ""
            text += f"{i}. {p.user_name}{cost_text} - {join_time}\\n"
    else:
        text += "暂无参与者"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 返回抽奖", callback_data=f"lottery_view_{lottery_id}")]
    ])
    
    await editMessage(call, text, buttons=buttons)


@bot.on_callback_query(filters.regex(r'^lottery_prizes_(\\d+)$'))
async def lottery_prizes_callback(_, call):
    """查看奖品列表"""
    lottery_id = int(call.data.split('_')[2])
    
    lottery = sql_get_lottery(lottery_id)
    if not lottery:
        return await callAnswer(call, "❌ 抽奖不存在", show_alert=True)
    
    prizes = sql_get_lottery_prizes(lottery_id)
    
    text = f"🎁 **{lottery.title} - 奖品列表**\\n\\n"
    
    if prizes:
        for i, prize in enumerate(prizes, 1):
            text += f"**{i}. {prize.prize_name}**\\n"
            
            if prize.prize_type == "coins":
                text += f"   💰 {prize.prize_value}{sakura_b}\\n"
            else:
                text += f"   🎁 {prize.prize_value}\\n"
            
            if prize.prize_description:
                text += f"   📝 {prize.prize_description}\\n"
            
            text += f"   📦 数量：{prize.quantity}\\n\\n"
    else:
        text += "暂无奖品信息"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 返回抽奖", callback_data=f"lottery_view_{lottery_id}")]
    ])
    
    await editMessage(call, text, buttons=buttons)


@bot.on_callback_query(filters.regex(r'^lottery_none$'))
async def lottery_none_callback(_, call):
    """无抽奖回调"""
    await callAnswer(call, "暂无抽奖活动")


@bot.on_callback_query(filters.regex(r'^lottery_participated$'))
async def lottery_participated_callback(_, call):
    """已参与回调"""
    await callAnswer(call, "您已经参与过此抽奖")


@bot.on_message(filters.command('my_lottery', prefixes) & user_in_group_on_filter)
async def my_lottery_status(_, msg):
    """查看我的抽奖参与状态"""
    await msg.delete()
    
    user = sql_get_emby(msg.from_user.id)
    if not user:
        return await sendMessage(msg, "❌ 您还未注册，请先注册")
    
    # 获取用户参与的所有抽奖
    active_lotteries = sql_get_active_lotteries()
    participated_lotteries = []
    
    for lottery in active_lotteries:
        if sql_check_user_participated(lottery.id, msg.from_user.id):
            participated_lotteries.append(lottery)
    
    text = f"📊 **{msg.from_user.first_name} 的抽奖状态**\\n\\n"
    text += f"💰 **当前{sakura_b}：** {user.iv}\\n\\n"
    
    if participated_lotteries:
        text += f"🎯 **参与的抽奖 ({len(participated_lotteries)}个)：**\\n\\n"
        for lottery in participated_lotteries:
            status_emoji = "🎯" if lottery.status == "active" else "✅"
            text += f"{status_emoji} {lottery.title}\\n"
            
            if lottery.draw_type == "time" and lottery.draw_time:
                draw_time = lottery.draw_time.strftime("%m-%d %H:%M")
                text += f"   ⏰ 开奖时间：{draw_time}\\n"
            elif lottery.draw_type == "count":
                progress = f"{lottery.total_participants}/{lottery.target_participants}"
                text += f"   👥 进度：{progress}\\n"
            
            text += "\\n"
    else:
        text += "🎲 **暂未参与任何抽奖**\\n"
        text += "使用 /lottery 查看可参与的抽奖"
    
    # 检查是否有中奖记录
    winners_info = ""
    for lottery in active_lotteries + sql_get_active_lotteries():  # 包括已结束的
        winners = sql_get_lottery_winners(lottery.id)
        user_wins = [w for w in winners if w.user_tg == msg.from_user.id]
        
        if user_wins:
            if not winners_info:
                winners_info = "\\n🏆 **中奖记录：**\\n\\n"
            
            for win in user_wins:
                prize = sql_get_lottery_prizes(lottery.id)
                prize_info = next((p for p in prize if p.id == win.prize_id), None)
                if prize_info:
                    claimed_text = "✅ 已领取" if win.claimed else "⏳ 待领取"
                    winners_info += f"🎁 {lottery.title} - {prize_info.prize_name} ({claimed_text})\\n"
    
    text += winners_info
    
    await sendMessage(msg, text)