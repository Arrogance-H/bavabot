"""
车库游戏定时任务
"""
import asyncio
from datetime import datetime, timedelta
from bot import LOGGER, schedall
from bot.sql_helper.sql_hunt import sql_cleanup_expired_equipment, sql_cleanup_timed_out_hunts, sql_cleanup_idle_hunts
from bot.sql_helper.sql_emby import get_all_emby
from bot.sql_helper.sql_emby import get_all_emby


async def cleanup_hunt_equipment():
    """清理过期装备"""
    try:
        sql_cleanup_expired_equipment()
        LOGGER.info("【车库清理】过期装备清理完成")
    except Exception as e:
        LOGGER.error(f"【车库清理】过期装备清理失败: {e}")


async def cleanup_expired_hunts():
    """清理超时的车库游戏"""
    try:
        sql_cleanup_timed_out_hunts()
        LOGGER.info("【车库清理】超时游戏清理完成")
    except Exception as e:
        LOGGER.error(f"【车库清理】清理超时游戏失败: {e}")


async def cleanup_idle_hunts():
    """清理闲置的车库游戏"""
    try:
        sql_cleanup_idle_hunts()
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
