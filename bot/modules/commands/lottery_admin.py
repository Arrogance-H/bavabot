"""
管理员抽奖命令
Admin Lottery Commands

Author: GitHub Copilot
Date: 2024
"""

import asyncio
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot import bot, prefixes, sakura_b, LOGGER, config
from bot.func_helper.filters import admins_on_filter, user_in_group_on_filter
from bot.func_helper.msg_utils import sendMessage, editMessage, callAnswer
from bot.func_helper.fix_bottons import ikb
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby
from bot.sql_helper.sql_lottery import (
    sql_create_lottery, sql_add_lottery_prize, sql_get_lottery,
    sql_get_active_lotteries, sql_draw_lottery, sql_update_lottery_status,
    sql_get_lottery_winners, sql_get_lottery_participants, sql_get_lottery_prizes,
    sql_claim_prize, sql_check_lottery_ready_to_draw
)


@bot.on_message(filters.command('lottery_create', prefixes) & admins_on_filter)
async def create_lottery_command(_, msg):
    """创建抽奖 - 管理员命令"""
    if not config.lottery.status:
        return await sendMessage(msg, "❌ 抽奖系统暂未开启")
    
    # 解析命令参数
    try:
        args = msg.text.split(None, 1)
        if len(args) < 2:
            help_text = f"""**🎲 创建抽奖命令帮助**

**基本语法：**
`/lottery_create <标题> | <描述> | <模式配置> | <开奖配置>`

**模式配置格式：**
- `free` - 免费抽奖
- `cost:<金额>` - 付费抽奖，如 cost:10
- `emby:true/false` - 是否需要emby账号

**开奖配置格式：**
- `time:<时间>` - 指定时间开奖，格式：YYYY-MM-DD HH:MM
- `count:<人数>` - 指定人数开奖，如 count:50

**示例：**
`/lottery_create 新年抽奖 | 新年快乐，送{sakura_b}啦！ | free,emby:true | time:2024-01-01 12:00`
`/lottery_create 会员专享 | 付费抽奖活动 | cost:50,emby:true | count:20`

**创建后使用 `/lottery_add_prize <抽奖ID>` 添加奖品**
            """
            return await sendMessage(msg, help_text)
        
        # 解析参数
        params = args[1].split(' | ')
        if len(params) < 4:
            return await sendMessage(msg, "❌ 参数不足，请参考帮助信息")
        
        title = params[0].strip()
        description = params[1].strip()
        mode_config = params[2].strip()
        draw_config = params[3].strip()
        
        # 解析模式配置
        is_free = True
        cost = 0
        require_emby = True
        
        for config_item in mode_config.split(','):
            config_item = config_item.strip()
            if config_item == 'free':
                is_free = True
            elif config_item.startswith('cost:'):
                is_free = False
                cost = int(config_item.split(':')[1])
            elif config_item.startswith('emby:'):
                require_emby = config_item.split(':')[1].lower() == 'true'
        
        # 解析开奖配置
        draw_type = None
        draw_time = None
        target_participants = None
        
        for config_item in draw_config.split(','):
            config_item = config_item.strip()
            if config_item.startswith('time:'):
                draw_type = 'time'
                time_str = config_item.split(':', 1)[1]
                draw_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
            elif config_item.startswith('count:'):
                draw_type = 'count'
                target_participants = int(config_item.split(':')[1])
        
        if not draw_type:
            return await sendMessage(msg, "❌ 必须指定开奖方式（time 或 count）")
        
        # 创建抽奖
        lottery_id = sql_create_lottery(
            title=title,
            description=description,
            creator_tg=msg.from_user.id,
            is_free=is_free,
            cost=cost,
            require_emby=require_emby,
            draw_type=draw_type,
            draw_time=draw_time,
            target_participants=target_participants,
            max_participants=config.lottery.default_max_participants
        )
        
        if lottery_id:
            text = f"✅ **抽奖创建成功！**\\n\\n"
            text += f"🆔 **抽奖ID：** {lottery_id}\\n"
            text += f"🎯 **标题：** {title}\\n"
            text += f"📝 **描述：** {description}\\n"
            text += f"💰 **模式：** {'免费' if is_free else f'{cost}{sakura_b}'}\\n"
            text += f"📱 **要求emby：** {'是' if require_emby else '否'}\\n"
            
            if draw_type == 'time':
                text += f"⏰ **开奖时间：** {draw_time.strftime('%Y-%m-%d %H:%M:%S')}\\n"
            else:
                text += f"👥 **开奖人数：** {target_participants}人\\n"
            
            text += f"\\n**下一步：** 使用 `/lottery_add_prize {lottery_id}` 添加奖品"
            
            await sendMessage(msg, text)
            LOGGER.info(f"管理员 {msg.from_user.first_name}({msg.from_user.id}) 创建抽奖: {title}({lottery_id})")
        else:
            await sendMessage(msg, "❌ 创建抽奖失败，请检查参数")
    
    except ValueError as e:
        await sendMessage(msg, f"❌ 参数格式错误：{str(e)}")
    except Exception as e:
        await sendMessage(msg, f"❌ 创建失败：{str(e)}")


@bot.on_message(filters.command('lottery_add_prize', prefixes) & admins_on_filter)
async def add_lottery_prize_command(_, msg):
    """添加抽奖奖品 - 管理员命令"""
    try:
        args = msg.text.split(None, 1)
        if len(args) < 2:
            help_text = f"""**🎁 添加抽奖奖品帮助**

**语法：**
`/lottery_add_prize <抽奖ID> <奖品名称> | <奖品类型> | <奖品价值> | <数量> | [描述]`

**奖品类型：**
- `coins` - {sakura_b}奖励（自动发放）
- `other` - 其他奖品（需要联系管理员）

**示例：**
`/lottery_add_prize 1 一等奖 | coins | 1000 | 1 | 大额{sakura_b}奖励`
`/lottery_add_prize 1 二等奖 | other | 永久会员 | 2 | 联系管理员领取`
            """
            return await sendMessage(msg, help_text)
        
        # 解析参数
        params = args[1].split(None, 1)
        lottery_id = int(params[0])
        
        if len(params) < 2:
            return await sendMessage(msg, "❌ 请提供奖品信息")
        
        prize_params = params[1].split(' | ')
        if len(prize_params) < 4:
            return await sendMessage(msg, "❌ 奖品参数不足")
        
        prize_name = prize_params[0].strip()
        prize_type = prize_params[1].strip()
        prize_value = prize_params[2].strip()
        quantity = int(prize_params[3].strip())
        prize_description = prize_params[4].strip() if len(prize_params) > 4 else None
        
        # 验证奖品类型
        if prize_type not in ['coins', 'other']:
            return await sendMessage(msg, "❌ 奖品类型必须是 coins 或 other")
        
        # 验证抽奖存在
        lottery = sql_get_lottery(lottery_id)
        if not lottery:
            return await sendMessage(msg, "❌ 抽奖不存在")
        
        # 添加奖品
        if sql_add_lottery_prize(
            lottery_id=lottery_id,
            prize_name=prize_name,
            prize_type=prize_type,
            prize_value=prize_value,
            quantity=quantity,
            prize_description=prize_description
        ):
            text = f"✅ **奖品添加成功！**\\n\\n"
            text += f"🎯 **抽奖：** {lottery.title}\\n"
            text += f"🎁 **奖品：** {prize_name}\\n"
            text += f"🏷️ **类型：** {prize_type}\\n"
            text += f"💎 **价值：** {prize_value}\\n"
            text += f"📦 **数量：** {quantity}\\n"
            if prize_description:
                text += f"📝 **描述：** {prize_description}\\n"
            
            await sendMessage(msg, text)
            LOGGER.info(f"管理员 {msg.from_user.first_name}({msg.from_user.id}) 为抽奖{lottery_id}添加奖品: {prize_name}")
        else:
            await sendMessage(msg, "❌ 添加奖品失败")
    
    except ValueError as e:
        await sendMessage(msg, f"❌ 参数格式错误：{str(e)}")
    except Exception as e:
        await sendMessage(msg, f"❌ 操作失败：{str(e)}")


@bot.on_message(filters.command('lottery_manage', prefixes) & admins_on_filter)
async def manage_lottery_command(_, msg):
    """管理抽奖 - 管理员命令"""
    await msg.delete()
    
    lotteries = sql_get_active_lotteries()
    
    text = "🎲 **抽奖管理面板**\\n\\n"
    
    if lotteries:
        text += f"共有 {len(lotteries)} 个活跃抽奖\\n"
        text += "点击下方按钮进行管理"
    else:
        text += "暂无活跃的抽奖\\n"
        text += "使用 `/lottery_create` 创建新抽奖"
    
    buttons = []
    for lottery in lotteries:
        cost_text = f"({lottery.cost}{sakura_b})" if not lottery.is_free else "(免费)"
        buttons.append([
            InlineKeyboardButton(
                f"🎯 {lottery.title} {cost_text}",
                callback_data=f"lottery_admin_{lottery.id}"
            )
        ])
    
    buttons.append([InlineKeyboardButton("➕ 创建新抽奖", callback_data="lottery_create_help")])
    buttons.append([InlineKeyboardButton("🔄 刷新", callback_data="lottery_manage")])
    
    await sendMessage(msg, text, buttons=InlineKeyboardMarkup(buttons))


@bot.on_callback_query(filters.regex(r'^lottery_manage$'))
async def manage_lottery_callback(_, call):
    """抽奖管理回调"""
    lotteries = sql_get_active_lotteries()
    
    text = "🎲 **抽奖管理面板**\\n\\n"
    
    if lotteries:
        text += f"共有 {len(lotteries)} 个活跃抽奖\\n"
        text += "点击下方按钮进行管理"
    else:
        text += "暂无活跃的抽奖\\n"
        text += "使用 `/lottery_create` 创建新抽奖"
    
    buttons = []
    for lottery in lotteries:
        cost_text = f"({lottery.cost}{sakura_b})" if not lottery.is_free else "(免费)"
        buttons.append([
            InlineKeyboardButton(
                f"🎯 {lottery.title} {cost_text}",
                callback_data=f"lottery_admin_{lottery.id}"
            )
        ])
    
    buttons.append([InlineKeyboardButton("➕ 创建新抽奖", callback_data="lottery_create_help")])
    buttons.append([InlineKeyboardButton("🔄 刷新", callback_data="lottery_manage")])
    
    await editMessage(call, text, buttons=InlineKeyboardMarkup(buttons))


@bot.on_callback_query(filters.regex(r'^lottery_admin_(\\d+)$'))
async def lottery_admin_callback(_, call):
    """抽奖管理详情"""
    lottery_id = int(call.data.split('_')[2])
    
    lottery = sql_get_lottery(lottery_id)
    if not lottery:
        return await callAnswer(call, "❌ 抽奖不存在", show_alert=True)
    
    participants = sql_get_lottery_participants(lottery_id)
    prizes = sql_get_lottery_prizes(lottery_id)
    
    text = f"🎲 **{lottery.title} - 管理面板**\\n\\n"
    
    # 基本信息
    text += f"🆔 **ID：** {lottery_id}\\n"
    cost_text = f"{lottery.cost}{sakura_b}" if not lottery.is_free else "免费"
    text += f"💰 **费用：** {cost_text}\\n"
    text += f"📱 **需要emby：** {'是' if lottery.require_emby else '否'}\\n"
    
    # 开奖信息
    if lottery.draw_type == "time":
        draw_time_str = lottery.draw_time.strftime("%Y-%m-%d %H:%M:%S") if lottery.draw_time else "待定"
        text += f"⏰ **开奖时间：** {draw_time_str}\\n"
    elif lottery.draw_type == "count":
        text += f"👥 **开奖条件：** {lottery.target_participants} 人\\n"
    
    # 统计信息
    text += f"📊 **参与人数：** {len(participants)}\\n"
    text += f"🎁 **奖品数量：** {len(prizes)}\\n"
    
    status_text = {
        'active': '🟢 进行中',
        'drawn': '✅ 已开奖',
        'cancelled': '❌ 已取消'
    }.get(lottery.status, lottery.status)
    text += f"📈 **状态：** {status_text}\\n"
    
    # 按钮
    buttons = []
    
    if lottery.status == 'active':
        buttons.extend([
            [InlineKeyboardButton("🎯 立即开奖", callback_data=f"lottery_draw_{lottery_id}")],
            [InlineKeyboardButton("❌ 取消抽奖", callback_data=f"lottery_cancel_{lottery_id}")]
        ])
    
    if lottery.status == 'drawn':
        buttons.append([InlineKeyboardButton("🏆 查看获奖者", callback_data=f"lottery_winners_{lottery_id}")])
    
    buttons.extend([
        [InlineKeyboardButton("👥 参与者", callback_data=f"lottery_admin_participants_{lottery_id}"),
         InlineKeyboardButton("🎁 奖品", callback_data=f"lottery_admin_prizes_{lottery_id}")],
        [InlineKeyboardButton("🔙 返回管理", callback_data="lottery_manage")]
    ])
    
    await editMessage(call, text, buttons=InlineKeyboardMarkup(buttons))


@bot.on_callback_query(filters.regex(r'^lottery_draw_(\\d+)$'))
async def lottery_draw_callback(_, call):
    """执行抽奖回调"""
    lottery_id = int(call.data.split('_')[2])
    
    lottery = sql_get_lottery(lottery_id)
    if not lottery:
        return await callAnswer(call, "❌ 抽奖不存在", show_alert=True)
    
    if lottery.status != 'active':
        return await callAnswer(call, "❌ 抽奖已结束", show_alert=True)
    
    # 执行抽奖
    result = sql_draw_lottery(lottery_id)
    
    if result["success"]:
        winners = result["winners"]
        total_participants = result["total_participants"]
        
        # 自动发放币奖励
        coins_distributed = 0
        for winner in winners:
            if winner["prize_type"] == "coins":
                try:
                    coins_amount = int(winner["prize_value"])
                    user = sql_get_emby(winner["user_tg"])
                    if user:
                        new_balance = user.iv + coins_amount
                        if sql_update_emby(Emby.tg == winner["user_tg"], iv=new_balance):
                            coins_distributed += coins_amount
                            # 标记为已领取
                            sql_claim_prize(lottery_id, winner["user_tg"], 
                                           next(p.id for p in sql_get_lottery_prizes(lottery_id) 
                                               if p.prize_name == winner["prize_name"]))
                except:
                    pass
        
        # 构建结果消息
        text = f"🎉 **抽奖 {lottery.title} 开奖完成！**\\n\\n"
        text += f"👥 **参与人数：** {total_participants}\\n"
        text += f"🏆 **获奖人数：** {len(winners)}\\n\\n"
        
        if winners:
            text += "**🎊 获奖名单：**\\n"
            for winner in winners:
                text += f"🎁 {winner['user_name']} - {winner['prize_name']}\\n"
        
        if coins_distributed > 0:
            text += f"\\n💰 **已自动发放{sakura_b}：** {coins_distributed}\\n"
        
        # 发送公告到群组
        try:
            await sendMessage(call, text, send=True)
        except:
            pass
        
        await callAnswer(call, "🎉 抽奖开奖成功！", show_alert=True)
        
        # 刷新管理面板
        await lottery_admin_callback(_, call)
        
        LOGGER.info(f"抽奖 {lottery.title}({lottery_id}) 开奖完成，{len(winners)}人获奖")
    else:
        await callAnswer(call, f"❌ 开奖失败：{result['message']}", show_alert=True)


@bot.on_callback_query(filters.regex(r'^lottery_cancel_(\\d+)$'))
async def lottery_cancel_callback(_, call):
    """取消抽奖回调"""
    lottery_id = int(call.data.split('_')[2])
    
    lottery = sql_get_lottery(lottery_id)
    if not lottery:
        return await callAnswer(call, "❌ 抽奖不存在", show_alert=True)
    
    if lottery.status != 'active':
        return await callAnswer(call, "❌ 抽奖已结束", show_alert=True)
    
    # 退还所有参与费用
    participants = sql_get_lottery_participants(lottery_id)
    refunded_count = 0
    refunded_amount = 0
    
    for participant in participants:
        if participant.cost_paid > 0:
            user = sql_get_emby(participant.user_tg)
            if user:
                new_balance = user.iv + participant.cost_paid
                if sql_update_emby(Emby.tg == participant.user_tg, iv=new_balance):
                    refunded_count += 1
                    refunded_amount += participant.cost_paid
    
    # 更新抽奖状态
    if sql_update_lottery_status(lottery_id, 'cancelled'):
        text = f"❌ **抽奖 {lottery.title} 已取消**\\n\\n"
        text += f"💰 **已退还费用给 {refunded_count} 人，共 {refunded_amount}{sakura_b}**"
        
        await callAnswer(call, "抽奖已取消", show_alert=True)
        
        # 发送公告
        try:
            await sendMessage(call, text, send=True)
        except:
            pass
        
        # 刷新管理面板
        await lottery_admin_callback(_, call)
        
        LOGGER.info(f"抽奖 {lottery.title}({lottery_id}) 被取消，退还费用给{refunded_count}人")
    else:
        await callAnswer(call, "❌ 取消失败", show_alert=True)


@bot.on_message(filters.command('lottery_draw', prefixes) & admins_on_filter)
async def manual_draw_lottery(_, msg):
    """手动开奖命令"""
    try:
        args = msg.text.split()
        if len(args) < 2:
            return await sendMessage(msg, "❌ 请指定抽奖ID：`/lottery_draw <抽奖ID>`")
        
        lottery_id = int(args[1])
        lottery = sql_get_lottery(lottery_id)
        
        if not lottery:
            return await sendMessage(msg, "❌ 抽奖不存在")
        
        if lottery.status != 'active':
            return await sendMessage(msg, "❌ 抽奖已结束")
        
        # 执行抽奖（复用上面的逻辑）
        result = sql_draw_lottery(lottery_id)
        
        if result["success"]:
            winners = result["winners"]
            
            # 自动发放币奖励
            for winner in winners:
                if winner["prize_type"] == "coins":
                    try:
                        coins_amount = int(winner["prize_value"])
                        user = sql_get_emby(winner["user_tg"])
                        if user:
                            new_balance = user.iv + coins_amount
                            sql_update_emby(Emby.tg == winner["user_tg"], iv=new_balance)
                    except:
                        pass
            
            text = f"🎉 **抽奖 {lottery.title} 开奖完成！**\\n\\n"
            text += f"🏆 **获奖人数：** {len(winners)}\\n\\n"
            
            if winners:
                text += "**获奖名单：**\\n"
                for winner in winners:
                    text += f"🎁 {winner['user_name']} - {winner['prize_name']}\\n"
            
            await sendMessage(msg, text)
        else:
            await sendMessage(msg, f"❌ 开奖失败：{result['message']}")
    
    except ValueError:
        await sendMessage(msg, "❌ 抽奖ID必须是数字")
    except Exception as e:
        await sendMessage(msg, f"❌ 操作失败：{str(e)}")


@bot.on_message(filters.command('lottery_list_all', prefixes) & admins_on_filter)
async def list_all_lotteries(_, msg):
    """查看所有抽奖 - 管理员命令"""
    active_lotteries = sql_get_active_lotteries()
    
    text = "📋 **所有抽奖列表**\\n\\n"
    
    if active_lotteries:
        for lottery in active_lotteries:
            text += f"🆔 **ID：** {lottery.id}\\n"
            text += f"🎯 **标题：** {lottery.title}\\n"
            
            cost_text = f"{lottery.cost}{sakura_b}" if not lottery.is_free else "免费"
            text += f"💰 **费用：** {cost_text}\\n"
            
            status_text = {
                'active': '🟢 进行中',
                'drawn': '✅ 已开奖',
                'cancelled': '❌ 已取消'
            }.get(lottery.status, lottery.status)
            text += f"📈 **状态：** {status_text}\\n"
            text += f"👥 **参与：** {lottery.total_participants}人\\n"
            
            if lottery.draw_type == "time" and lottery.draw_time:
                draw_time = lottery.draw_time.strftime("%m-%d %H:%M")
                text += f"⏰ **开奖：** {draw_time}\\n"
            elif lottery.draw_type == "count":
                text += f"🎯 **目标：** {lottery.target_participants}人\\n"
            
            text += "\\n" + "="*30 + "\\n\\n"
    else:
        text += "暂无抽奖活动"
    
    await sendMessage(msg, text)


# 定时检查开奖任务（需要在调度器中调用）
async def check_auto_draw():
    """自动检查并开奖"""
    if not config.lottery.auto_draw:
        return
    
    ready_lotteries = sql_check_lottery_ready_to_draw()
    
    for lottery in ready_lotteries:
        try:
            result = sql_draw_lottery(lottery.id)
            
            if result["success"]:
                winners = result["winners"]
                
                # 自动发放币奖励
                for winner in winners:
                    if winner["prize_type"] == "coins":
                        try:
                            coins_amount = int(winner["prize_value"])
                            user = sql_get_emby(winner["user_tg"])
                            if user:
                                new_balance = user.iv + coins_amount
                                sql_update_emby(Emby.tg == winner["user_tg"], iv=new_balance)
                                # 标记为已领取
                                sql_claim_prize(lottery.id, winner["user_tg"], 
                                               next(p.id for p in sql_get_lottery_prizes(lottery.id) 
                                                   if p.prize_name == winner["prize_name"]))
                        except:
                            pass
                
                # 发送开奖公告到主群
                try:
                    text = f"🎉 **抽奖 {lottery.title} 自动开奖！**\\n\\n"
                    text += f"🏆 **获奖人数：** {len(winners)}\\n\\n"
                    
                    if winners:
                        text += "**🎊 获奖名单：**\\n"
                        for winner in winners:
                            text += f"🎁 {winner['user_name']} - {winner['prize_name']}\\n"
                    
                    # 发送到主群（这里需要配置群组ID）
                    # await bot.send_message(config.main_group, text)
                    
                except:
                    pass
                
                LOGGER.info(f"自动开奖：{lottery.title}({lottery.id})，{len(winners)}人获奖")
        except Exception as e:
            LOGGER.error(f"自动开奖失败：{lottery.title}({lottery.id}) - {str(e)}")


# 其他管理回调
@bot.on_callback_query(filters.regex(r'^lottery_create_help$'))
async def lottery_create_help_callback(_, call):
    """创建抽奖帮助"""
    help_text = f"""**🎲 创建抽奖命令帮助**

**基本语法：**
`/lottery_create <标题> | <描述> | <模式配置> | <开奖配置>`

**模式配置格式：**
- `free` - 免费抽奖
- `cost:<金额>` - 付费抽奖，如 cost:10
- `emby:true/false` - 是否需要emby账号

**开奖配置格式：**
- `time:<时间>` - 指定时间开奖，格式：YYYY-MM-DD HH:MM
- `count:<人数>` - 指定人数开奖，如 count:50

**示例：**
`/lottery_create 新年抽奖 | 新年快乐，送{sakura_b}啦！ | free,emby:true | time:2024-01-01 12:00`

**创建后使用 `/lottery_add_prize <抽奖ID>` 添加奖品**
    """
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 返回管理", callback_data="lottery_manage")]
    ])
    
    await editMessage(call, help_text, buttons=buttons)