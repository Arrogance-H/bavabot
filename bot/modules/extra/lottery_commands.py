"""
抽奖管理命令处理器
"""

import asyncio
from datetime import datetime
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup

from bot import bot, prefixes, lottery, LOGGER
from bot.func_helper.filters import admins_on_filter
from bot.func_helper.msg_utils import sendMessage, callListen, editMessage
from bot.sql_helper.sql_lottery import (
    sql_create_lottery, sql_add_lottery_prize, sql_get_lottery_by_id,
    sql_update_lottery_message
)
from bot.modules.extra.lottery import LotteryManager


# 处理创建抽奖的输入
@bot.on_message(filters.reply & filters.private & admins_on_filter)
async def handle_lottery_creation(_, msg):
    """处理创建抽奖的回复消息"""
    if not msg.reply_to_message or not msg.reply_to_message.text:
        return
    
    # 检查是否是创建抽奖的回复
    if "创建新抽奖" not in msg.reply_to_message.text:
        return
    
    if not lottery.status:
        return await sendMessage(msg, "抽奖功能已关闭")
    
    try:
        # 解析输入格式: 抽奖名称|描述|参与方式|开奖方式|参与条件|参数
        parts = msg.text.strip().split('|')
        if len(parts) != 6:
            return await sendMessage(msg, 
                "❌ 格式错误，请按照以下格式输入：\n"
                "`抽奖名称|描述|参与方式|开奖方式|参与条件|参数`")
        
        name, description, lottery_type_str, draw_type_str, participation_type_str, param = parts
        
        # 验证参数
        lottery_type = int(lottery_type_str)
        draw_type = int(draw_type_str)
        participation_type = int(participation_type_str)
        
        if lottery_type not in [1, 2]:
            return await sendMessage(msg, "❌ 参与方式必须是 1 或 2")
        if draw_type not in [1, 2]:
            return await sendMessage(msg, "❌ 开奖方式必须是 1 或 2")
        if participation_type not in [1, 2, 3]:
            return await sendMessage(msg, "❌ 参与条件必须是 1、2 或 3")
        
        # 解析参数
        keyword = None
        draw_time = None
        target_participants = None
        participation_cost = 0
        
        if lottery_type == 1:  # 关键字参与
            if ',' in param:
                keyword, cost_str = param.split(',', 1)
                if participation_type == 1:  # 付费参与
                    participation_cost = int(cost_str)
            else:
                keyword = param
        elif lottery_type == 2:  # 按钮参与
            if participation_type == 1:  # 付费参与
                participation_cost = int(param)
        
        if draw_type == 1:  # 定时开奖
            if lottery_type == 2:  # 按钮参与，参数是时间
                draw_time = datetime.strptime(param, "%Y-%m-%d %H:%M")
            elif lottery_type == 1 and ',' in param:  # 关键字参与，时间在逗号后
                keyword, time_str = param.split(',', 1)
                if ':' in time_str:  # 时间格式
                    draw_time = datetime.strptime(time_str.strip(), "%Y-%m-%d %H:%M")
                else:  # 可能是费用
                    if participation_type == 1:
                        participation_cost = int(time_str)
        elif draw_type == 2:  # 人数开奖
            if lottery_type == 2:  # 按钮参与
                target_participants = int(param)
            elif lottery_type == 1 and ',' in param:  # 关键字参与
                keyword, count_str = param.split(',', 1)
                target_participants = int(count_str)
        
        # 创建抽奖
        lottery_id = sql_create_lottery(
            creator_tg=msg.from_user.id,
            name=name.strip(),
            lottery_type=lottery_type,
            draw_type=draw_type,
            participation_type=participation_type,
            keyword=keyword,
            draw_time=draw_time,
            target_participants=target_participants,
            participation_cost=participation_cost,
            description=description.strip()
        )
        
        if lottery_id:
            await sendMessage(msg, 
                f"✅ 抽奖创建成功！\n\n"
                f"抽奖ID: {lottery_id}\n"
                f"名称: {name}\n"
                f"现在请添加奖品，使用以下格式：\n"
                f"`{lottery_id}|奖品名称|数量|描述|类型`")
            LOGGER.info(f"管理员 {msg.from_user.first_name} 创建了抽奖: {name} (ID: {lottery_id})")
        else:
            await sendMessage(msg, "❌ 创建抽奖失败，请稍后重试")
            
    except ValueError as e:
        await sendMessage(msg, f"❌ 参数格式错误: {str(e)}")
    except Exception as e:
        await sendMessage(msg, f"❌ 创建失败: {str(e)}")
        LOGGER.error(f"创建抽奖失败: {e}")


# 处理添加奖品的输入
@bot.on_message(filters.reply & filters.private & admins_on_filter)
async def handle_prize_addition(_, msg):
    """处理添加奖品的回复消息"""
    if not msg.reply_to_message or not msg.reply_to_message.text:
        return
    
    # 检查是否是添加奖品的回复
    if "添加抽奖奖品" not in msg.reply_to_message.text:
        return
    
    if not lottery.status:
        return await sendMessage(msg, "抽奖功能已关闭")
    
    try:
        # 解析输入格式: 抽奖ID|奖品名称|数量|描述|类型
        parts = msg.text.strip().split('|')
        if len(parts) != 5:
            return await sendMessage(msg,
                "❌ 格式错误，请按照以下格式输入：\n"
                "`抽奖ID|奖品名称|数量|描述|类型`")
        
        lottery_id_str, prize_name, quantity_str, description, prize_type = parts
        
        lottery_id = int(lottery_id_str)
        quantity = int(quantity_str)
        
        if quantity <= 0:
            return await sendMessage(msg, "❌ 奖品数量必须大于0")
        
        # 验证抽奖是否存在
        lottery_event = sql_get_lottery_by_id(lottery_id)
        if not lottery_event:
            return await sendMessage(msg, f"❌ 抽奖ID {lottery_id} 不存在")
        
        if lottery_event.status != 'active':
            return await sendMessage(msg, "❌ 只能为活跃状态的抽奖添加奖品")
        
        # 添加奖品
        if sql_add_lottery_prize(lottery_id, prize_name.strip(), quantity, 
                                description.strip(), prize_type.strip()):
            await sendMessage(msg,
                f"✅ 奖品添加成功！\n\n"
                f"抽奖: {lottery_event.name}\n"
                f"奖品: {prize_name} x{quantity}\n"
                f"类型: {prize_type}")
            LOGGER.info(f"管理员 {msg.from_user.first_name} 为抽奖 {lottery_id} 添加了奖品: {prize_name}")
        else:
            await sendMessage(msg, "❌ 添加奖品失败，请稍后重试")
            
    except ValueError as e:
        await sendMessage(msg, f"❌ 参数格式错误: {str(e)}")
    except Exception as e:
        await sendMessage(msg, f"❌ 添加失败: {str(e)}")
        LOGGER.error(f"添加奖品失败: {e}")


# 发布抽奖到群组
@bot.on_message(filters.command("lottery_publish", prefixes) & admins_on_filter & filters.private)
async def publish_lottery_command(_, msg):
    """发布抽奖到群组"""
    if not lottery.status:
        return await sendMessage(msg, "抽奖功能已关闭")
    
    if len(msg.command) != 3:
        return await sendMessage(msg,
            "❌ 使用格式: `/lottery_publish <抽奖ID> <群组ID>`\n"
            "例如: `/lottery_publish 1 -1001234567890`")
    
    try:
        lottery_id = int(msg.command[1])
        chat_id = int(msg.command[2])
        
        lottery_event = sql_get_lottery_by_id(lottery_id)
        if not lottery_event:
            return await sendMessage(msg, f"❌ 抽奖ID {lottery_id} 不存在")
        
        if lottery_event.status != 'active':
            return await sendMessage(msg, "❌ 只能发布活跃状态的抽奖")
        
        # 创建抽奖消息
        message_text = await LotteryManager.create_lottery_message(lottery_id)
        keyboard = await LotteryManager.create_lottery_keyboard(lottery_id)
        
        # 发送到群组
        sent_message = await bot.send_message(chat_id, message_text, reply_markup=keyboard)
        
        # 更新抽奖消息ID
        sql_update_lottery_message(lottery_id, sent_message.id, chat_id)
        
        await sendMessage(msg, f"✅ 抽奖已发布到群组 {chat_id}")
        LOGGER.info(f"管理员 {msg.from_user.first_name} 发布了抽奖 {lottery_id} 到群组 {chat_id}")
        
    except ValueError:
        await sendMessage(msg, "❌ 参数格式错误，请输入正确的数字")
    except Exception as e:
        await sendMessage(msg, f"❌ 发布失败: {str(e)}")
        LOGGER.error(f"发布抽奖失败: {e}")


# 查看抽奖详情
@bot.on_message(filters.command("lottery_info", prefixes) & admins_on_filter)  
async def lottery_info_command(_, msg):
    """查看抽奖详情"""
    if not lottery.status:
        return await sendMessage(msg, "抽奖功能已关闭")
    
    if len(msg.command) != 2:
        return await sendMessage(msg, "❌ 使用格式: `/lottery_info <抽奖ID>`")
    
    try:
        lottery_id = int(msg.command[1])
        message_text = await LotteryManager.create_lottery_message(lottery_id)
        await sendMessage(msg, message_text)
        
    except ValueError:
        await sendMessage(msg, "❌ 抽奖ID必须是数字")
    except Exception as e:
        await sendMessage(msg, f"❌ 查询失败: {str(e)}")