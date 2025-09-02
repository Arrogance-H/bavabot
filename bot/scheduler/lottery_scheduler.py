"""
抽奖系统定时任务
Lottery System Scheduler

Author: GitHub Copilot
Date: 2024
"""

import asyncio
from datetime import datetime
from bot import bot, LOGGER, config
from bot.modules.commands.lottery_admin import check_auto_draw
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# 创建调度器实例
lottery_scheduler = AsyncIOScheduler()


async def lottery_auto_draw_task():
    """自动开奖任务"""
    try:
        if config.lottery.status and config.lottery.auto_draw:
            await check_auto_draw()
    except Exception as e:
        LOGGER.error(f"自动开奖任务执行失败: {e}")


def start_lottery_scheduler():
    """启动抽奖调度器"""
    try:
        if config.lottery.status:
            # 每分钟检查一次是否需要自动开奖
            lottery_scheduler.add_job(
                lottery_auto_draw_task,
                'interval',
                minutes=1,
                id='lottery_auto_draw',
                replace_existing=True
            )
            
            lottery_scheduler.start()
            LOGGER.info("抽奖系统调度器已启动")
        else:
            LOGGER.info("抽奖系统未开启，跳过调度器启动")
    except Exception as e:
        LOGGER.error(f"启动抽奖调度器失败: {e}")


def stop_lottery_scheduler():
    """停止抽奖调度器"""
    try:
        if lottery_scheduler.running:
            lottery_scheduler.shutdown()
            LOGGER.info("抽奖系统调度器已停止")
    except Exception as e:
        LOGGER.error(f"停止抽奖调度器失败: {e}")