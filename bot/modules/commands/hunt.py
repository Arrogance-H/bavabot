"""
寻宝游戏命令
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
    sql_start_hunt, sql_end_hunt, sql_get_active_hunt, sql_add_fragment,
    sql_get_user_fragments, sql_get_today_hunt_count, sql_get_daily_treasure,
    sql_check_treasure_synthesis, sql_synthesize_treasure
)


# 寻宝游戏按钮
def hunt_game_ikb(hunt_id: int, last_hunt_time: int = 0):
    """创建寻宝游戏按钮"""
    current_time = int(datetime.datetime.now().timestamp())
    cooldown_remaining = max(0, 1 - (current_time - last_hunt_time))  # 1秒冷却
    can_hunt = cooldown_remaining == 0
    
    if can_hunt:
        hunt_btn_text = "🎯 寻宝"
    else:
        hunt_btn_text = f"⏰ 寻宝 ({cooldown_remaining}s)"
    
    return ikb([
        [(hunt_btn_text, f"hunt_action_{hunt_id}")],
        [("📦 背包", f"hunt_inventory_{hunt_id}"), ("🔧 合成", f"hunt_synthesis_{hunt_id}")],
        [("❌ 结束游戏", f"hunt_end_{hunt_id}")]
    ])


def hunt_inventory_ikb(hunt_id: int):
    """背包界面按钮"""
    return ikb([
        [("🔧 合成宝物", f"hunt_synthesis_{hunt_id}")],
        [("🔙 返回游戏", f"hunt_game_{hunt_id}")]
    ])


def hunt_synthesis_ikb(hunt_id: int, treasure_id: int = None):
    """合成界面按钮"""
    buttons = []
    if treasure_id:
        buttons.append([("✨ 合成", f"hunt_do_synthesis_{hunt_id}_{treasure_id}")])
    
    buttons.extend([
        [("📦 背包", f"hunt_inventory_{hunt_id}")],
        [("🔙 返回游戏", f"hunt_game_{hunt_id}")]
    ])
    
    return ikb(buttons)


@bot.on_message(filters.command('hunt', prefixes) & user_in_group_on_filter)
async def start_hunt(_, msg):
    """开始寻宝游戏"""
    await msg.delete()
    
    user = sql_get_emby(msg.from_user.id)
    if not user:
        return await sendMessage(msg, "❌ 请先私聊机器人进行注册")
    
    # 检查今日游戏次数
    today_count = sql_get_today_hunt_count(msg.from_user.id)
    if today_count >= 5:
        return await sendMessage(msg, f"❌ 您今日已进行了 {today_count} 次寻宝，每日限制 5 次")
    
    # 检查是否有进行中的游戏
    active_hunt = sql_get_active_hunt(msg.from_user.id)
    if active_hunt:
        # 检查游戏是否超时（30分钟）
        start_time = active_hunt.start_time
        current_time = datetime.datetime.now()
        if (current_time - start_time).total_seconds() > 1800:  # 30分钟
            sql_end_hunt(active_hunt.id)
            return await sendMessage(msg, "⏰ 您的上一场寻宝游戏已超时结束，请重新开始")
        else:
            remaining_time = 1800 - int((current_time - start_time).total_seconds())
            remaining_minutes = remaining_time // 60
            remaining_seconds = remaining_time % 60
            
            # 获取今日宝物
            daily_treasure = sql_get_daily_treasure()
            treasure_name = daily_treasure.treasure_name if daily_treasure else "未知"
            
            return await sendMessage(
                msg,
                f"🎮 **寻宝游戏进行中**\n\n"
                f"🎯 今日目标宝物: **{treasure_name}**\n"
                f"⏰ 剩余时间: {remaining_minutes}分{remaining_seconds}秒\n"
                f"💰 每次寻宝消耗 1{sakura_b}\n"
                f"🎲 找到的碎片: {active_hunt.fragments_found}个\n\n"
                f"点击下方按钮进行寻宝！",
                buttons=hunt_game_ikb(active_hunt.id)
            )
    
    # 开始新游戏
    hunt_id = sql_start_hunt(msg.from_user.id)
    if hunt_id == -1:
        return await sendMessage(msg, f"❌ 您今日已进行了 5 次寻宝，请明日再来")
    elif hunt_id == -2:
        return await sendMessage(msg, "❌ 您已有进行中的寻宝游戏")
    elif hunt_id == 0:
        return await sendMessage(msg, "❌ 开始寻宝失败，请稍后重试")
    
    # 获取今日宝物
    daily_treasure = sql_get_daily_treasure()
    treasure_name = daily_treasure.treasure_name if daily_treasure else "未知"
    required_fragments = daily_treasure.fragment_ids if daily_treasure else "1,2,3"
    
    await sendMessage(
        msg,
        f"🎮 **寻宝游戏开始！**\n\n"
        f"🎯 今日目标宝物: **{treasure_name}**\n"
        f"🧩 需要碎片: {required_fragments}\n"
        f"⏰ 游戏时间: 30分钟\n"
        f"💰 每次寻宝消耗 1{sakura_b}\n"
        f"🔄 寻宝冷却: 1秒\n"
        f"📅 碎片仅当天有效\n\n"
        f"**今日剩余游戏次数: {5 - today_count - 1}**\n\n"
        f"点击下方按钮开始寻宝！",
        buttons=hunt_game_ikb(hunt_id)
    )


@bot.on_callback_query(filters.regex(r'^hunt_action_(\d+)$'))
async def hunt_action(_, call):
    """寻宝动作"""
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
        return await editMessage(call, "⏰ 寻宝游戏时间已结束！\n\n感谢参与，请明日再来！")
    
    # 检查1秒冷却时间
    if hunt.last_hunt_time:
        time_since_last = (current_time - hunt.last_hunt_time).total_seconds()
        if time_since_last < 1:
            remaining = 1 - time_since_last
            return await callAnswer(call, f"⏰ 请等待 {remaining:.1f} 秒后再寻宝", show_alert=True)
    
    # 检查用户金币
    user = sql_get_emby(call.from_user.id)
    if not user or user.iv < 1:
        return await callAnswer(call, f"❌ {sakura_b}不足，需要 1{sakura_b}", show_alert=True)
    
    # 扣除金币
    if not sql_update_emby(Emby.tg == call.from_user.id, iv=user.iv - 1):
        return await callAnswer(call, "❌ 扣除金币失败", show_alert=True)
    
    # 随机获得碎片（1-6）
    fragment_id = random.randint(1, 6)
    
    if sql_add_fragment(call.from_user.id, hunt_id, fragment_id):
        # 更新游戏界面
        remaining_time = 1800 - int((current_time - start_time).total_seconds())
        remaining_minutes = remaining_time // 60
        remaining_seconds = remaining_time % 60
        
        # 获取今日宝物
        daily_treasure = sql_get_daily_treasure()
        treasure_name = daily_treasure.treasure_name if daily_treasure else "未知"
        
        # 刷新hunt对象
        hunt = sql_get_active_hunt(call.from_user.id)
        
        await callAnswer(call, f"🎉 获得碎片 {fragment_id}！")
        await editMessage(
            call,
            f"🎮 **寻宝游戏进行中**\n\n"
            f"🎯 今日目标宝物: **{treasure_name}**\n"
            f"⏰ 剩余时间: {remaining_minutes}分{remaining_seconds}秒\n"
            f"💰 当前{sakura_b}: {user.iv - 1}\n"
            f"🎲 找到的碎片: {hunt.fragments_found}个\n"
            f"🆕 刚获得: 碎片 {fragment_id}\n\n"
            f"继续寻宝吧！",
            buttons=hunt_game_ikb(hunt_id, int(current_time.timestamp()))
        )
    else:
        # 如果添加碎片失败，退还金币
        sql_update_emby(Emby.tg == call.from_user.id, iv=user.iv)
        await callAnswer(call, "❌ 寻宝失败，请重试", show_alert=True)


@bot.on_callback_query(filters.regex(r'^hunt_inventory_(\d+)$'))
async def hunt_inventory(_, call):
    """查看背包"""
    hunt_id = int(call.matches[0].group(1))
    
    # 验证游戏会话
    hunt = sql_get_active_hunt(call.from_user.id)
    if not hunt or hunt.id != hunt_id:
        return await callAnswer(call, "❌ 游戏会话无效", show_alert=True)
    
    # 获取用户碎片
    fragments = sql_get_user_fragments(call.from_user.id, today_only=True)
    
    # 统计碎片
    fragment_counts = {}
    for frag in fragments:
        fragment_counts[frag.fragment_id] = fragment_counts.get(frag.fragment_id, 0) + 1
    
    # 创建背包显示
    inventory_text = "📦 **背包内容**\n\n"
    if fragment_counts:
        for fragment_id in sorted(fragment_counts.keys()):
            count = fragment_counts[fragment_id]
            inventory_text += f"🧩 碎片 {fragment_id}: {count}个\n"
    else:
        inventory_text += "空空如也...\n"
    
    inventory_text += "\n💡 提示：碎片仅当天有效"
    
    await callAnswer(call, "📦 查看背包")
    await editMessage(call, inventory_text, buttons=hunt_inventory_ikb(hunt_id))


@bot.on_callback_query(filters.regex(r'^hunt_synthesis_(\d+)$'))
async def hunt_synthesis(_, call):
    """宝物合成界面"""
    hunt_id = int(call.matches[0].group(1))
    
    # 验证游戏会话
    hunt = sql_get_active_hunt(call.from_user.id)
    if not hunt or hunt.id != hunt_id:
        return await callAnswer(call, "❌ 游戏会话无效", show_alert=True)
    
    # 获取今日宝物
    daily_treasure = sql_get_daily_treasure()
    if not daily_treasure:
        return await callAnswer(call, "❌ 今日宝物配置错误", show_alert=True)
    
    # 检查是否可以合成
    can_synthesize = sql_check_treasure_synthesis(call.from_user.id, daily_treasure.id)
    
    # 获取用户碎片统计
    fragments = sql_get_user_fragments(call.from_user.id, today_only=True)
    fragment_counts = {}
    for frag in fragments:
        fragment_counts[frag.fragment_id] = fragment_counts.get(frag.fragment_id, 0) + 1
    
    required_fragments = [int(x) for x in daily_treasure.fragment_ids.split(',')]
    
    synthesis_text = f"🔧 **宝物合成**\n\n"
    synthesis_text += f"🎯 今日目标: **{daily_treasure.treasure_name}**\n"
    synthesis_text += f"📝 描述: {daily_treasure.description}\n\n"
    synthesis_text += f"📋 **需要碎片:**\n"
    
    for req_id in required_fragments:
        have_count = fragment_counts.get(req_id, 0)
        status = "✅" if have_count >= 1 else "❌"
        synthesis_text += f"{status} 碎片 {req_id}: {have_count}/1\n"
    
    if can_synthesize:
        synthesis_text += f"\n🎉 **可以合成！**"
    else:
        synthesis_text += f"\n❌ **碎片不足，无法合成**"
    
    await callAnswer(call, "🔧 宝物合成")
    await editMessage(
        call, 
        synthesis_text, 
        buttons=hunt_synthesis_ikb(hunt_id, daily_treasure.id if can_synthesize else None)
    )


@bot.on_callback_query(filters.regex(r'^hunt_do_synthesis_(\d+)_(\d+)$'))
async def hunt_do_synthesis(_, call):
    """执行宝物合成"""
    hunt_id = int(call.matches[0].group(1))
    treasure_id = int(call.matches[0].group(2))
    
    # 验证游戏会话
    hunt = sql_get_active_hunt(call.from_user.id)
    if not hunt or hunt.id != hunt_id:
        return await callAnswer(call, "❌ 游戏会话无效", show_alert=True)
    
    # 执行合成
    if sql_synthesize_treasure(call.from_user.id, treasure_id):
        # 获取宝物信息
        daily_treasure = sql_get_daily_treasure()
        treasure_name = daily_treasure.treasure_name if daily_treasure else "神秘宝物"
        
        await callAnswer(call, f"🎉 成功合成 {treasure_name}！")
        await editMessage(
            call,
            f"✨ **合成成功！**\n\n"
            f"🎊 恭喜您获得宝物: **{treasure_name}**\n"
            f"📝 {daily_treasure.description if daily_treasure else ''}\n\n"
            f"🎮 继续游戏可以获得更多碎片！",
            buttons=hunt_game_ikb(hunt_id)
        )
    else:
        await callAnswer(call, "❌ 合成失败，请检查碎片", show_alert=True)


@bot.on_callback_query(filters.regex(r'^hunt_end_(\d+)$'))
async def hunt_end(_, call):
    """结束寻宝游戏"""
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
        
        # 获取用户今日碎片
        fragments = sql_get_user_fragments(call.from_user.id, today_only=True)
        fragment_counts = {}
        for frag in fragments:
            fragment_counts[frag.fragment_id] = fragment_counts.get(frag.fragment_id, 0) + 1
        
        result_text = f"🏁 **寻宝游戏结束**\n\n"
        result_text += f"⏱️ 游戏时长: {duration_minutes}分{duration_seconds}秒\n"
        result_text += f"🎲 找到碎片: {hunt.fragments_found}个\n"
        result_text += f"💰 消耗{sakura_b}: {hunt.coins_spent}\n\n"
        result_text += f"📦 **当前背包:**\n"
        
        if fragment_counts:
            for fragment_id in sorted(fragment_counts.keys()):
                count = fragment_counts[fragment_id]
                result_text += f"🧩 碎片 {fragment_id}: {count}个\n"
        else:
            result_text += "空空如也...\n"
        
        result_text += f"\n💡 记住：碎片仅当天有效哦！\n感谢参与寻宝游戏！"
        
        await callAnswer(call, "🏁 游戏结束")
        await editMessage(call, result_text)
    else:
        await callAnswer(call, "❌ 结束游戏失败", show_alert=True)


@bot.on_callback_query(filters.regex(r'^hunt_game_(\d+)$'))
async def hunt_game_return(_, call):
    """返回游戏界面"""
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
        return await editMessage(call, "⏰ 寻宝游戏时间已结束！\n\n感谢参与，请明日再来！")
    
    remaining_time = 1800 - int((current_time - start_time).total_seconds())
    remaining_minutes = remaining_time // 60
    remaining_seconds = remaining_time % 60
    
    # 获取今日宝物
    daily_treasure = sql_get_daily_treasure()
    treasure_name = daily_treasure.treasure_name if daily_treasure else "未知"
    
    # 获取用户当前金币
    user = sql_get_emby(call.from_user.id)
    current_coins = user.iv if user else 0
    
    await callAnswer(call, "🎮 返回游戏")
    await editMessage(
        call,
        f"🎮 **寻宝游戏进行中**\n\n"
        f"🎯 今日目标宝物: **{treasure_name}**\n"
        f"⏰ 剩余时间: {remaining_minutes}分{remaining_seconds}秒\n"
        f"💰 当前{sakura_b}: {current_coins}\n"
        f"🎲 找到的碎片: {hunt.fragments_found}个\n\n"
        f"点击下方按钮继续寻宝！",
        buttons=hunt_game_ikb(hunt_id)
    )