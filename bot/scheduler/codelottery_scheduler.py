"""
抽奖系统定时任务
Enhanced with hunt system patterns for better reliability and monitoring
"""
import asyncio
import random
from datetime import datetime, timedelta
from pyrogram.errors import FloodWait
from bot import LOGGER, bot, config, sakura_b, group
from bot.sql_helper.sql_codelottery import (
    sql_get_expired_lottery_rounds,
    sql_get_lottery_participants,
    sql_complete_lottery_round,
    sql_get_codelottery_user,
    sql_cleanup_old_lottery_data,
    sql_get_codelottery_health_status
)


async def send_message_with_fallback(chat_id, message, message_type="群组"):
    """
    发送消息并处理各种错误情况 - 借鉴hunt系统的错误处理模式
    """
    try:
        await bot.send_message(chat_id, message)
        LOGGER.info(f"【抽奖定时】成功发送{message_type}消息到 {chat_id}")
        return True
        
    except FloodWait as f:
        LOGGER.warning(f"【抽奖定时】{message_type}消息发送遇到限流: {f}")
        await asyncio.sleep(f.value * 1.2)
        try:
            await bot.send_message(chat_id, message)
            LOGGER.info(f"【抽奖定时】{message_type}消息重试发送成功到 {chat_id}")
            return True
        except Exception as retry_e:
            LOGGER.error(f"【抽奖定时】{message_type}消息重试发送失败到 {chat_id}: {retry_e}")
            
    except Exception as e:
        LOGGER.error(f"【抽奖定时】发送{message_type}消息失败到 {chat_id}: {e}")
        LOGGER.error(f"【抽奖定时】消息详情: 长度={len(message)}, 聊天ID={chat_id}")
        
        # 尝试发送简化版本的消息（无markdown格式）
        try:
            simple_msg = message.replace("**", "")  # 移除markdown格式
            await bot.send_message(chat_id, simple_msg)
            LOGGER.info(f"【抽奖定时】简化{message_type}消息发送成功到 {chat_id}")
            return True
        except Exception as simple_e:
            LOGGER.error(f"【抽奖定时】简化{message_type}消息也发送失败到 {chat_id}: {simple_e}")
            
    return False


async def validate_lottery_environment():
    """
    验证抽奖环境配置 - 借鉴hunt系统的环境检查
    """
    try:
        # 检查基础配置
        if not hasattr(config, 'code_lottery'):
            LOGGER.error("【抽奖定时】配置错误: 缺少 code_lottery 配置")
            return False
            
        if not group or len(group) == 0:
            LOGGER.error("【抽奖定时】配置错误: 群组配置为空")
            return False
            
        # 检查机器人权限
        try:
            chat_info = await bot.get_chat(group[0])
            LOGGER.debug(f"【抽奖定时】群组信息验证: {chat_info.title} ({group[0]})")
        except Exception as chat_e:
            LOGGER.error(f"【抽奖定时】无法访问群组 {group[0]}: {chat_e}")
            return False
            
        return True
        
    except Exception as e:
        LOGGER.error(f"【抽奖定时】环境验证失败: {e}")
        return False
async def auto_draw_expired_lotteries():
    """自动为过期的抽奖进行开奖 - 增强错误处理和日志记录"""
    try:
        # 环境验证
        if not await validate_lottery_environment():
            LOGGER.error("【抽奖定时】环境验证失败，跳过本次检查")
            return
            
        expired_rounds = sql_get_expired_lottery_rounds()
        
        if not expired_rounds:
            LOGGER.debug("【抽奖定时】没有发现过期的抽奖轮次")
            return
            
        LOGGER.info(f"【抽奖定时】开始处理 {len(expired_rounds)} 个过期抽奖轮次")
        
        for round_obj in expired_rounds:
            try:
                await process_single_lottery_round(round_obj)
            except Exception as round_error:
                LOGGER.error(f"【抽奖定时】处理抽奖轮次 {round_obj.id} 时发生错误: {round_error}")
                continue
        
        LOGGER.info(f"【抽奖定时】处理了 {len(expired_rounds)} 个过期抽奖")
        
    except Exception as e:
        LOGGER.error(f"【抽奖定时】自动开奖检查失败: {e}")


async def process_single_lottery_round(round_obj):
    """处理单个抽奖轮次的开奖 - 模块化处理逻辑"""
    try:
        round_id = round_obj.id
        LOGGER.info(f"【抽奖定时】开始处理第{round_obj.round_number}次抽奖 (ID: {round_id})")
        
        # 获取参与者列表
        participants = sql_get_lottery_participants(round_id)
        
        if len(participants) == 0:
            # 没有参与者，直接取消
            success, msg = sql_complete_lottery_round(round_id, [])
            if success:
                LOGGER.info(f"【抽奖定时】第{round_obj.round_number}次抽奖无参与者，已取消")
            else:
                LOGGER.error(f"【抽奖定时】取消第{round_obj.round_number}次抽奖失败: {msg}")
            return
        
        # 选择获奖者
        winners = await select_lottery_winners(round_obj, participants)
        if not winners:
            LOGGER.error(f"【抽奖定时】第{round_obj.round_number}次抽奖获奖者选择失败")
            return
            
        # 完成抽奖
        success, msg = sql_complete_lottery_round(round_id, winners)
        
        if success:
            await announce_lottery_results(round_obj, participants, winners)
            LOGGER.info(f"【抽奖定时】第{round_obj.round_number}次抽奖自动开奖完成，{len(winners)}人获奖")
        else:
            LOGGER.error(f"【抽奖定时】第{round_obj.round_number}次抽奖自动开奖失败: {msg}")
            
    except Exception as e:
        LOGGER.error(f"【抽奖定时】处理第{round_obj.round_number}次抽奖失败: {e}")


async def select_lottery_winners(round_obj, participants):
    """选择抽奖获奖者 - 包含保底机制"""
    try:
        winner_count = min(round_obj.winner_count, len(participants))
        
        # 获取保底用户（参与次数达到条件的用户）
        guaranteed_winners = []
        regular_participants = []
        
        guaranteed_threshold = getattr(config.code_lottery, 'guaranteed_win_count', 10)
        
        for participant in participants:
            lottery_user = sql_get_codelottery_user(participant.tg)
            if lottery_user and lottery_user.total_participations >= guaranteed_threshold:
                guaranteed_winners.append(participant)
            else:
                regular_participants.append(participant)
        
        LOGGER.debug(f"【抽奖定时】保底用户: {len(guaranteed_winners)}, 普通参与者: {len(regular_participants)}")
        
        # 选择获奖者
        winners = []
        
        # 首先添加保底获奖者
        for guaranteed in guaranteed_winners[:winner_count]:
            winners.append({
                'tg': guaranteed.tg,
                'nickname': guaranteed.nickname
            })
        
        # 如果还有名额，从普通参与者中随机选择
        remaining_slots = winner_count - len(winners)
        if remaining_slots > 0 and regular_participants:
            random_winners = random.sample(regular_participants, min(remaining_slots, len(regular_participants)))
            for winner in random_winners:
                winners.append({
                    'tg': winner.tg,
                    'nickname': winner.nickname
                })
        
        LOGGER.info(f"【抽奖定时】选出获奖者: 保底 {min(len(guaranteed_winners), winner_count)} 人, "
                   f"随机 {remaining_slots if remaining_slots > 0 else 0} 人")
        return winners
        
    except Exception as e:
        LOGGER.error(f"【抽奖定时】选择获奖者失败: {e}")
        return []


async def announce_lottery_results(round_obj, participants, winners):
    """发布抽奖结果 - 分离群组通知和私信通知"""
    try:
        # 构建开奖信息
        draw_msg = build_lottery_result_message(round_obj, participants, winners)
        
        # 发送开奖结果到群组
        LOGGER.info(f"【抽奖定时】准备发送开奖结果到群组 {group[0]}")
        group_success = await send_message_with_fallback(group[0], draw_msg, "群组")
        
        if not group_success:
            LOGGER.warning(f"【抽奖定时】群组消息发送失败，但继续私信通知获奖者")
        
        # 私信通知获奖者
        await notify_lottery_winners(round_obj, winners)
        
    except Exception as e:
        LOGGER.error(f"【抽奖定时】发布抽奖结果失败: {e}")


def build_lottery_result_message(round_obj, participants, winners):
    """构建抽奖结果消息"""
    try:
        draw_msg = (
            f"🎊 **开奖结果** 🎊\n\n"
            f"🎲 抽奖名称：{round_obj.lottery_name}\n"
            f"📅 轮次：第{round_obj.round_number}次\n"
            f"⏰ 时间到期自动开奖\n"
            f"👥 参与人数：{len(participants)}人\n"
            f"🏆 获奖人数：{len(winners)}人\n\n"
            f"🎉 **获奖名单** 🎉\n"
        )
        
        for i, winner in enumerate(winners, 1):
            lottery_user = sql_get_codelottery_user(winner['tg'])
            total_participations = lottery_user.total_participations if lottery_user else 0
            draw_msg += f"{i}. {winner['nickname']} (累计参与{total_participations}次)\n"
        
        draw_msg += f"\n🎁 获奖者请联系me领奖"
        return draw_msg
        
    except Exception as e:
        LOGGER.error(f"【抽奖定时】构建开奖消息失败: {e}")
        return "开奖结果构建失败"


async def notify_lottery_winners(round_obj, winners):
    """通知抽奖获奖者"""
    try:
        notification_tasks = []
        
        for winner in winners:
            winner_msg = (
                f"🎊 **恭喜中奖！** 🎊\n\n"
                f"🎲 抽奖名称：{round_obj.lottery_name}\n"
                f"📅 轮次：第{round_obj.round_number}次\n"
                f"⏰ 时间到期自动开奖\n"
                f"🏆 您已获奖！\n\n"
                f"📞 **请联系me领奖**"
            )
            
            # 创建异步任务但不等待全部完成
            task = asyncio.create_task(
                send_winner_notification(winner['tg'], winner['nickname'], winner_msg)
            )
            notification_tasks.append(task)
            
        # 并发发送所有通知
        if notification_tasks:
            results = await asyncio.gather(*notification_tasks, return_exceptions=True)
            success_count = sum(1 for r in results if r is True)
            LOGGER.info(f"【抽奖定时】获奖者通知完成: {success_count}/{len(winners)} 成功")
            
    except Exception as e:
        LOGGER.error(f"【抽奖定时】批量通知获奖者失败: {e}")


async def send_winner_notification(tg, nickname, message):
    """发送单个获奖者通知"""
    try:
        success = await send_message_with_fallback(tg, message, f"私信({nickname})")
        if success:
            LOGGER.info(f"【抽奖定时】用户{tg}({nickname})获奖通知发送成功")
        return success
    except Exception as e:
        LOGGER.error(f"【抽奖定时】发送获奖通知给{tg}({nickname})失败: {e}")
        return False


async def codelottery_health_monitor():
    """抽奖系统健康监控任务 - 借鉴hunt系统的监控机制"""
    try:
        health_status = sql_get_codelottery_health_status()
        if not health_status:
            LOGGER.warning("【抽奖监控】无法获取系统健康状态")
            return
            
        # 检查是否有问题需要报告
        issues = []
        
        if health_status['expired_active_rounds'] > 0:
            issues.append(f"发现 {health_status['expired_active_rounds']} 个过期但仍活跃的抽奖轮次")
            
        if health_status['active_rounds'] > 3:
            issues.append(f"活跃抽奖轮次过多: {health_status['active_rounds']}")
            
        if issues:
            LOGGER.warning(f"【抽奖监控】发现问题: {'; '.join(issues)}")
        else:
            LOGGER.debug(f"【抽奖监控】系统健康: {health_status['health_score']}")
            
    except Exception as e:
        LOGGER.error(f"【抽奖监控】健康检查失败: {e}")


async def codelottery_maintenance():
    """抽奖系统维护任务 - 借鉴hunt系统的维护机制"""
    try:
        LOGGER.info("【抽奖维护】开始执行维护任务")
        
        # 清理30天前的旧数据
        cleaned_count = sql_cleanup_old_lottery_data(30)
        if cleaned_count > 0:
            LOGGER.info(f"【抽奖维护】清理了 {cleaned_count} 个旧抽奖轮次")
        
        # 获取系统统计
        health_status = sql_get_codelottery_health_status()
        if health_status:
            LOGGER.info(f"【抽奖维护】系统统计: 用户 {health_status['total_users']}, "
                       f"轮次 {health_status['total_rounds']}, "
                       f"活跃轮次 {health_status['active_rounds']}")
        
        LOGGER.info("【抽奖维护】维护任务完成")
        
    except Exception as e:
        LOGGER.error(f"【抽奖维护】维护任务失败: {e}")


# 注册定时任务 - 增强任务管理
if getattr(config.code_lottery, 'status', False):  # 只有在抽奖系统开启时才启动定时任务
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    import atexit
    
    scheduler = AsyncIOScheduler()
    
    try:
        # 每分钟检查一次过期的抽奖
        scheduler.add_job(
            auto_draw_expired_lotteries,
            'interval',
            minutes=1,
            id='codelottery_auto_draw',
            max_instances=1,  # 防止任务重叠
            coalesce=True     # 合并延迟的任务
        )
        
        # 每5分钟进行一次健康检查
        scheduler.add_job(
            codelottery_health_monitor,
            'interval',
            minutes=5,
            id='codelottery_health_monitor',
            max_instances=1
        )
        
        # 每天凌晨2点进行维护
        scheduler.add_job(
            codelottery_maintenance,
            'cron',
            hour=2,
            minute=0,
            id='codelottery_maintenance',
            max_instances=1
        )
        
        scheduler.start()
        LOGGER.info("【抽奖定时】抽奖系统定时任务启动成功")
        LOGGER.info("【抽奖定时】已注册任务: 自动开奖(每分钟), 健康监控(每5分钟), 系统维护(每日2点)")
        
    except Exception as e:
        LOGGER.error(f"【抽奖定时】定时任务启动失败: {e}")
    
    # 程序退出时关闭调度器
    def shutdown_scheduler():
        try:
            if scheduler.running:
                scheduler.shutdown(wait=True)
                LOGGER.info("【抽奖定时】调度器已安全关闭")
        except Exception as e:
            LOGGER.error(f"【抽奖定时】关闭调度器失败: {e}")
    
    atexit.register(shutdown_scheduler)
else:
    LOGGER.info("【抽奖定时】抽奖系统未开启，跳过定时任务")