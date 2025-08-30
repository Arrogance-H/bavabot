"""
寻宝游戏定时任务
"""
import asyncio
from datetime import datetime, timedelta
from bot import LOGGER, schedall
from bot.sql_helper.sql_hunt import sql_cleanup_expired_fragments, sql_end_hunt, sql_get_active_hunt
from bot.sql_helper.sql_emby import get_all_emby


async def cleanup_hunt_fragments():
    """清理过期碎片"""
    try:
        sql_cleanup_expired_fragments()
        LOGGER.info("【寻宝清理】过期碎片清理完成")
    except Exception as e:
        LOGGER.error(f"【寻宝清理】过期碎片清理失败: {e}")


async def cleanup_expired_hunts():
    """清理超时的寻宝游戏"""
    try:
        from bot.sql_helper.sql_hunt import Hunt, Session
        
        with Session() as session:
            # 获取所有超过30分钟且仍活跃的游戏
            timeout_threshold = datetime.now() - timedelta(minutes=30)
            expired_hunts = session.query(Hunt).filter(
                Hunt.is_active == True,
                Hunt.start_time < timeout_threshold
            ).all()
            
            count = 0
            for hunt in expired_hunts:
                hunt.is_active = False
                hunt.end_time = datetime.now()
                count += 1
            
            session.commit()
            
            if count > 0:
                LOGGER.info(f"【寻宝清理】清理了 {count} 个超时的寻宝游戏")
            
    except Exception as e:
        LOGGER.error(f"【寻宝清理】清理超时游戏失败: {e}")


# 注册定时任务
if schedall.get('hunt_cleanup', True):  # 默认启用
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    import atexit
    
    scheduler = AsyncIOScheduler()
    
    # 每天凌晨1点清理过期碎片
    scheduler.add_job(
        cleanup_hunt_fragments,
        'cron',
        hour=1,
        minute=0,
        id='hunt_fragments_cleanup'
    )
    
    # 每10分钟清理超时游戏
    scheduler.add_job(
        cleanup_expired_hunts,
        'interval',
        minutes=10,
        id='hunt_expired_cleanup'
    )
    
    try:
        scheduler.start()
        LOGGER.info("【寻宝定时】寻宝游戏定时任务启动成功")
    except Exception as e:
        LOGGER.error(f"【寻宝定时】定时任务启动失败: {e}")
    
    # 程序退出时关闭调度器
    atexit.register(lambda: scheduler.shutdown())