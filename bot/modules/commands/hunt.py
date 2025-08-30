"""
车库游戏命令
"""
import asyncio
import datetime
import random
from pyrogram import filters
from bot import bot, prefixes, sakura_b, LOGGER
from bot.func_helper.filters import user_in_group_on_filter
from bot.func_helper.msg_utils import sendMessage, editMessage, callAnswer
from bot.func_helper.fix_bottons import ikb
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby
from bot.sql_helper.sql_hunt import (
    sql_start_hunt, sql_end_hunt, sql_get_active_hunt, sql_add_equipment,
    sql_get_user_equipment, sql_get_today_hunt_count, sql_get_daily_car,
    sql_check_car_assembly, sql_assemble_car, sql_get_equipment_definition,
    sql_random_equipment_by_rarity, sql_count_user_equipment, sql_discard_equipment
)


# 车库游戏按钮
def hunt_game_ikb(hunt_id: int, last_hunt_time: int = 0):
    """创建车库游戏按钮"""
    current_time = int(datetime.datetime.now().timestamp())
    cooldown_remaining = max(0, 1 - (current_time - last_hunt_time))  # 1秒冷却
    can_hunt = cooldown_remaining == 0
    
    if can_hunt:
        hunt_btn_text = "🔍 寻找装备"
    else:
        hunt_btn_text = f"⏰ 寻找装备 ({cooldown_remaining}s)"
    
    return ikb([
        [(hunt_btn_text, f"hunt_action_{hunt_id}")],
        [("🎒 背包", f"hunt_inventory_{hunt_id}"), ("🔧 组装", f"hunt_assembly_{hunt_id}")],
        [("❌ 结束游戏", f"hunt_end_{hunt_id}")]
    ])


def hunt_inventory_ikb(hunt_id: int):
    """背包界面按钮"""
    return ikb([
        [("🔧 组装汽车", f"hunt_assembly_{hunt_id}")],
        [("🔙 返回车库", f"hunt_game_{hunt_id}")]
    ])


def hunt_assembly_ikb(hunt_id: int, car_id: int = None):
    """组装界面按钮"""
    buttons = []
    if car_id:
        buttons.append([("✨ 组装", f"hunt_do_assembly_{hunt_id}_{car_id}")])
    
    buttons.extend([
        [("🎒 背包", f"hunt_inventory_{hunt_id}")],
        [("🔙 返回车库", f"hunt_game_{hunt_id}")]
    ])
    
    return ikb(buttons)


def equipment_choice_ikb(hunt_id: int, equipment_id: int):
    """装备选择按钮（保留或丢弃）"""
    return ikb([
        [("💎 保留", f"keep_equipment_{hunt_id}_{equipment_id}"), ("🗑️ 丢弃", f"discard_equipment_{hunt_id}_{equipment_id}")]
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


@bot.on_message(filters.command('hunt', prefixes) & user_in_group_on_filter)
async def start_hunt(_, msg):
    """开始车库游戏"""
    await msg.delete()
    
    user = sql_get_emby(msg.from_user.id)
    if not user:
        return await sendMessage(msg, "❌ 请先私聊机器人进行注册")
    
    # 检查今日游戏次数
    today_count = sql_get_today_hunt_count(msg.from_user.id)
    if today_count >= 5:
        return await sendMessage(msg, f"❌ 您今日已进行了 {today_count} 次车库游戏，每日限制 5 次")
    
    # 检查是否有进行中的游戏
    active_hunt = sql_get_active_hunt(msg.from_user.id)
    if active_hunt:
        # 检查游戏是否超时（30分钟）
        start_time = active_hunt.start_time
        current_time = datetime.datetime.now()
        if (current_time - start_time).total_seconds() > 1800:  # 30分钟
            sql_end_hunt(active_hunt.id)
            return await sendMessage(msg, "⏰ 您的上一场车库游戏已超时结束，请重新开始")
        else:
            remaining_time = 1800 - int((current_time - start_time).total_seconds())
            remaining_minutes = remaining_time // 60
            remaining_seconds = remaining_time % 60
            
            # 获取今日汽车
            daily_car = sql_get_daily_car()
            car_name = daily_car.car_name if daily_car else "未知"
            
            # 获取背包装备数量
            equipment_count = sql_count_user_equipment(msg.from_user.id, today_only=True)
            
            return await sendMessage(
                msg,
                f"🏎️ **车库游戏进行中**\n\n"
                f"🎯 今日目标汽车: **{car_name}**\n"
                f"⏰ 剩余时间: {remaining_minutes}分{remaining_seconds}秒\n"
                f"💰 每次寻找消耗 1{sakura_b}\n"
                f"🎒 背包装备: {equipment_count}/30\n"
                f"🔍 找到的装备: {active_hunt.equipment_found}个\n\n"
                f"点击下方按钮进行寻找装备！",
                buttons=hunt_game_ikb(active_hunt.id)
            )
    
    # 开始新游戏
    hunt_id = sql_start_hunt(msg.from_user.id)
    if hunt_id == -1:
        return await sendMessage(msg, f"❌ 您今日已进行了 5 次车库游戏，请明日再来")
    elif hunt_id == -2:
        return await sendMessage(msg, "❌ 您已有进行中的车库游戏")
    elif hunt_id == 0:
        return await sendMessage(msg, "❌ 开始车库游戏失败，请稍后重试")
    
    # 获取今日汽车
    daily_car = sql_get_daily_car()
    car_name = daily_car.car_name if daily_car else "未知"
    required_equipment = daily_car.equipment_ids if daily_car else "5,12,6,15,1"
    
    await sendMessage(
        msg,
        f"🏎️ **车库游戏开始！**\n\n"
        f"🎯 今日目标汽车: **{car_name}**\n"
        f"🔧 需要装备: {required_equipment}\n"
        f"⏰ 游戏时间: 30分钟\n"
        f"💰 每次寻找消耗 1{sakura_b}\n"
        f"🔄 寻找冷却: 1秒\n"
        f"🎒 背包容量: 30个装备\n"
        f"📅 装备仅当天有效\n\n"
        f"**今日剩余游戏次数: {5 - today_count - 1}**\n\n"
        f"点击下方按钮开始寻找装备！",
        buttons=hunt_game_ikb(hunt_id)
    )


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
        return await editMessage(call, "⏰ 车库游戏时间已结束！\n\n感谢参与，请明日再来！")
    
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
    
    # 检查背包是否已满
    current_equipment_count = sql_count_user_equipment(call.from_user.id, today_only=True)
    if current_equipment_count >= 30:
        return await callAnswer(call, "❌ 背包已满！请先丢弃一些装备", show_alert=True)
    
    # 扣除金币
    if not sql_update_emby(Emby.tg == call.from_user.id, iv=user.iv - 1):
        return await callAnswer(call, "❌ 扣除金币失败", show_alert=True)
    
    # 根据稀有度权重随机获得装备
    equipment_id = sql_random_equipment_by_rarity()
    
    if equipment_id:
        # 获取装备定义
        equipment_def = sql_get_equipment_definition(equipment_id)
        if equipment_def:
            equipment_name = equipment_def.equipment_name
            equipment_category = equipment_def.category
            color_emoji = get_equipment_color_emoji(equipment_category)
            
            # 显示装备选择界面
            await callAnswer(call, f"🎉 发现了{equipment_name}！")
            await editMessage(
                call,
                f"🔍 **发现装备！**\n\n"
                f"{color_emoji} **{equipment_name}**\n"
                f"📝 {equipment_def.description}\n"
                f"🏷️ 类别: {equipment_category}\n\n"
                f"🎒 当前背包: {current_equipment_count}/30\n\n"
                f"是否保留这个装备？",
                buttons=equipment_choice_ikb(hunt_id, equipment_id)
            )
        else:
            # 如果装备定义不存在，退还金币
            sql_update_emby(Emby.tg == call.from_user.id, iv=user.iv)
            await callAnswer(call, "❌ 寻找失败，请重试", show_alert=True)
    else:
        # 如果随机装备失败，退还金币
        sql_update_emby(Emby.tg == call.from_user.id, iv=user.iv)
        await callAnswer(call, "❌ 寻找失败，请重试", show_alert=True)


@bot.on_callback_query(filters.regex(r'^keep_equipment_(\d+)_(\d+)$'))
async def keep_equipment(_, call):
    """保留装备"""
    hunt_id = int(call.matches[0].group(1))
    equipment_id = int(call.matches[0].group(2))
    
    # 验证游戏会话
    hunt = sql_get_active_hunt(call.from_user.id)
    if not hunt or hunt.id != hunt_id:
        return await callAnswer(call, "❌ 游戏会话无效", show_alert=True)
    
    # 再次检查背包容量
    current_equipment_count = sql_count_user_equipment(call.from_user.id, today_only=True)
    if current_equipment_count >= 30:
        return await callAnswer(call, "❌ 背包已满！无法保留装备", show_alert=True)
    
    # 添加装备到背包
    if sql_add_equipment(call.from_user.id, hunt_id, equipment_id):
        # 更新游戏界面
        remaining_time = 1800 - int((datetime.datetime.now() - hunt.start_time).total_seconds())
        remaining_minutes = remaining_time // 60
        remaining_seconds = remaining_time % 60
        
        # 获取今日汽车
        daily_car = sql_get_daily_car()
        car_name = daily_car.car_name if daily_car else "未知"
        
        # 刷新hunt对象
        hunt = sql_get_active_hunt(call.from_user.id)
        
        # 获取装备信息
        equipment_def = sql_get_equipment_definition(equipment_id)
        equipment_name = equipment_def.equipment_name if equipment_def else f"装备 {equipment_id}"
        
        # 获取用户当前金币
        user = sql_get_emby(call.from_user.id)
        current_coins = user.iv if user else 0
        
        await callAnswer(call, f"✅ 已保留{equipment_name}！")
        await editMessage(
            call,
            f"🏎️ **车库游戏进行中**\n\n"
            f"🎯 今日目标汽车: **{car_name}**\n"
            f"⏰ 剩余时间: {remaining_minutes}分{remaining_seconds}秒\n"
            f"💰 当前{sakura_b}: {current_coins}\n"
            f"🎒 背包装备: {current_equipment_count + 1}/30\n"
            f"🔍 找到的装备: {hunt.equipment_found}个\n"
            f"🆕 刚保留: {equipment_name}\n\n"
            f"继续寻找装备吧！",
            buttons=hunt_game_ikb(hunt_id, int(datetime.datetime.now().timestamp()))
        )
    else:
        await callAnswer(call, "❌ 保留装备失败", show_alert=True)


@bot.on_callback_query(filters.regex(r'^discard_equipment_(\d+)_(\d+)$'))
async def discard_equipment(_, call):
    """丢弃装备"""
    hunt_id = int(call.matches[0].group(1))
    equipment_id = int(call.matches[0].group(2))
    
    # 验证游戏会话
    hunt = sql_get_active_hunt(call.from_user.id)
    if not hunt or hunt.id != hunt_id:
        return await callAnswer(call, "❌ 游戏会话无效", show_alert=True)
    
    # 获取装备信息
    equipment_def = sql_get_equipment_definition(equipment_id)
    equipment_name = equipment_def.equipment_name if equipment_def else f"装备 {equipment_id}"
    
    # 更新游戏界面
    remaining_time = 1800 - int((datetime.datetime.now() - hunt.start_time).total_seconds())
    remaining_minutes = remaining_time // 60
    remaining_seconds = remaining_time % 60
    
    # 获取今日汽车
    daily_car = sql_get_daily_car()
    car_name = daily_car.car_name if daily_car else "未知"
    
    # 获取用户当前金币和背包数量
    user = sql_get_emby(call.from_user.id)
    current_coins = user.iv if user else 0
    current_equipment_count = sql_count_user_equipment(call.from_user.id, today_only=True)
    
    await callAnswer(call, f"🗑️ 已丢弃{equipment_name}")
    await editMessage(
        call,
        f"🏎️ **车库游戏进行中**\n\n"
        f"🎯 今日目标汽车: **{car_name}**\n"
        f"⏰ 剩余时间: {remaining_minutes}分{remaining_seconds}秒\n"
        f"💰 当前{sakura_b}: {current_coins}\n"
        f"🎒 背包装备: {current_equipment_count}/30\n"
        f"🔍 找到的装备: {hunt.equipment_found}个\n"
        f"🗑️ 刚丢弃: {equipment_name}\n\n"
        f"继续寻找装备吧！",
        buttons=hunt_game_ikb(hunt_id, int(datetime.datetime.now().timestamp()))
    )


@bot.on_callback_query(filters.regex(r'^hunt_inventory_(\d+)$'))
async def hunt_inventory(_, call):
    """查看背包"""
    hunt_id = int(call.matches[0].group(1))
    
    # 验证游戏会话
    hunt = sql_get_active_hunt(call.from_user.id)
    if not hunt or hunt.id != hunt_id:
        return await callAnswer(call, "❌ 游戏会话无效", show_alert=True)
    
    # 获取用户装备
    equipment_list = sql_get_user_equipment(call.from_user.id, today_only=True)
    
    # 统计装备
    equipment_counts = {}
    for equip in equipment_list:
        equipment_counts[equip.equipment_id] = equipment_counts.get(equip.equipment_id, 0) + 1
    
    # 创建背包显示
    inventory_text = "🎒 **背包内容**\n\n"
    if equipment_counts:
        for equipment_id in sorted(equipment_counts.keys()):
            count = equipment_counts[equipment_id]
            # 获取装备定义以显示更好的名称和颜色
            equipment_def = sql_get_equipment_definition(equipment_id)
            if equipment_def:
                equipment_name = equipment_def.equipment_name
                color_emoji = get_equipment_color_emoji(equipment_def.category)
                inventory_text += f"{color_emoji} {equipment_name}: {count}个\n"
            else:
                inventory_text += f"⚪ 装备 {equipment_id}: {count}个\n"
        
        inventory_text += f"\n📊 总数: {len(equipment_list)}/30"
    else:
        inventory_text += "空空如也...\n"
    
    inventory_text += "\n💡 提示：装备仅当天有效"
    
    await callAnswer(call, "🎒 查看背包")
    await editMessage(call, inventory_text, buttons=hunt_inventory_ikb(hunt_id))


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
    
    # 获取用户装备统计
    equipment_list = sql_get_user_equipment(call.from_user.id, today_only=True)
    equipment_counts = {}
    for equip in equipment_list:
        equipment_counts[equip.equipment_id] = equipment_counts.get(equip.equipment_id, 0) + 1
    
    required_equipment = [int(x) for x in daily_car.equipment_ids.split(',')]
    
    assembly_text = f"🔧 **汽车组装**\n\n"
    assembly_text += f"🏎️ 今日目标: **{daily_car.car_name}**\n"
    assembly_text += f"📝 描述: {daily_car.description}\n\n"
    assembly_text += f"📋 **需要装备:**\n"
    
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
    if sql_assemble_car(call.from_user.id, car_id):
        # 获取汽车信息
        daily_car = sql_get_daily_car()
        car_name = daily_car.car_name if daily_car else "神秘汽车"
        
        await callAnswer(call, f"🎉 成功组装 {car_name}！")
        await editMessage(
            call,
            f"✨ **组装成功！**\n\n"
            f"🏎️ 恭喜您获得汽车: **{car_name}**\n"
            f"📝 {daily_car.description if daily_car else ''}\n\n"
            f"🎮 继续游戏可以获得更多装备！",
            buttons=hunt_game_ikb(hunt_id)
        )
    else:
        await callAnswer(call, "❌ 组装失败，请检查装备", show_alert=True)


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
        
        # 获取用户今日装备
        equipment_list = sql_get_user_equipment(call.from_user.id, today_only=True)
        equipment_counts = {}
        for equip in equipment_list:
            equipment_counts[equip.equipment_id] = equipment_counts.get(equip.equipment_id, 0) + 1
        
        result_text = f"🏁 **车库游戏结束**\n\n"
        result_text += f"⏱️ 游戏时长: {duration_minutes}分{duration_seconds}秒\n"
        result_text += f"🔍 找到装备: {hunt.equipment_found}个\n"
        result_text += f"💰 消耗{sakura_b}: {hunt.coins_spent}\n\n"
        result_text += f"🎒 **当前背包:**\n"
        
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
    
    # 获取用户当前金币和背包数量
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
        f"🎒 背包装备: {equipment_count}/30\n"
        f"🔍 找到的装备: {hunt.equipment_found}个\n\n"
        f"点击下方按钮继续寻找装备！",
        buttons=hunt_game_ikb(hunt_id)
    )