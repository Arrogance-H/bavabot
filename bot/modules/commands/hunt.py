"""
车库游戏命令 - 优化版本（移除背包功能）
"""
import asyncio
import datetime
import random
from pyrogram import filters
from bot import bot, prefixes, sakura_b, LOGGER
from bot.func_helper.filters import user_in_group_on_filter
from bot.func_helper.msg_utils import sendMessage, editMessage, callAnswer, deleteMessage
from bot.func_helper.fix_bottons import ikb
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby
from bot.sql_helper.sql_hunt import (
    sql_start_hunt, sql_end_hunt, sql_get_active_hunt, sql_add_equipment,
    sql_get_user_equipment, sql_get_today_hunt_count, sql_get_daily_car,
    sql_check_car_assembly, sql_assemble_car, sql_get_equipment_definition,
    sql_random_equipment_by_rarity, sql_count_user_equipment,
    sql_get_reward_button, sql_update_hunt_stats
)


async def delete_message_after_delay(message, delay_seconds: int):
    """在指定延迟后删除消息"""
    try:
        await asyncio.sleep(delay_seconds)
        await deleteMessage(message)
    except Exception as e:
        LOGGER.error(f"删除延迟消息失败: {e}")


# 车库游戏按钮
def hunt_game_ikb(hunt_id: int, last_hunt_time: int = 0):
    """创建车库游戏按钮"""
    current_time = int(datetime.datetime.now().timestamp())
    cooldown_remaining = max(0, 1 - (current_time - last_hunt_time))  # 1秒冷却
    can_hunt = cooldown_remaining == 0
    
    if can_hunt:
        hunt_btn_text = "🔍 寻找装备"
        bulk_hunt_btn_text = "💎 批量寻找"
    else:
        hunt_btn_text = f"⏰ 寻找装备 ({cooldown_remaining}s)"
        bulk_hunt_btn_text = f"⏰ 批量寻找 ({cooldown_remaining}s)"
    
    return ikb([
        [(hunt_btn_text, f"hunt_action_{hunt_id}")],
        [(bulk_hunt_btn_text, f"hunt_bulk_action_{hunt_id}")],
        [("🔧 组装汽车", f"hunt_assembly_{hunt_id}")],
        [("❌ 结束游戏", f"hunt_end_{hunt_id}")]
    ])


def get_equipment_color_emoji(category: str) -> str:
    """获取装备颜色对应的emoji"""
    color_map = {
        'purple': '🟣',
        'gold': '🟡', 
        'green': '🟢',
        'blue': '🔵'
    }
    return color_map.get(category, '⚪')


def hunt_assembly_ikb(hunt_id: int, car_id: int = None):
    """组装界面按钮"""
    buttons = []
    if car_id:
        buttons.append([("✨ 组装", f"hunt_do_assembly_{hunt_id}_{car_id}")])
    
    buttons.append([("🔙 返回车库", f"hunt_game_{hunt_id}")])
    
    return ikb(buttons)


@bot.on_message(filters.command('hunt', prefixes) & user_in_group_on_filter)
async def start_hunt(_, msg):
    """开始车库游戏"""
    await msg.delete()
    
    user = sql_get_emby(msg.from_user.id)
    if not user:
        return await sendMessage(msg, "❌ 您还未注册，请先注册后再参与车库游戏")
    
    # 检查今日游戏次数
    today_count = sql_get_today_hunt_count(msg.from_user.id)
    if today_count >= 5:
        return await sendMessage(msg, "⏰ 您今日的寻宝游戏次数已用完，请明日再来！")
    
    # 检查是否已有活跃游戏
    active_hunt = sql_get_active_hunt(msg.from_user.id)
    if active_hunt:
        start_time = active_hunt.start_time
        current_time = datetime.datetime.now()
        if (current_time - start_time).total_seconds() > 1800:  # 30分钟
            sql_end_hunt(active_hunt.id)
            return await sendMessage(msg, "⏰ 您的上一场寻宝游戏已超时结束，请重新开始")
        else:
            remaining_time = 1800 - int((current_time - start_time).total_seconds())
            remaining_minutes = remaining_time // 60
            remaining_seconds = remaining_time % 60
            
            # 获取今日汽车
            daily_car = sql_get_daily_car()
            car_name = daily_car.car_name if daily_car else "未知"
            
            # 获取目标装备数量
            equipment_count = sql_count_user_equipment(msg.from_user.id, today_only=True)
            
            # 获取用户昵称
            user_nickname = msg.from_user.first_name
            
            return await sendMessage(
                msg,
                f"🏎️ **寻宝游戏进行中**\n\n"
                f"👤 **{user_nickname}** 正在寻宝...\n\n"
                f"🎯 今日目标汽车: **{car_name}**\n"
                f"⏰ 剩余时间: {remaining_minutes}分{remaining_seconds}秒\n"
                f"💰 当前{sakura_b}: {user.iv}\n"
                f"🎒 目标装备: {equipment_count}个\n"
                f"🔍 找到装备: {active_hunt.equipment_found}个\n\n"
                f"继续您的寻宝之旅吧！",
                buttons=hunt_game_ikb(active_hunt.id)
            )
    
    # 开始新游戏
    hunt_id = sql_start_hunt(msg.from_user.id)
    if hunt_id == -1:
        return await sendMessage(msg, "❌ 您今日的寻宝游戏次数已达上限！")
    elif hunt_id == -2:
        return await sendMessage(msg, "❌ 您已有进行中的游戏，请先结束当前游戏")
    elif hunt_id == 0:
        return await sendMessage(msg, "❌ 开始游戏失败，请稍后再试")
    
    # 获取今日汽车和装备信息
    daily_car = sql_get_daily_car()
    if not daily_car:
        return await sendMessage(msg, "❌ 今日汽车配置错误，请联系管理员")
    
    car_name = daily_car.car_name
    required_equipment_ids = [int(x) for x in daily_car.equipment_ids.split(',')]
    
    # 构建装备显示信息
    equipment_display = ""
    for equipment_id in required_equipment_ids:
        equipment_def = sql_get_equipment_definition(equipment_id)
        if equipment_def:
            color_emoji = get_equipment_color_emoji(equipment_def.category)
            equipment_display += f"{color_emoji} {equipment_def.equipment_name}\n"
        else:
            equipment_display += f"⚪ 装备 {equipment_id}\n"
    
    # 获取奖励信息
    from bot.sql_helper.sql_hunt import sql_get_reward_config
    reward_config = sql_get_reward_config(daily_car.id)
    reward_text = ""
    if reward_config:
        if reward_config.reward_type == "coins":
            reward_text = f"🎁 完成奖励: {reward_config.reward_value}{sakura_b}\n"
        else:
            reward_text = f"🎁 完成奖励: {reward_config.reward_description}\n"
    
    # 获取用户昵称
    user_nickname = msg.from_user.first_name
    
    await sendMessage(
        msg,
        f"🏎️ **寻宝游戏开始！**\n\n"
        f"👤 **{user_nickname}** 正在寻宝...\n\n"
        f"🎯 今日目标汽车: **{car_name}**\n"
        f"{reward_text}\n"
        f"🔧 需要装备:\n{equipment_display}\n\n"
        f"⏰ 游戏时间: 30分钟\n"
        f"💰 每次寻找消耗 1{sakura_b}\n"
        f"🔄 寻找冷却: 1秒\n"
        f"**今日剩余游戏次数: {5 - today_count - 1}**\n\n"
        f"💡 提示: 非目标装备将自动丢弃\n"
        f"点击下方按钮开始寻找装备！",
        buttons=hunt_game_ikb(hunt_id)
    )


@bot.on_callback_query(filters.regex(r'^hunt_bulk_action_(\d+)$'))
async def hunt_bulk_action(_, call):
    """批量寻找装备"""
    hunt_id = int(call.matches[0].group(1))
    
    # 验证游戏会话
    hunt = sql_get_active_hunt(call.from_user.id)
    if not hunt or hunt.id != hunt_id:
        return await callAnswer(call, "❌ 游戏会话无效", show_alert=True)
    
    # 检查游戏是否超时
    start_time = hunt.start_time
    current_time = datetime.datetime.now()
    if (current_time - start_time).total_seconds() > 1800:  # 30分钟
        sql_end_hunt(hunt_id)
        return await editMessage(call, "⏰ 寻宝游戏时间已结束！")
    
    # 检查用户金币（批量寻找消耗10金币）
    user = sql_get_emby(call.from_user.id)
    if not user or user.iv < 10:
        return await callAnswer(call, f"❌ {sakura_b}不足，批量寻找需要 10{sakura_b}", show_alert=True)
    
    # 扣除金币
    if not sql_update_emby(Emby.tg == call.from_user.id, iv=user.iv - 10):
        return await callAnswer(call, f"❌ 扣除{sakura_b}失败", show_alert=True)
    
    # 获取今日目标汽车装备ID
    daily_car = sql_get_daily_car()
    target_equipment_ids = []
    if daily_car:
        target_equipment_ids = [int(x) for x in daily_car.equipment_ids.split(',')]
    
    # 批量寻找10次
    found_equipment = []
    target_found = 0
    non_target_found = 0
    
    for i in range(10):
        equipment_id = sql_random_equipment_by_rarity()
        if equipment_id:
            equipment_def = sql_get_equipment_definition(equipment_id)
            is_target = equipment_id in target_equipment_ids
            
            if is_target:
                # 目标装备，保留
                if sql_add_equipment(call.from_user.id, hunt_id, equipment_id):
                    target_found += 1
                    found_equipment.append({
                        'id': equipment_id,
                        'name': equipment_def.equipment_name if equipment_def else f"装备 {equipment_id}",
                        'category': equipment_def.category if equipment_def else 'blue',
                        'is_target': True
                    })
            else:
                # 非目标装备，自动丢弃
                non_target_found += 1
                found_equipment.append({
                    'id': equipment_id,
                    'name': equipment_def.equipment_name if equipment_def else f"装备 {equipment_id}",
                    'category': equipment_def.category if equipment_def else 'blue',
                    'is_target': False
                })
    
    # 更新寻找统计
    sql_update_hunt_stats(hunt_id, current_time)
    
    # 构建结果消息
    result_text = f"💎 **批量寻找完成！**\n\n"
    result_text += f"🔍 寻找次数: 10次\n"
    result_text += f"✅ 获得目标装备: {target_found}个\n"
    result_text += f"🗑️ 自动丢弃非目标装备: {non_target_found}个\n\n"
    
    if found_equipment:
        result_text += "📦 **发现的装备:**\n"
        for item in found_equipment:
            color_emoji = get_equipment_color_emoji(item['category'])
            status = "🎯" if item['is_target'] else "🗑️"
            result_text += f"{status} {color_emoji} {item['name']}\n"
    
    # 获取最新状态
    remaining_time = 1800 - int((current_time - start_time).total_seconds())
    remaining_minutes = remaining_time // 60
    remaining_seconds = remaining_time % 60
    
    car_name = daily_car.car_name if daily_car else "未知"
    current_equipment_count = sql_count_user_equipment(call.from_user.id, today_only=True)
    hunt = sql_get_active_hunt(call.from_user.id)  # 刷新统计
    
    result_text += f"\n🏎️ **当前状态:**\n"
    result_text += f"🎯 目标汽车: {car_name}\n"
    result_text += f"⏰ 剩余时间: {remaining_minutes}分{remaining_seconds}秒\n"
    result_text += f"💰 当前{sakura_b}: {user.iv - 10}\n"
    result_text += f"🎒 目标装备: {current_equipment_count}个\n"
    result_text += f"🔍 总计找到: {hunt.equipment_found}个\n\n"
    result_text += f"继续寻找装备吧！"
    
    await callAnswer(call, "💎 批量寻找完成！")
    await editMessage(call, result_text, buttons=hunt_game_ikb(hunt_id, int(current_time.timestamp())))


@bot.on_callback_query(filters.regex(r'^hunt_action_(\d+)$'))
async def hunt_action(_, call):
    """寻找装备动作"""
    hunt_id = int(call.matches[0].group(1))
    
    # 验证游戏会话
    hunt = sql_get_active_hunt(call.from_user.id)
    if not hunt or hunt.id != hunt_id:
        return await callAnswer(call, "❌ 游戏会话无效", show_alert=True)
    
    # 检查游戏是否超时
    start_time = hunt.start_time
    current_time = datetime.datetime.now()
    if (current_time - start_time).total_seconds() > 1800:  # 30分钟
        sql_end_hunt(hunt_id)
        return await editMessage(call, "⏰ 寻宝游戏时间已结束！")
    
    # 检查1秒冷却时间
    if hunt.last_hunt_time:
        time_since_last = (current_time - hunt.last_hunt_time).total_seconds()
        if time_since_last < 1:
            remaining = 1 - time_since_last
            return await callAnswer(call, f"⏰ 请等待 {remaining:.1f} 秒后再寻找", show_alert=True)
    
    # 检查用户金币
    user = sql_get_emby(call.from_user.id)
    if not user or user.iv < 1:
        return await callAnswer(call, f"❌ {sakura_b}不足，需要 1{sakura_b}", show_alert=True)
    
    # 扣除金币
    if not sql_update_emby(Emby.tg == call.from_user.id, iv=user.iv - 1):
        return await callAnswer(call, f"❌ 扣除{sakura_b}失败", show_alert=True)
    
    # 根据稀有度权重随机获得装备
    equipment_id = sql_random_equipment_by_rarity()
    
    if equipment_id:
        # 获取装备定义
        equipment_def = sql_get_equipment_definition(equipment_id)
        if equipment_def:
            equipment_name = equipment_def.equipment_name
            equipment_category = equipment_def.category
            color_emoji = get_equipment_color_emoji(equipment_category)
            
            # 检查是否为今日目标汽车装备
            daily_car = sql_get_daily_car()
            is_target_equipment = False
            if daily_car:
                required_equipment_ids = [int(x) for x in daily_car.equipment_ids.split(',')]
                is_target_equipment = equipment_id in required_equipment_ids
            
            # 更新最后寻找时间和找到装备数量
            sql_update_hunt_stats(hunt_id, current_time)
            
            if is_target_equipment:
                # 目标装备，自动保留
                if sql_add_equipment(call.from_user.id, hunt_id, equipment_id):
                    await callAnswer(call, f"🎉 发现目标装备！已自动保留 {equipment_name}")
                    
                    # 更新游戏界面
                    remaining_time = 1800 - int((current_time - start_time).total_seconds())
                    remaining_minutes = remaining_time // 60
                    remaining_seconds = remaining_time % 60
                    
                    car_name = daily_car.car_name if daily_car else "未知"
                    current_equipment_count = sql_count_user_equipment(call.from_user.id, today_only=True)
                    
                    # 刷新hunt对象获取最新统计
                    hunt = sql_get_active_hunt(call.from_user.id)
                    
                    await editMessage(
                        call,
                        f"🏎️ **寻宝游戏进行中**\n\n"
                        f"🎯 今日目标汽车: **{car_name}**\n"
                        f"⏰ 剩余时间: {remaining_minutes}分{remaining_seconds}秒\n"
                        f"💰 当前{sakura_b}: {user.iv - 1}\n"
                        f"🎒 目标装备: {current_equipment_count}个\n"
                        f"🔍 找到装备: {hunt.equipment_found}个\n"
                        f"✅ 刚获得: {color_emoji} {equipment_name} (目标装备)\n\n"
                        f"继续寻找装备吧！",
                        buttons=hunt_game_ikb(hunt_id, int(current_time.timestamp()))
                    )
                else:
                    await callAnswer(call, "❌ 保留装备失败", show_alert=True)
            else:
                # 非目标装备，自动丢弃并提示
                await callAnswer(call, f"🗑️ 发现非目标装备 {equipment_name}，已自动丢弃")
                
                # 更新游戏界面
                remaining_time = 1800 - int((current_time - start_time).total_seconds())
                remaining_minutes = remaining_time // 60
                remaining_seconds = remaining_time % 60
                
                car_name = daily_car.car_name if daily_car else "未知"
                current_equipment_count = sql_count_user_equipment(call.from_user.id, today_only=True)
                
                # 刷新hunt对象获取最新统计
                hunt = sql_get_active_hunt(call.from_user.id)
                
                await editMessage(
                    call,
                    f"🏎️ **寻宝游戏进行中**\n\n"
                    f"🎯 今日目标汽车: **{car_name}**\n"
                    f"⏰ 剩余时间: {remaining_minutes}分{remaining_seconds}秒\n"
                    f"💰 当前{sakura_b}: {user.iv - 1}\n"
                    f"🎒 目标装备: {current_equipment_count}个\n"
                    f"🔍 找到装备: {hunt.equipment_found}个\n"
                    f"🗑️ 刚丢弃: {color_emoji} {equipment_name} (非目标装备)\n\n"
                    f"继续寻找装备吧！",
                    buttons=hunt_game_ikb(hunt_id, int(current_time.timestamp()))
                )
        else:
            # 如果装备定义不存在，退还金币
            sql_update_emby(Emby.tg == call.from_user.id, iv=user.iv)
            await callAnswer(call, "❌ 寻找失败，请重试", show_alert=True)
    else:
        # 如果随机装备失败，退还金币
        sql_update_emby(Emby.tg == call.from_user.id, iv=user.iv)
        await callAnswer(call, "❌ 寻找失败，请重试", show_alert=True)


@bot.on_callback_query(filters.regex(r'^hunt_assembly_(\d+)$'))
async def hunt_assembly(_, call):
    """汽车组装界面"""
    hunt_id = int(call.matches[0].group(1))
    
    # 验证游戏会话
    hunt = sql_get_active_hunt(call.from_user.id)
    if not hunt or hunt.id != hunt_id:
        return await callAnswer(call, "❌ 游戏会话无效", show_alert=True)
    
    # 获取今日汽车
    daily_car = sql_get_daily_car()
    if not daily_car:
        return await callAnswer(call, "❌ 今日汽车配置错误", show_alert=True)
    
    # 检查是否可以组装
    can_assemble = sql_check_car_assembly(call.from_user.id, daily_car.id)
    
    # 获取奖励信息
    from bot.sql_helper.sql_hunt import sql_get_reward_config
    reward_config = sql_get_reward_config(daily_car.id)
    
    # 获取用户装备统计
    equipment_list = sql_get_user_equipment(call.from_user.id, today_only=True)
    equipment_counts = {}
    for equip in equipment_list:
        equipment_counts[equip.equipment_id] = equipment_counts.get(equip.equipment_id, 0) + 1
    
    required_equipment = [int(x) for x in daily_car.equipment_ids.split(',')]
    
    assembly_text = f"🔧 **汽车组装**\n\n"
    assembly_text += f"🏎️ 今日目标: **{daily_car.car_name}**\n"
    assembly_text += f"📝 描述: {daily_car.description}\n"
    
    # 添加奖励信息
    if reward_config:
        if reward_config.reward_type == "coins":
            assembly_text += f"🎁 完成奖励: {reward_config.reward_value}{sakura_b}\n"
        else:
            assembly_text += f"🎁 完成奖励: {reward_config.reward_description}\n"
    
    assembly_text += f"\n📋 **需要装备:**\n"
    
    for req_id in required_equipment:
        have_count = equipment_counts.get(req_id, 0)
        status = "✅" if have_count >= 1 else "❌"
        # 获取装备定义以显示更好的名称和颜色
        equipment_def = sql_get_equipment_definition(req_id)
        if equipment_def:
            equipment_name = equipment_def.equipment_name
            color_emoji = get_equipment_color_emoji(equipment_def.category)
            assembly_text += f"{status} {color_emoji} {equipment_name}: {have_count}/1\n"
        else:
            assembly_text += f"{status} ⚪ 装备 {req_id}: {have_count}/1\n"
    
    if can_assemble:
        assembly_text += f"\n🎉 **可以组装！**"
    else:
        assembly_text += f"\n❌ **装备不足，无法组装**"
    
    await callAnswer(call, "🔧 汽车组装")
    await editMessage(
        call, 
        assembly_text, 
        buttons=hunt_assembly_ikb(hunt_id, daily_car.id if can_assemble else None)
    )


@bot.on_callback_query(filters.regex(r'^hunt_do_assembly_(\d+)_(\d+)$'))
async def hunt_do_assembly(_, call):
    """执行汽车组装"""
    hunt_id = int(call.matches[0].group(1))
    car_id = int(call.matches[0].group(2))
    
    # 验证游戏会话
    hunt = sql_get_active_hunt(call.from_user.id)
    if not hunt or hunt.id != hunt_id:
        return await callAnswer(call, "❌ 游戏会话无效", show_alert=True)
    
    # 执行组装
    assembly_result = sql_assemble_car(call.from_user.id, car_id)
    
    if assembly_result["success"]:
        car_name = assembly_result["car_name"]
        reward_info = assembly_result["reward"]
        
        # 构建奖励信息
        reward_text = ""
        if reward_info["success"]:
            if reward_info["reward_type"] == "coins":
                reward_text = f"\n💰 奖励: +{reward_info['reward_value']}{sakura_b} (已自动添加)"
            elif reward_info["reward_type"] == "code":
                reward_text = f"\n🎫 奖励: {reward_info['reward_value']}个注册码\n📞 请联系 @MEBimmerSupportBot 领取"
            elif reward_info["reward_type"] == "white":
                reward_text = f"\n⚪ 奖励: {reward_info['reward_value']}个白名单\n📞 请联系 @MEBimmerSupportBot 领取"
            else:
                reward_text = f"\n🎁 奖励: {reward_info['message']}"
        
        await callAnswer(call, f"🎉 成功组装 {car_name}！")
        
        # 构建按钮 - 移除自定义奖励按钮，只保留游戏控制按钮
        buttons = [
            [("🎮 继续游戏", f"hunt_game_{hunt_id}")],
            [("❌ 结束游戏", f"hunt_end_{hunt_id}")]
        ]
        
        await editMessage(
            call,
            f"✨ **组装成功！**\n\n"
            f"🏎️ 恭喜您获得汽车: **{car_name}**\n"
            f"📝 {assembly_result.get('description', '')}\n"
            f"{reward_text}\n\n"
            f"🎮 您可以继续游戏或结束当前游戏！",
            buttons=ikb(buttons)
        )
        
        # 3分钟后删除消息的异步任务
        asyncio.create_task(delete_message_after_delay(call.message, 180))  # 180秒 = 3分钟
        
    else:
        await callAnswer(call, f"❌ 组装失败: {assembly_result['message']}", show_alert=True)


@bot.on_callback_query(filters.regex(r'^hunt_end_(\d+)$'))
async def hunt_end(_, call):
    """结束车库游戏"""
    hunt_id = int(call.matches[0].group(1))
    
    # 验证游戏会话
    hunt = sql_get_active_hunt(call.from_user.id)
    if not hunt or hunt.id != hunt_id:
        return await callAnswer(call, "❌ 游戏会话无效", show_alert=True)
    
    # 结束游戏
    if sql_end_hunt(hunt_id):
        # 获取游戏统计
        game_duration = datetime.datetime.now() - hunt.start_time
        duration_minutes = int(game_duration.total_seconds() // 60)
        duration_seconds = int(game_duration.total_seconds() % 60)
        
        # 获取用户昵称
        user_nickname = call.from_user.first_name
        if call.from_user.last_name:
            user_nickname += f" {call.from_user.last_name}"
        if call.from_user.username:
            user_nickname += f" (@{call.from_user.username})"
        
        # 获取用户今日装备
        equipment_list = sql_get_user_equipment(call.from_user.id, today_only=True)
        equipment_counts = {}
        for equip in equipment_list:
            equipment_counts[equip.equipment_id] = equipment_counts.get(equip.equipment_id, 0) + 1
        
        result_text = f"🏁 **车库游戏结束**\n\n"
        result_text += f"👤 **{user_nickname}** 已经结束寻宝\n\n"
        result_text += f"⏱️ 游戏时长: {duration_minutes}分{duration_seconds}秒\n"
        result_text += f"🔍 找到装备: {hunt.equipment_found}个\n"
        result_text += f"💰 消耗{sakura_b}: {hunt.coins_spent}\n\n"
        result_text += f"🎒 **已获得目标装备:**\n"
        
        if equipment_counts:
            for equipment_id in sorted(equipment_counts.keys()):
                count = equipment_counts[equipment_id]
                # 获取装备定义以显示更好的名称和颜色
                equipment_def = sql_get_equipment_definition(equipment_id)
                if equipment_def:
                    equipment_name = equipment_def.equipment_name
                    color_emoji = get_equipment_color_emoji(equipment_def.category)
                    result_text += f"{color_emoji} {equipment_name}: {count}个\n"
                else:
                    result_text += f"⚪ 装备 {equipment_id}: {count}个\n"
        else:
            result_text += "空空如也...\n"
        
        result_text += f"\n💡 记住：装备仅当天有效哦！\n感谢参与车库游戏！"
        
        await callAnswer(call, "🏁 游戏结束")
        await editMessage(call, result_text)
        
        # 3分钟后删除结束消息
        asyncio.create_task(delete_message_after_delay(call.message, 180))  # 180秒 = 3分钟
        
    else:
        await callAnswer(call, "❌ 结束游戏失败", show_alert=True)


@bot.on_callback_query(filters.regex(r'^hunt_game_(\d+)$'))
async def hunt_game_return(_, call):
    """返回车库游戏界面"""
    hunt_id = int(call.matches[0].group(1))
    
    # 验证游戏会话
    hunt = sql_get_active_hunt(call.from_user.id)
    if not hunt or hunt.id != hunt_id:
        return await callAnswer(call, "❌ 游戏会话无效", show_alert=True)
    
    # 检查游戏是否超时
    start_time = hunt.start_time
    current_time = datetime.datetime.now()
    if (current_time - start_time).total_seconds() > 1800:  # 30分钟
        sql_end_hunt(hunt_id)
        return await editMessage(call, "⏰ 车库游戏时间已结束！\n\n感谢参与，请明日再来！")
    
    remaining_time = 1800 - int((current_time - start_time).total_seconds())
    remaining_minutes = remaining_time // 60
    remaining_seconds = remaining_time % 60
    
    # 获取今日汽车
    daily_car = sql_get_daily_car()
    car_name = daily_car.car_name if daily_car else "未知"
    
    # 获取用户当前金币和目标装备数量
    user = sql_get_emby(call.from_user.id)
    current_coins = user.iv if user else 0
    equipment_count = sql_count_user_equipment(call.from_user.id, today_only=True)
    
    await callAnswer(call, "🏎️ 返回车库")
    await editMessage(
        call,
        f"🏎️ **车库游戏进行中**\n\n"
        f"🎯 今日目标汽车: **{car_name}**\n"
        f"⏰ 剩余时间: {remaining_minutes}分{remaining_seconds}秒\n"
        f"💰 当前{sakura_b}: {current_coins}\n"
        f"🎒 目标装备: {equipment_count}个\n"
        f"🔍 找到的装备: {hunt.equipment_found}个\n\n"
        f"点击下方按钮继续寻找装备！",
        buttons=hunt_game_ikb(hunt_id)
    )
