"""
抽奖系统定时任务
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
    sql_get_codelottery_user
)


async def auto_draw_expired_lotteries():
    """自动为过期的抽奖进行开奖"""
    try:
        expired_rounds = sql_get_expired_lottery_rounds()
        
        for round_obj in expired_rounds:
            try:
                # 获取参与者列表
                participants = sql_get_lottery_participants(round_obj.id)
                
                if len(participants) == 0:
                    # 没有参与者，直接取消
                    sql_complete_lottery_round(round_obj.id, [])
                    LOGGER.info(f"【抽奖定时】第{round_obj.round_number}次抽奖无参与者，已取消")
                    continue
                
                winner_count = min(round_obj.winner_count, len(participants))
                
                # 获取保底用户（参与次数达到条件的用户）
                guaranteed_winners = []
                regular_participants = []
                
                for participant in participants:
                    lottery_user = sql_get_codelottery_user(participant.tg)
                    if lottery_user and lottery_user.total_participations >= config.code_lottery.guaranteed_win_count:
                        guaranteed_winners.append(participant)
                    else:
                        regular_participants.append(participant)
                
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
                
                # 完成抽奖
                success, msg = sql_complete_lottery_round(round_obj.id, winners)
                
                if success:
                    # 构建开奖信息
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
                    
                    # 发送开奖结果到群组
                    LOGGER.info(f"【抽奖定时】准备发送开奖结果到群组 {group[0]}")
                    try:
                        await bot.send_message(group[0], draw_msg)
                        LOGGER.info(f"【抽奖定时】成功发送开奖结果到群组")
                    except FloodWait as f:
                        LOGGER.warning(f"【抽奖定时】群组消息发送遇到限流: {f}")
                        await asyncio.sleep(f.value * 1.2)
                        try:
                            await bot.send_message(group[0], draw_msg)
                            LOGGER.info(f"【抽奖定时】群组消息重试发送成功")
                        except Exception as retry_e:
                            LOGGER.error(f"【抽奖定时】群组消息重试发送失败: {retry_e}")
                    except Exception as e:
                        LOGGER.error(f"【抽奖定时】发送开奖结果失败: {e}")
                        LOGGER.error(f"【抽奖定时】群组ID: {group[0]}, 消息长度: {len(draw_msg)}")
                        # 尝试发送简化版本的消息（无markdown格式）
                        try:
                            simple_msg = draw_msg.replace("**", "")  # 移除markdown格式
                            await bot.send_message(group[0], simple_msg)
                            LOGGER.info(f"【抽奖定时】简化消息发送成功")
                        except Exception as simple_e:
                            LOGGER.error(f"【抽奖定时】简化消息也发送失败: {simple_e}")
                    
                    # 私信通知获奖者
                    for winner in winners:
                        winner_msg = (
                            f"🎊 **恭喜中奖！** 🎊\n\n"
                            f"🎲 抽奖名称：{round_obj.lottery_name}\n"
                            f"📅 轮次：第{round_obj.round_number}次\n"
                            f"⏰ 时间到期自动开奖\n"
                            f"🏆 您已获奖！\n\n"
                            f"📞 **请联系me领奖**"
                        )
                        
                        try:
                            await bot.send_message(winner['tg'], winner_msg)
                            LOGGER.info(f"【抽奖定时】成功发送中奖通知给用户{winner['tg']}")
                        except FloodWait as f:
                            LOGGER.warning(f"【抽奖定时】私信发送遇到限流: {f}")
                            await asyncio.sleep(f.value * 1.2)
                            try:
                                await bot.send_message(winner['tg'], winner_msg)
                                LOGGER.info(f"【抽奖定时】私信重试发送成功给用户{winner['tg']}")
                            except Exception as retry_e:
                                LOGGER.error(f"【抽奖定时】私信重试发送失败给用户{winner['tg']}: {retry_e}")
                        except Exception as e:
                            LOGGER.error(f"【抽奖定时】发送私信给用户{winner['tg']}失败: {e}")
                            # 尝试发送简化版本的消息（无markdown格式）
                            try:
                                simple_winner_msg = winner_msg.replace("**", "")  # 移除markdown格式
                                await bot.send_message(winner['tg'], simple_winner_msg)
                                LOGGER.info(f"【抽奖定时】简化私信发送成功给用户{winner['tg']}")
                            except Exception as simple_e:
                                LOGGER.error(f"【抽奖定时】简化私信也发送失败给用户{winner['tg']}: {simple_e}")
                                # 用户可能没有私聊机器人，这是正常的
                        
                        LOGGER.info(f"【抽奖定时】用户{winner['tg']}({winner['nickname']})在第{round_obj.id}轮抽奖中获奖")
                    
                    LOGGER.info(f"【抽奖定时】第{round_obj.round_number}次抽奖自动开奖完成，{len(winners)}人获奖")
                else:
                    LOGGER.error(f"【抽奖定时】第{round_obj.round_number}次抽奖自动开奖失败: {msg}")
                    
            except Exception as e:
                LOGGER.error(f"【抽奖定时】处理第{round_obj.round_number}次抽奖失败: {e}")
        
        if expired_rounds:
            LOGGER.info(f"【抽奖定时】处理了 {len(expired_rounds)} 个过期抽奖")
            
    except Exception as e:
        LOGGER.error(f"【抽奖定时】自动开奖检查失败: {e}")


# 注册定时任务
if getattr(config.code_lottery, 'status', False):  # 只有在抽奖系统开启时才启动定时任务
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    import atexit
    
    scheduler = AsyncIOScheduler()
    
    # 每分钟检查一次过期的抽奖
    scheduler.add_job(
        auto_draw_expired_lotteries,
        'interval',
        minutes=1,
        id='codelottery_auto_draw'
    )
    
    try:
        scheduler.start()
        LOGGER.info("【抽奖定时】抽奖系统定时任务启动成功")
    except Exception as e:
        LOGGER.error(f"【抽奖定时】定时任务启动失败: {e}")
    
    # 程序退出时关闭调度器
    atexit.register(lambda: scheduler.shutdown())
else:
    LOGGER.info("【抽奖定时】抽奖系统未开启，跳过定时任务")