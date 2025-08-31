"""
车库游戏管理命令
"""
import datetime
from pyrogram import filters
from bot import bot, prefixes, sakura_b, LOGGER
from bot.func_helper.filters import user_in_group_on_filter
from bot.func_helper.msg_utils import sendMessage
from bot.sql_helper.sql_emby import sql_get_emby
from bot.sql_helper.sql_hunt import (
    sql_update_reward_config, sql_get_reward_config, 
    sql_get_probability_stats, Car, RewardConfig
)
from bot.sql_helper import Session


@bot.on_message(filters.command('hunt_config_reward', prefixes) & user_in_group_on_filter)
async def config_hunt_reward(_, msg):
    """配置车库游戏奖励 - 仅管理员使用"""
    await msg.delete()
    
    user = sql_get_emby(msg.from_user.id)
    if not user:
        return await sendMessage(msg, "❌ 请先私聊机器人进行注册")
    
    # 简单的管理员检查 - 这里可以根据实际需求修改权限检查逻辑
    # if not user.is_admin:  # 假设有管理员字段
    #     return await sendMessage(msg, "❌ 仅管理员可以使用此命令")
    
    # 解析命令参数
    args = msg.text.split()
    if len(args) < 4:
        help_text = """
🔧 **车库奖励配置帮助**

**用法:** `/hunt_config_reward <车型ID> <奖励类型> <奖励值> [描述]`

**参数说明:**
- 车型ID: 1=赞德福特蓝M2, 2=曼岛绿M3, 3=圣保罗黄M4, 4=风暴灰M5
- 奖励类型: coins(金币), title(称号), badge(徽章)
- 奖励值: 金币数量或称号名称
- 描述: 可选的奖励描述

**示例:**
`/hunt_config_reward 1 coins 100 组装M2获得100金币`
`/hunt_config_reward 2 title M3车主 曼岛绿M3专属称号`
        """
        return await sendMessage(msg, help_text)
    
    try:
        car_id = int(args[1])
        reward_type = args[2]
        reward_value = args[3]
        reward_description = " ".join(args[4:]) if len(args) > 4 else None
        
        # 验证车型ID
        if car_id not in [1, 2, 3, 4]:
            return await sendMessage(msg, "❌ 车型ID必须为1-4之间")
        
        # 验证奖励类型
        if reward_type not in ['coins', 'title', 'badge']:
            return await sendMessage(msg, "❌ 奖励类型必须为 coins, title 或 badge")
        
        # 验证金币奖励值
        if reward_type == 'coins':
            try:
                coin_amount = int(reward_value)
                if coin_amount <= 0:
                    return await sendMessage(msg, "❌ 金币数量必须大于0")
            except ValueError:
                return await sendMessage(msg, "❌ 金币数量必须为有效数字")
        
        # 更新奖励配置
        if sql_update_reward_config(car_id, reward_type, reward_value, reward_description):
            car_names = {1: "赞德福特蓝M2", 2: "曼岛绿M3", 3: "圣保罗黄M4", 4: "风暴灰M5"}
            car_name = car_names.get(car_id, f"汽车{car_id}")
            
            await sendMessage(
                msg,
                f"✅ **奖励配置成功**\n\n"
                f"🏎️ 汽车: {car_name}\n"
                f"🎁 奖励类型: {reward_type}\n"
                f"💎 奖励值: {reward_value}\n"
                f"📝 描述: {reward_description or '无'}"
            )
        else:
            await sendMessage(msg, "❌ 奖励配置失败，请稍后重试")
            
    except ValueError:
        await sendMessage(msg, "❌ 车型ID必须为有效数字")
    except Exception as e:
        LOGGER.error(f"配置奖励失败: {e}")
        await sendMessage(msg, "❌ 配置失败，请检查参数格式")


@bot.on_message(filters.command('hunt_list_rewards', prefixes) & user_in_group_on_filter)
async def list_hunt_rewards(_, msg):
    """查看当前奖励配置"""
    await msg.delete()
    
    user = sql_get_emby(msg.from_user.id)
    if not user:
        return await sendMessage(msg, "❌ 请先私聊机器人进行注册")
    
    try:
        with Session() as session:
            # 获取所有奖励配置
            reward_configs = session.query(RewardConfig).filter(
                RewardConfig.is_active == True
            ).all()
            
            if not reward_configs:
                return await sendMessage(msg, "❌ 暂无奖励配置")
            
            # 获取汽车信息
            cars = session.query(Car).all()
            car_dict = {car.id: car.car_name for car in cars}
            
            reward_text = "🎁 **当前奖励配置**\n\n"
            
            for config in reward_configs:
                car_name = car_dict.get(config.car_id, f"汽车{config.car_id}")
                reward_text += f"🏎️ **{car_name}**\n"
                reward_text += f"   类型: {config.reward_type}\n"
                reward_text += f"   奖励: {config.reward_value}\n"
                if config.reward_description:
                    reward_text += f"   描述: {config.reward_description}\n"
                reward_text += "\n"
            
            # 添加概率信息
            prob_stats = sql_get_probability_stats()
            reward_text += "📊 **装备概率信息**\n"
            reward_text += f"🟣 紫色: {prob_stats['purple']['probability']}\n"
            reward_text += f"🟡 金色: {prob_stats['gold']['probability']}\n"
            reward_text += f"🟢 绿色: {prob_stats['green']['probability']}\n"
            reward_text += f"🔵 蓝色: {prob_stats['blue']['probability']}"
            
            await sendMessage(msg, reward_text)
            
    except Exception as e:
        LOGGER.error(f"查看奖励配置失败: {e}")
        await sendMessage(msg, "❌ 查看配置失败")


@bot.on_message(filters.command('hunt_stats', prefixes) & user_in_group_on_filter)
async def hunt_statistics(_, msg):
    """查看车库游戏统计信息"""
    await msg.delete()
    
    try:
        from bot.sql_helper.sql_hunt import (
            Hunt, Equipment, AssemblyReward
        )
        
        with Session() as session:
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            
            # 今日游戏统计
            today_hunts = session.query(Hunt).filter(Hunt.game_date == today).count()
            today_equipment = session.query(Equipment).filter(Equipment.obtained_date == today).count()
            today_assemblies = session.query(AssemblyReward).filter(AssemblyReward.obtained_date == today).count()
            
            # 用户个人统计
            user_today_hunts = session.query(Hunt).filter(
                Hunt.tg == msg.from_user.id, Hunt.game_date == today
            ).count()
            
            user_today_equipment = session.query(Equipment).filter(
                Equipment.tg == msg.from_user.id, Equipment.obtained_date == today
            ).count()
            
            user_today_rewards = session.query(AssemblyReward).filter(
                AssemblyReward.tg == msg.from_user.id, AssemblyReward.obtained_date == today
            ).count()
            
            stats_text = f"📊 **车库游戏统计**\n\n"
            stats_text += f"📅 **今日全服数据:**\n"
            stats_text += f"🎮 游戏场次: {today_hunts}\n"
            stats_text += f"🔍 发现装备: {today_equipment}\n"
            stats_text += f"🏎️ 完成组装: {today_assemblies}\n\n"
            
            stats_text += f"👤 **您的今日数据:**\n"
            stats_text += f"🎮 游戏场次: {user_today_hunts}/5\n"
            stats_text += f"🔍 发现装备: {user_today_equipment}\n"
            stats_text += f"🏎️ 完成组装: {user_today_rewards}\n"
            
            await sendMessage(msg, stats_text)
            
    except Exception as e:
        LOGGER.error(f"查看统计信息失败: {e}")
        await sendMessage(msg, "❌ 获取统计信息失败")