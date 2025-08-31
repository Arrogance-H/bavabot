"""
车库游戏管理命令
"""
import datetime
import json
import os
from pyrogram import filters
from bot import bot, prefixes, sakura_b, LOGGER, hunt_daily_limit
from bot.func_helper.filters import user_in_group_on_filter
from bot.func_helper.msg_utils import sendMessage
from bot.sql_helper.sql_emby import sql_get_emby
from bot.sql_helper.sql_hunt import (
    sql_update_reward_config, sql_get_reward_config, 
    sql_get_probability_stats, Car, RewardConfig,
    sql_set_reward_button, sql_get_reward_button, RewardButton
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
- 奖励类型: coins({sakura_b}), title(称号), badge(徽章), code(注册码), white(白名单)
- 奖励值: {sakura_b}数量、称号名称、注册码数量或白名单数量
- 描述: 可选的奖励描述

**示例:**
`/hunt_config_reward 1 coins 100 组装M2获得100{sakura_b}`
`/hunt_config_reward 2 title M3车主 曼岛绿M3专属称号`
`/hunt_config_reward 3 code 1 组装M4获得1个注册码`
`/hunt_config_reward 4 white 1 组装M5获得1个白名单`
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
        if reward_type not in ['coins', 'title', 'badge', 'code', 'white']:
            return await sendMessage(msg, "❌ 奖励类型必须为 coins, title, badge, code 或 white")
        
        # 验证数值类型的奖励值
        if reward_type in ['coins', 'code', 'white']:
            try:
                amount = int(reward_value)
                if amount <= 0:
                    reward_name = {
                        'coins': f"{sakura_b}数量",
                        'code': "注册码数量", 
                        'white': "白名单数量"
                    }[reward_type]
                    return await sendMessage(msg, f"❌ {reward_name}必须大于0")
            except ValueError:
                reward_name = {
                    'coins': f"{sakura_b}数量",
                    'code': "注册码数量",
                    'white': "白名单数量"
                }[reward_type]
                return await sendMessage(msg, f"❌ {reward_name}必须为有效数字")
        
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
            
            # 添加概率信息 - 按高到低排序显示
            prob_stats = sql_get_probability_stats()
            reward_text += "📊 **装备概率信息**\n"
            reward_text += f"🔵 蓝色: {prob_stats['blue']['probability']}\n"
            reward_text += f"🟢 绿色: {prob_stats['green']['probability']}\n"
            reward_text += f"🟡 金色: {prob_stats['gold']['probability']}\n"
            reward_text += f"🟣 紫色: {prob_stats['purple']['probability']}"
            
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
            stats_text += f"🎮 游戏场次: {user_today_hunts}/{hunt_daily_limit}\n"
            stats_text += f"🔍 发现装备: {user_today_equipment}\n"
            stats_text += f"🏎️ 完成组装: {user_today_rewards}\n"
            
            await sendMessage(msg, stats_text)
            
    except Exception as e:
        LOGGER.error(f"查看统计信息失败: {e}")
        await sendMessage(msg, "❌ 获取统计信息失败")


@bot.on_message(filters.command('hunt_config_button', prefixes) & user_in_group_on_filter)
async def config_hunt_button(_, msg):
    """配置车库游戏自定义奖励按钮 - 仅管理员使用"""
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
🔧 **车库奖励按钮配置帮助**

**用法:** `/hunt_config_button <车型ID> <按钮文字> <跳转URL>`

**参数说明:**
- 车型ID: 1=赞德福特蓝M2, 2=曼岛绿M3, 3=圣保罗黄M4, 4=风暴灰M5
- 按钮文字: 按钮显示的文字（如：🎁 领取专属奖励）
- 跳转URL: 点击按钮后跳转的网址

**示例:**
`/hunt_config_button 1 🎁 领取M2奖励 https://example.com/reward1`
`/hunt_config_button 2 🏆 查看称号 https://example.com/title2`

**注意:** 按钮仅在用户成功组装汽车后显示
        """
        return await sendMessage(msg, help_text)
    
    try:
        car_id = int(args[1])
        # 处理包含空格的按钮文字和URL
        parts = msg.text.split(None, 3)  # 最多分割3次
        if len(parts) < 4:
            return await sendMessage(msg, "❌ 参数不完整，请提供按钮文字和URL")
        
        # 从第三个参数开始可能包含空格，需要特殊处理
        remaining_text = parts[3]
        # 寻找最后一个以http开头的部分作为URL
        words = remaining_text.split()
        url = None
        button_text_words = []
        
        for i, word in enumerate(words):
            if word.startswith('http'):
                url = word
                button_text_words = words[:i]
                break
        
        if not url:
            return await sendMessage(msg, "❌ 未找到有效的URL（必须以http开头）")
        
        if not button_text_words:
            return await sendMessage(msg, "❌ 按钮文字不能为空")
        
        button_text = ' '.join(button_text_words)
        
        # 验证车型ID
        with Session() as session:
            car = session.query(Car).filter(Car.id == car_id).first()
            if not car:
                return await sendMessage(msg, f"❌ 车型ID {car_id} 不存在")
            
            car_name = car.car_name
        
        # 设置奖励按钮
        if sql_set_reward_button(car_id, button_text, url):
            await sendMessage(
                msg, 
                f"✅ **奖励按钮配置成功！**\n\n"
                f"🏎️ 汽车: {car_name}\n"
                f"🔘 按钮文字: {button_text}\n"
                f"🔗 跳转链接: {url}\n\n"
                f"💡 用户组装此汽车后将看到自定义按钮"
            )
        else:
            await sendMessage(msg, "❌ 配置奖励按钮失败")
            
    except ValueError:
        await sendMessage(msg, "❌ 车型ID必须是数字")
    except Exception as e:
        LOGGER.error(f"配置奖励按钮失败: {e}")
        await sendMessage(msg, f"❌ 配置失败: {str(e)}")


@bot.on_message(filters.command('hunt_view_button', prefixes) & user_in_group_on_filter)
async def view_hunt_button(_, msg):
    """查看车库游戏奖励按钮配置"""
    await msg.delete()
    
    user = sql_get_emby(msg.from_user.id)
    if not user:
        return await sendMessage(msg, "❌ 请先私聊机器人进行注册")
    
    try:
        with Session() as session:
            cars = session.query(Car).all()
            
            if not cars:
                return await sendMessage(msg, "❌ 没有找到任何汽车配置")
            
            config_text = "🔧 **奖励按钮配置**\n\n"
            
            for car in cars:
                button_config = sql_get_reward_button(car.id)
                config_text += f"🏎️ **{car.car_name}** (ID: {car.id})\n"
                
                if button_config:
                    config_text += f"🔘 按钮: {button_config.button_text}\n"
                    config_text += f"🔗 链接: {button_config.button_url}\n"
                    config_text += f"📱 状态: {'✅ 启用' if button_config.is_active else '❌ 禁用'}\n"
                else:
                    config_text += f"📱 状态: ❌ 未配置\n"
                
                config_text += "\n"
            
            config_text += "💡 使用 `/hunt_config_button` 命令配置自定义按钮"
            
            await sendMessage(msg, config_text)
            
    except Exception as e:
        LOGGER.error(f"查看奖励按钮配置失败: {e}")
        await sendMessage(msg, "❌ 获取配置信息失败")


@bot.on_message(filters.command('hunt_export_config', prefixes) & user_in_group_on_filter)
async def export_hunt_config(_, msg):
    """导出车库游戏配置到config.json"""
    await msg.delete()
    
    user = sql_get_emby(msg.from_user.id)
    if not user:
        return await sendMessage(msg, "❌ 请先私聊机器人进行注册")
    
    try:
        config_path = "/home/runner/work/bavabot/bavabot/config.json"
        
        # 读取现有配置或创建新配置
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {}
        
        # 获取当前的奖励配置
        with Session() as session:
            reward_configs = session.query(RewardConfig).filter(
                RewardConfig.is_active == True
            ).all()
            
            button_configs = session.query(RewardButton).filter(
                RewardButton.is_active == True  
            ).all()
            
            cars = session.query(Car).all()
            car_dict = {car.id: car.car_name for car in cars}
        
        # 构建hunt配置结构
        hunt_config = {
            "rewards": {},
            "buttons": {}
        }
        
        # 添加奖励配置
        for reward in reward_configs:
            car_name = car_dict.get(reward.car_id, f"Car_{reward.car_id}")
            hunt_config["rewards"][str(reward.car_id)] = {
                "car_name": car_name,
                "reward_type": reward.reward_type,
                "reward_value": reward.reward_value,
                "reward_description": reward.reward_description
            }
        
        # 添加按钮配置
        for button in button_configs:
            car_name = car_dict.get(button.car_id, f"Car_{button.car_id}")
            hunt_config["buttons"][str(button.car_id)] = {
                "car_name": car_name,
                "button_text": button.button_text,
                "button_url": button.button_url
            }
        
        # 更新配置文件
        config["hunt"] = hunt_config
        
        # 写入配置文件
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        await sendMessage(
            msg,
            f"✅ **车库配置导出成功！**\n\n"
            f"📄 配置文件: {config_path}\n"
            f"🎁 奖励配置: {len(hunt_config['rewards'])} 项\n"
            f"🔘 按钮配置: {len(hunt_config['buttons'])} 项\n\n"
            f"💡 配置已保存到 config.json 的 hunt 字段中"
        )
        
    except Exception as e:
        LOGGER.error(f"导出车库配置失败: {e}")
        await sendMessage(msg, f"❌ 导出配置失败: {str(e)}")