"""
抽奖定时任务
"""
from datetime import datetime

from bot import LOGGER, lottery
from bot.modules.extra.lottery import check_lottery_schedules


async def check_lottery_timing():
    """检查抽奖定时任务"""
    if not lottery.status:
        return
    
    try:
        await check_lottery_schedules()
        LOGGER.debug("抽奖定时检查完成")
    except Exception as e:
        LOGGER.error(f"抽奖定时检查失败: {e}")