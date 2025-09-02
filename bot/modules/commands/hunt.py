"""
车库游戏命令 - 优化版本（移除背包功能）
"""
import asyncio
import datetime
import random
from pyrogram import filters
from bot import bot, prefixes, sakura_b, LOGGER, config
from bot.func_helper.filters import user_in_group_on_filter
from bot.func_helper.msg_utils import sendMessage, editMessage, callAnswer, deleteMessage
from bot.func_helper.fix_bottons import ikb
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby
from bot.sql_helper.sql_hunt import (
    sql_start_hunt, sql_end_hunt, sql_get_active_hunt, sql_get_hunt_by_id, sql_add_equipment,
    sql_get_user_equipment, sql_get_today_hunt_count, sql_get_total_hunt_actions, sql_get_daily_car,
    sql_get_equipment_definition, sql_random_equipment_by_rarity, sql_count_user_equipment,
    sql_update_hunt_stats, sql_get_cached_daily_car, sql_update_bulk_hunt_stats, sql_check_and_fix_hunt_table,
    sql_clear_user_equipment
)


async def delete_message_after_delay(message, delay_seconds: int):
    """在指定延迟后删除消息"""
    try:
        await asyncio.sleep(delay_seconds)
        await deleteMessage(message)
    except Exception as e:
        LOGGER.error(f"删除延迟消息失败: {e}")


async def validate_hunt_session(call, hunt_id: int) -> tuple[bool, any]:
    """
    验证车库游戏会话
    返回 (is_valid, hunt_object)
    - 如果会话有效且属于当前用户，返回 (True, hunt)
    - 如果会话有效但属于别人，显示提示并返回 (False, None)
    - 如果会话无效，删除消息并返回 (False, None)
    """
    # 首先检查用户自己的活跃游戏
    user_hunt = sql_get_active_hunt(call.from_user.id)
    if user_hunt and user_hunt.id == hunt_id:
        # 会话有效且属于当前用户
        return True, user_hunt
    
    # 检查该hunt_id是否属于其他用户
    other_hunt = sql_get_hunt_by_id(hunt_id)
    if other_hunt and other_hunt.tg != call.from_user.id:
        # 会话存在但属于别人
        await callAnswer(call, "❌ 这是别人的寻宝图，请启动自己的游戏", show_alert=True)
        return False, None
    
    # 会话不存在或已过期，删除消息
    await callAnswer(call, "❌ 游戏会话无效", show_alert=True)
    try:
        await deleteMessage(call.message)
    except:
        pass
    return False, None


# 车库游戏按钮
def hunt_game_ikb(hunt_id: int, last_hunt_time: int = 0):
    """创建车库游戏按钮 - 包含批量寻找选项"""
    current_time = int(datetime.datetime.now().timestamp())
    cooldown_remaining = max(0, 1 - (current_time - last_hunt_time))  # 1秒冷却
    can_hunt = cooldown_remaining == 0
    
    if can_hunt:
        hunt_btn_text = "🔍 开始寻宝"
        bulk_10_text = "🔍 寻找10次"
        bulk_50_text = "🔍 寻找50次"
    else:
        hunt_btn_text = f"⏰ 寻找寻宝"
        bulk_10_text = f"⏰ 寻找10次"
        bulk_50_text = f"⏰ 寻找50次"
    
    return ikb([
        [(hunt_btn_text, f"hunt_action_{hunt_id}")],
        [(bulk_10_text, f"hunt_bulk_action_{hunt_id}_10"), (bulk_50_text, f"hunt_bulk_action_{hunt_id}_50")],
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


async def handle_game_completion(call, hunt_id: int, daily_car, equipment_found_text: str = "") -> bool:
    """处理游戏完成逻辑 - 当收集齐全部目标装备时"""
    if not daily_car:
        return False
    
    # 获取奖励信息
    from bot.sql_helper.sql_hunt import sql_get_reward_config, sql_give_assembly_reward
    reward_config = sql_get_reward_config(daily_car.id)
    
    # 获取hunt对象以获取完整的统计信息
    hunt = sql_get_active_hunt(call.from_user.id)
    if not hunt:
        return False
    
    # 构建简化的完成消息（不包含奖励信息）
    message_text = f"{equipment_found_text}🎉 **恭喜完成寻宝！**\n\n"
    message_text += f"🏎️ 目标汽车: **{daily_car.car_name}**\n"
    message_text += f"📝 {daily_car.description}\n"
    message_text += f"\n✨ **装备已收集完成，游戏自动结束！**\n"
    message_text += f"🧹 **装备已清空，可以重新开始游戏！**\n"
    message_text += f"🎮 感谢参与寻宝游戏！"
    
    # 处理奖励发放（用于独立通知消息）
    reward_given = False
    reward_description = ""
    claim_info = ""
    
    if reward_config:
        # 使用现有的奖励发放系统给用户发放奖励（所有类型）
        reward_result = sql_give_assembly_reward(call.from_user.id, daily_car.id)
        if reward_result.get("success", False):
            reward_given = True
            if reward_config.reward_type == "coins":
                reward_description = f"{reward_config.reward_value}{sakura_b}"
                claim_info = "✅已自动到账"
            elif reward_config.reward_type == "code":
                reward_description = reward_config.reward_description
                claim_info = "📞 请联系 @MEBimmerSupportBot 领取"
            elif reward_config.reward_type == "white":
                reward_description = reward_config.reward_description
                claim_info = "📞 请联系 @MEBimmerSupportBot 领取"
            else:
                reward_description = reward_config.reward_description
                claim_info = "请查看游戏详情"
        else:
            # 发放失败的情况
            if reward_config.reward_type == "coins":
                reward_description = f"{reward_config.reward_value}{sakura_b}"
                claim_info = "❌发放失败，请联系管理员"
            else:
                reward_description = reward_config.reward_description
                claim_info = "❌奖励发放失败，请联系管理员"
    else:
        reward_description = "无奖励配置"
        claim_info = "无需领取"
    
    # 结束游戏
    sql_end_hunt(hunt_id)
    
    # 清空用户装备，为下次游戏做准备
    equipment_cleared = sql_clear_user_equipment(call.from_user.id, today_only=True)
    if equipment_cleared:
        LOGGER.info(f"已清空用户 {call.from_user.id} 的所有装备")
    else:
        LOGGER.warning(f"清空用户 {call.from_user.id} 装备失败")
    
    # 编辑当前消息显示简化的完成信息
    await editMessage(call, message_text)
    
    # 发送独立的完成通知消息
    completion_time = datetime.datetime.now()
    user_nickname = call.from_user.first_name
    if call.from_user.last_name:
        user_nickname += f" {call.from_user.last_name}"
    
    # 构建详细的完成通知消息
    notification_text = f"🎉 **寻宝游戏完成通知** 🎉\n\n"
    notification_text += f"👤 **用户信息:**\n"
    notification_text += f"   昵称: {user_nickname}\n"
    if call.from_user.username:
        notification_text += f"   用户名: @{call.from_user.username}\n"
    notification_text += f"   TG ID: `{call.from_user.id}`\n\n"
    notification_text += f"⏰ **完成时间:** {completion_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    notification_text += f"🏎️ **目标汽车:** {daily_car.car_name}\n\n"
    notification_text += f"💰 **消耗JOY币:** {hunt.coins_spent}\n\n"
    notification_text += f"🎁 **获得奖励:** {reward_description}\n\n"
    notification_text += f"📋 **领奖信息:** {claim_info}\n\n"
    notification_text += f"🎮 恭喜完成寻宝挑战！"
    
    # 发送独立的通知消息
    try:
        await sendMessage(call, notification_text, send=False)
    except Exception as e:
        LOGGER.error(f"发送完成通知消息失败: {e}")
    
    # 5分钟后删除消息（超过5分钟无操作自动删除）
    asyncio.create_task(delete_message_after_delay(call.message, 300))
    
    return True






def get_user_target_equipment_display(tg: int, target_equipment_ids: list) -> str:
    """获取用户目标装备显示信息"""
    # 获取用户今日装备
    equipment_list = sql_get_user_equipment(tg, today_only=True)
    equipment_counts = {}
    for equip in equipment_list:
        equipment_counts[equip.equipment_id] = equipment_counts.get(equip.equipment_id, 0) + 1
    
    display_text = "🎒 **已获得目标装备:**\n"
    all_equipped = True
    
    for target_id in target_equipment_ids:
        have_count = equipment_counts.get(target_id, 0)
        status = "✅" if have_count >= 1 else "❌"
        if have_count < 1:
            all_equipped = False
            
        # 获取装备定义
        equipment_def = sql_get_equipment_definition(target_id)
        if equipment_def:
            equipment_name = equipment_def.equipment_name
            color_emoji = get_equipment_color_emoji(equipment_def.category)
            display_text += f"{status} {color_emoji} {equipment_name}: {have_count}/1\n"
        else:
            display_text += f"{status} ⚪ 装备 {target_id}: {have_count}/1\n"
    
    if all_equipped:
        display_text += "\n🎉 **装备齐全，可以组装！**"
    else:
        display_text += "\n❓ **还需收集更多装备**"
    
    return display_text, all_equipped




@bot.on_message(filters.command('hunt', prefixes) & user_in_group_on_filter)
async def start_hunt(_, msg):
    """开始车库游戏"""
    await msg.delete()
    
    user = sql_get_emby(msg.from_user.id)
    if not user:
        return await sendMessage(msg, "❌ 您还未注册，请先注册后再参与车库游戏")
    
    # 检查今日游戏次数
    today_count = sql_get_today_hunt_count(msg.from_user.id)
    if today_count >= config.hunt_daily_limit:
        return await sendMessage(msg, "⏰ 您今日的寻宝游戏次数已用完，请明日再来！")
    
    # 检查是否已有活跃游戏
    active_hunt = sql_get_active_hunt(msg.from_user.id)
    if active_hunt:
        # 获取缓存的每日汽车信息
        daily_car = sql_get_cached_daily_car(active_hunt)
        car_name = daily_car.car_name if daily_car else "未知"
        
        # 获取目标装备数量
        equipment_count = sql_count_user_equipment(msg.from_user.id, today_only=True)
        
        # 获取目标装备显示信息
        target_equipment_ids = []
        equipment_display = ""
        assembly_ready = False
        if daily_car:
            target_equipment_ids = [int(x) for x in daily_car.equipment_ids.split(',')]
            equipment_display, assembly_ready = get_user_target_equipment_display(msg.from_user.id, target_equipment_ids)
        
        # 获取用户昵称
        user_nickname = msg.from_user.first_name
        
        return await sendMessage(
            msg,
            f"🏎️ **寻宝游戏进行中**\n\n"
            f"👤 **{user_nickname}** 正在寻宝...\n\n"
            f"🎯 今日目标汽车: **{car_name}**\n"
            f"💰 当前{sakura_b}: {user.iv}\n"
            f"📊 总寻宝次数: {sql_get_total_hunt_actions(msg.from_user.id)}次\n\n"
            f"{equipment_display}\n\n"
            f"💪 继续您的寻宝之旅吧！",
            buttons=hunt_game_ikb(active_hunt.id)
        )
    
    # 开始新游戏
    hunt_id = sql_start_hunt(msg.from_user.id)
    if hunt_id == -1:
        return await sendMessage(msg, "❌ 您今日的寻宝游戏次数已达上限！")
    elif hunt_id == -2:
        return await sendMessage(msg, "❌ 您已有进行中的游戏，请先结束当前游戏")
    elif hunt_id == -3:
        # 数据库结构问题，尝试修复
        if sql_check_and_fix_hunt_table():
            # 修复成功，重试开始游戏
            hunt_id = sql_start_hunt(msg.from_user.id)
            if hunt_id > 0:
                # 成功了，继续正常流程
                pass
            else:
                return await sendMessage(msg, 
                    "❌ 数据库已修复，但游戏启动仍失败\n\n"
                    "🔧 请管理员运行数据库重构脚本：\n"
                    "`python3 reconstruct_hunt_database.py --backup`\n\n"
                    "或查看 HUNT_RECONSTRUCTION_README.md 获取详细说明")
        else:
            return await sendMessage(msg, 
                "❌ 数据库结构需要重构以兼容当前游戏代码\n\n"
                "🔧 请管理员运行以下命令：\n"
                "`python3 reconstruct_hunt_database.py --backup`\n\n"
                "📖 详细说明请查看：HUNT_RECONSTRUCTION_README.md")
    elif hunt_id == 0:
        return await sendMessage(msg, "❌ 开始游戏失败，请稍后再试")
    
    if hunt_id <= 0:
        return  # 如果还是失败，直接返回
    
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
        f"🔧 需要装备:\n{equipment_display}\n"
        f"💰 每次寻找消耗 1{sakura_b}\n"
        f"🕹️ 今日剩余游戏次数: {config.hunt_daily_limit - today_count - 1}\n"
        f"📊 总寻宝次数: {sql_get_total_hunt_actions(msg.from_user.id)}次\n\n"
        f"👇 点击下方按钮开始寻找装备！",
        buttons=hunt_game_ikb(hunt_id)
    )


@bot.on_callback_query(filters.regex(r'^hunt_bulk_action_(\d+)_(\d+)$'))
async def hunt_bulk_action(_, call):
    """批量寻找装备"""
    hunt_id = int(call.matches[0].group(1))
    quantity = int(call.matches[0].group(2))
    
    # 验证批量数量
    if quantity not in [10, 50]:
        return await callAnswer(call, "❌ 无效的批量数量", show_alert=True)
    
    # 验证游戏会话
    is_valid, hunt = await validate_hunt_session(call, hunt_id)
    if not is_valid:
        return
    
    # 计算所需金币 (每次1金币)
    required_coins = quantity
    user = sql_get_emby(call.from_user.id)
    if not user or user.iv < required_coins:
        return await callAnswer(call, f"❌ {sakura_b}不足，批量寻找{quantity}次需要 {required_coins}{sakura_b}", show_alert=True)
    
    # 扣除金币
    if not sql_update_emby(Emby.tg == call.from_user.id, iv=user.iv - required_coins):
        return await callAnswer(call, f"❌ 扣除{sakura_b}失败", show_alert=True)
    
    # 获取今日目标汽车装备ID (从缓存)
    daily_car = sql_get_cached_daily_car(hunt)
    target_equipment_ids = []
    if daily_car:
        target_equipment_ids = [int(x) for x in daily_car.equipment_ids.split(',')]
    
    # 批量寻找指定次数
    found_equipment = []
    target_found = 0
    non_target_found = 0
    
    for i in range(quantity):
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
    
    # 更新寻找统计 - 批量寻找记录实际次数
    sql_update_bulk_hunt_stats(hunt_id, datetime.datetime.now(), quantity)
    
    # 构建结果消息
    result_text = f"⏳ **寻宝完成！**\n\n"
    result_text += f"🔍 寻找次数: {quantity}次\n"
    result_text += f"✅ 获得目标装备: {target_found}个\n"
    result_text += f"🗑️ 丢弃非目标装备: {non_target_found}个\n\n"
    
    if found_equipment:
        result_text += "📦 **发现的装备:**\n"
        for item in found_equipment:
            color_emoji = get_equipment_color_emoji(item['category'])
            status = "🎯" if item['is_target'] else "🗑️"
            result_text += f"{status} {color_emoji} {item['name']}\n"
    
    # 获取最新状态
    car_name = daily_car.car_name if daily_car else "未知"
    hunt = sql_get_active_hunt(call.from_user.id)  # 刷新统计
    
    # 获取目标装备显示信息
    target_equipment_ids = []
    equipment_display = ""
    assembly_ready = False
    if daily_car:
        target_equipment_ids = [int(x) for x in daily_car.equipment_ids.split(',')]
        equipment_display, assembly_ready = get_user_target_equipment_display(call.from_user.id, target_equipment_ids)
    
    # 检查是否装备齐全，自动完成游戏
    if assembly_ready and daily_car and target_found > 0:
        # 调用游戏完成处理函数
        await callAnswer(call, f"🎉 批量寻找{quantity}次完成并已收集齐全！游戏结束！")
        completion_success = await handle_game_completion(call, hunt_id, daily_car, result_text + "\n\n")
        if completion_success:
            return  # 游戏完成，直接返回
    
    # 装备未齐全或游戏完成失败，显示正常的游戏进行界面
    result_text += f"\n🏎️ **当前状态:**\n"
    result_text += f"👤 **{call.from_user.first_name}** 正在寻宝...\n"
    result_text += f"🎯 目标汽车: {car_name}\n"
    result_text += f"💰 当前{sakura_b}: {user.iv - required_coins}\n"
    result_text += f"📊 总寻宝次数: {sql_get_total_hunt_actions(call.from_user.id)}次\n\n"
    result_text += f"{equipment_display}\n\n"
    result_text += f"💪 继续寻找装备吧！"
    
    await callAnswer(call, f"⏳ 批量寻找{quantity}次完成！")
    await editMessage(call, result_text, buttons=hunt_game_ikb(hunt_id, int(datetime.datetime.now().timestamp())))


@bot.on_callback_query(filters.regex(r'^hunt_action_(\d+)$'))
async def hunt_action(_, call):
    """寻找装备动作"""
    hunt_id = int(call.matches[0].group(1))
    
    # 验证游戏会话
    is_valid, hunt = await validate_hunt_session(call, hunt_id)
    if not is_valid:
        return
    
    # 检查1秒冷却时间
    current_time = datetime.datetime.now()
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
            daily_car = sql_get_cached_daily_car(hunt)
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
                    car_name = daily_car.car_name if daily_car else "未知"
                    
                    # 获取目标装备显示信息
                    target_equipment_ids = []
                    equipment_display = ""
                    assembly_ready = False
                    if daily_car:
                        target_equipment_ids = [int(x) for x in daily_car.equipment_ids.split(',')]
                        equipment_display, assembly_ready = get_user_target_equipment_display(call.from_user.id, target_equipment_ids)
                    
                    # 检查是否装备齐全，自动完成游戏
                    if assembly_ready and daily_car:
                        # 调用游戏完成处理函数
                        await callAnswer(call, f"🎉 发现目标装备并已收集齐全！游戏结束！")
                        completion_success = await handle_game_completion(call, hunt_id, daily_car, 
                                                                         f"✅ 最后获得: {color_emoji} {equipment_name}\n\n")
                        if completion_success:
                            return  # 游戏完成，直接返回
                    
                    # 获取用户昵称
                    user_nickname = call.from_user.first_name
                    
                    # 装备未齐全或游戏完成失败，显示正常的游戏进行界面
                    # 刷新hunt对象获取最新统计
                    hunt = sql_get_active_hunt(call.from_user.id)
                    
                    await editMessage(
                        call,
                        f"🏎️ **寻宝游戏进行中**\n\n"
                        f"👤 **{user_nickname}** 正在寻宝...\n\n"
                        f"🎯 今日目标汽车: **{car_name}**\n"
                        f"💰 当前{sakura_b}: {user.iv - 1}\n"
                        f"📊 总寻宝次数: {sql_get_total_hunt_actions(call.from_user.id)}次\n"
                        f"✅ 刚获得: {color_emoji} {equipment_name} (目标装备)\n\n"
                        f"{equipment_display}\n\n"
                        f"💪 继续寻找装备吧！",
                        buttons=hunt_game_ikb(hunt_id, int(current_time.timestamp()))
                    )
                else:
                    await callAnswer(call, "❌ 保留装备失败", show_alert=True)
            else:
                # 非目标装备，自动丢弃并提示
                await callAnswer(call, f"🗑️ 发现非目标装备 {equipment_name}，已自动丢弃")
                
                # 更新游戏界面
                car_name = daily_car.car_name if daily_car else "未知"
                
                # 获取目标装备显示信息
                target_equipment_ids = []
                equipment_display = ""
                assembly_ready = False
                if daily_car:
                    target_equipment_ids = [int(x) for x in daily_car.equipment_ids.split(',')]
                    equipment_display, assembly_ready = get_user_target_equipment_display(call.from_user.id, target_equipment_ids)
                
                # 刷新hunt对象获取最新统计
                hunt = sql_get_active_hunt(call.from_user.id)
                
                # 获取用户昵称
                user_nickname = call.from_user.first_name
                
                await editMessage(
                    call,
                    f"🏎️ **寻宝游戏进行中**\n\n"
                    f"👤 **{user_nickname}** 正在寻宝...\n\n"
                    f"🎯 今日目标汽车: **{car_name}**\n"
                    f"💰 当前{sakura_b}: {user.iv - 1}\n"
                    f"📊 总寻宝次数: {sql_get_total_hunt_actions(call.from_user.id)}次\n"
                    f"🗑️ 刚丢弃: {color_emoji} {equipment_name} (非目标装备)\n\n"
                    f"{equipment_display}\n\n"
                    f"💪 继续寻找装备吧！",
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




@bot.on_callback_query(filters.regex(r'^hunt_end_(\d+)$'))
async def hunt_end(_, call):
    """结束车库游戏"""
    hunt_id = int(call.matches[0].group(1))
    
    # 验证游戏会话
    is_valid, hunt = await validate_hunt_session(call, hunt_id)
    if not is_valid:
        return
    
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
        
        result_text = f"🏁 **寻宝结束**\n\n"
        result_text += f"👤 **{user_nickname}** 已经结束寻宝\n\n"
        result_text += f"⏱️ 游戏时长: {duration_minutes}分{duration_seconds}秒\n"
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
        
        result_text += f"\n💡 记住：装备仅当天有效哦！\n☺️ 感谢参与寻宝游戏！"
        
        await callAnswer(call, "🏁 游戏结束")
        await editMessage(call, result_text)
        
        # 5分钟后删除结束消息（游戏结束后自动删除）
        asyncio.create_task(delete_message_after_delay(call.message, 300))  # 300秒 = 5分钟
        
    else:
        await callAnswer(call, "❌ 结束游戏失败", show_alert=True)


@bot.on_callback_query(filters.regex(r'^hunt_game_(\d+)$'))
async def hunt_game_return(_, call):
    """返回车库游戏界面"""
    hunt_id = int(call.matches[0].group(1))
    
    # 验证游戏会话
    is_valid, hunt = await validate_hunt_session(call, hunt_id)
    if not is_valid:
        return
    
    # 获取缓存的每日汽车
    daily_car = sql_get_cached_daily_car(hunt)
    car_name = daily_car.car_name if daily_car else "未知"
    
    # 获取用户当前金币
    user = sql_get_emby(call.from_user.id)
    current_coins = user.iv if user else 0
    
    # 获取目标装备显示信息
    target_equipment_ids = []
    equipment_display = ""
    assembly_ready = False
    if daily_car:
        target_equipment_ids = [int(x) for x in daily_car.equipment_ids.split(',')]
        equipment_display, assembly_ready = get_user_target_equipment_display(call.from_user.id, target_equipment_ids)
    
    await callAnswer(call, "🏎️ 返回车库")
    await editMessage(
        call,
        f"🏎️ **寻宝进行中**\n\n"
        f"👤 **{call.from_user.first_name}** 正在寻宝...\n\n"
        f"🎯 今日目标汽车: **{car_name}**\n"
        f"💰 当前{sakura_b}: {current_coins}\n"
        f"📊 总寻宝次数: {sql_get_total_hunt_actions(call.from_user.id)}次\n\n"
        f"{equipment_display}\n\n"
        f"👇 点击下方按钮继续寻找装备！",
        buttons=hunt_game_ikb(hunt_id)
    )
