"""
车库游戏定时任务
"""
import asyncio
from datetime import datetime, timedelta
from bot import LOGGER, schedall, bot
from bot.sql_helper.sql_hunt import sql_cleanup_expired_equipment, sql_cleanup_timed_out_hunts, sql_cleanup_idle_hunts
from bot.sql_helper.sql_emby import get_all_emby
from bot.func_helper.msg_utils import deleteMessage


async def cleanup_hunt_equipment():
    """清理过期装备"""
    try:
        sql_cleanup_expired_equipment()
        LOGGER.info("【车库清理】过期装备清理完成")
    except Exception as e:
        LOGGER.error(f"【车库清理】过期装备清理失败: {e}")


async def cleanup_expired_hunts():
    """清理超时的车库游戏并删除相关消息"""
    try:
        messages_to_delete = sql_cleanup_timed_out_hunts()
        
        # 删除相关的游戏界面消息
        deleted_count = 0
        for msg_info in messages_to_delete:
            try:
                # 创建一个模拟的消息对象用于删除
                class MockMessage:
                    def __init__(self, chat_id, message_id):
                        self.chat = type('obj', (object,), {'id': chat_id})()
                        self.id = message_id
                
                mock_msg = MockMessage(msg_info['chat_id'], msg_info['message_id'])
                await deleteMessage(mock_msg)
                deleted_count += 1
                LOGGER.info(f"【车库清理】已删除超时游戏会话 {msg_info['hunt_id']} 的消息")
            except Exception as e:
                LOGGER.warning(f"【车库清理】删除消息失败 (hunt_id: {msg_info['hunt_id']}): {e}")
        
        if messages_to_delete:
            LOGGER.info(f"【车库清理】超时游戏清理完成，删除了 {deleted_count}/{len(messages_to_delete)} 条消息")
        else:
            LOGGER.info("【车库清理】超时游戏清理完成")
    except Exception as e:
        LOGGER.error(f"【车库清理】清理超时游戏失败: {e}")


async def cleanup_idle_hunts():
    """清理闲置的车库游戏并删除相关消息"""
    try:
        messages_to_delete = sql_cleanup_idle_hunts()
        
        # 删除相关的游戏界面消息
        deleted_count = 0
        for msg_info in messages_to_delete:
            try:
                # 创建一个模拟的消息对象用于删除
                class MockMessage:
                    def __init__(self, chat_id, message_id):
                        self.chat = type('obj', (object,), {'id': chat_id})()
                        self.id = message_id
                
                mock_msg = MockMessage(msg_info['chat_id'], msg_info['message_id'])
                await deleteMessage(mock_msg)
                deleted_count += 1
                LOGGER.info(f"【车库清理】已删除闲置游戏会话 {msg_info['hunt_id']} 的消息")
            except Exception as e:
                LOGGER.warning(f"【车库清理】删除消息失败 (hunt_id: {msg_info['hunt_id']}): {e}")
        
        if messages_to_delete:
            LOGGER.info(f"【车库清理】闲置游戏清理完成，删除了 {deleted_count}/{len(messages_to_delete)} 条消息")
        else:
            LOGGER.info("【车库清理】闲置游戏清理完成")
    except Exception as e:
        LOGGER.error(f"【车库清理】清理闲置游戏失败: {e}")


# 注册定时任务
if getattr(schedall, 'hunt_cleanup', True):  # 默认启用
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    import atexit
    
    scheduler = AsyncIOScheduler()
    
    # 每天凌晨1点清理过期装备
    scheduler.add_job(
        cleanup_hunt_equipment,
        'cron',
        hour=1,
        minute=0,
        id='hunt_equipment_cleanup'
    )
    
    # 每10分钟清理超时游戏
    scheduler.add_job(
        cleanup_expired_hunts,
        'interval',
        minutes=10,
        id='hunt_expired_cleanup'
    )
    
    # 每5分钟清理闲置游戏
    scheduler.add_job(
        cleanup_idle_hunts,
        'interval',
        minutes=5,
        id='hunt_idle_cleanup'
    )
    
    try:
        scheduler.start()
        LOGGER.info("【车库定时】车库游戏定时任务启动成功")
    except Exception as e:
        LOGGER.error(f"【车库定时】定时任务启动失败: {e}")
    
    # 程序退出时关闭调度器
    atexit.register(lambda: scheduler.shutdown())
