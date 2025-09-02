"""
抽奖系统数据库操作
Lottery System Database Operations

Author: GitHub Copilot
Date: 2024
"""

import random
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from bot.sql_helper import Base, Session, engine
from sqlalchemy import (
    Column, BigInteger, String, DateTime, Integer, Boolean, Text, 
    ForeignKey, func, and_, or_
)
from sqlalchemy.orm import relationship
from bot import LOGGER


class Lottery(Base):
    """
    抽奖表 - 存储抽奖基本信息
    Lottery table - stores basic lottery information
    """
    __tablename__ = 'lottery'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)  # 抽奖标题
    description = Column(Text, nullable=True)  # 抽奖描述
    image_url = Column(String(500), nullable=True)  # 抽奖图片URL
    
    # 抽奖模式配置
    is_free = Column(Boolean, default=True)  # 是否免费
    cost = Column(Integer, default=0)  # 参与费用（币）
    require_emby = Column(Boolean, default=True)  # 是否需要emby账号
    
    # 开奖模式配置
    draw_type = Column(String(20), nullable=False)  # time/count - 时间开奖/人数开奖
    draw_time = Column(DateTime, nullable=True)  # 开奖时间
    target_participants = Column(Integer, nullable=True)  # 目标参与人数
    
    # 状态
    status = Column(String(20), default='active')  # active/drawn/cancelled
    created_by = Column(BigInteger, nullable=False)  # 创建者TG ID
    created_time = Column(DateTime, default=datetime.now)
    drawn_time = Column(DateTime, nullable=True)  # 开奖时间
    
    # 参与统计
    total_participants = Column(Integer, default=0)  # 当前参与人数
    max_participants = Column(Integer, nullable=True)  # 最大参与人数限制


class LotteryPrize(Base):
    """
    抽奖奖品表 - 存储奖品配置
    Lottery prize table - stores prize configuration
    """
    __tablename__ = 'lottery_prize'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    lottery_id = Column(Integer, ForeignKey('lottery.id'), nullable=False)
    
    prize_name = Column(String(200), nullable=False)  # 奖品名称
    prize_type = Column(String(20), nullable=False)  # coins/other
    prize_value = Column(String(100), nullable=False)  # 奖品价值/数量
    prize_description = Column(Text, nullable=True)  # 奖品描述
    quantity = Column(Integer, default=1)  # 奖品数量
    
    # 中奖概率设置
    probability = Column(Integer, default=100)  # 中奖概率 (1-10000, 支持小数点后两位)


class LotteryParticipant(Base):
    """
    抽奖参与者表 - 存储参与记录
    Lottery participant table - stores participation records
    """
    __tablename__ = 'lottery_participant'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    lottery_id = Column(Integer, ForeignKey('lottery.id'), nullable=False)
    user_tg = Column(BigInteger, nullable=False)  # 参与者TG ID
    user_name = Column(String(200), nullable=False)  # 参与者名称
    
    join_time = Column(DateTime, default=datetime.now)  # 参与时间
    cost_paid = Column(Integer, default=0)  # 支付的费用


class LotteryWinner(Base):
    """
    抽奖中奖记录表 - 存储中奖结果
    Lottery winner table - stores winning results
    """
    __tablename__ = 'lottery_winner'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    lottery_id = Column(Integer, ForeignKey('lottery.id'), nullable=False)
    prize_id = Column(Integer, ForeignKey('lottery_prize.id'), nullable=False)
    user_tg = Column(BigInteger, nullable=False)  # 中奖者TG ID
    user_name = Column(String(200), nullable=False)  # 中奖者名称
    
    win_time = Column(DateTime, default=datetime.now)  # 中奖时间
    claimed = Column(Boolean, default=False)  # 是否已领取
    claim_time = Column(DateTime, nullable=True)  # 领取时间


# 创建表
Lottery.__table__.create(bind=engine, checkfirst=True)
LotteryPrize.__table__.create(bind=engine, checkfirst=True)
LotteryParticipant.__table__.create(bind=engine, checkfirst=True)
LotteryWinner.__table__.create(bind=engine, checkfirst=True)


def sql_create_lottery(
    title: str,
    description: str,
    creator_tg: int,
    is_free: bool = True,
    cost: int = 0,
    require_emby: bool = True,
    draw_type: str = "time",
    draw_time: Optional[datetime] = None,
    target_participants: Optional[int] = None,
    max_participants: Optional[int] = None,
    image_url: Optional[str] = None
) -> Optional[int]:
    """创建抽奖"""
    with Session() as session:
        try:
            lottery = Lottery(
                title=title,
                description=description,
                image_url=image_url,
                is_free=is_free,
                cost=cost,
                require_emby=require_emby,
                draw_type=draw_type,
                draw_time=draw_time,
                target_participants=target_participants,
                max_participants=max_participants,
                created_by=creator_tg
            )
            session.add(lottery)
            session.commit()
            return lottery.id
        except Exception as e:
            session.rollback()
            LOGGER.error(f"创建抽奖失败: {e}")
            return None


def sql_add_lottery_prize(
    lottery_id: int,
    prize_name: str,
    prize_type: str,
    prize_value: str,
    quantity: int = 1,
    probability: int = 100,
    prize_description: Optional[str] = None
) -> bool:
    """添加抽奖奖品"""
    with Session() as session:
        try:
            prize = LotteryPrize(
                lottery_id=lottery_id,
                prize_name=prize_name,
                prize_type=prize_type,
                prize_value=prize_value,
                prize_description=prize_description,
                quantity=quantity,
                probability=probability
            )
            session.add(prize)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            LOGGER.error(f"添加抽奖奖品失败: {e}")
            return False


def sql_join_lottery(lottery_id: int, user_tg: int, user_name: str, cost_paid: int = 0) -> bool:
    """参与抽奖"""
    with Session() as session:
        try:
            # 检查是否已经参与
            existing = session.query(LotteryParticipant).filter(
                and_(LotteryParticipant.lottery_id == lottery_id, 
                     LotteryParticipant.user_tg == user_tg)
            ).first()
            
            if existing:
                return False  # 已经参与过
            
            # 添加参与记录
            participant = LotteryParticipant(
                lottery_id=lottery_id,
                user_tg=user_tg,
                user_name=user_name,
                cost_paid=cost_paid
            )
            session.add(participant)
            
            # 更新抽奖参与人数
            lottery = session.query(Lottery).filter(Lottery.id == lottery_id).first()
            if lottery:
                lottery.total_participants += 1
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            LOGGER.error(f"参与抽奖失败: {e}")
            return False


def sql_get_lottery(lottery_id: int) -> Optional[Lottery]:
    """获取抽奖信息"""
    with Session() as session:
        try:
            return session.query(Lottery).filter(Lottery.id == lottery_id).first()
        except Exception as e:
            LOGGER.error(f"获取抽奖信息失败: {e}")
            return None


def sql_get_active_lotteries() -> List[Lottery]:
    """获取所有活跃的抽奖"""
    with Session() as session:
        try:
            return session.query(Lottery).filter(Lottery.status == 'active').all()
        except Exception as e:
            LOGGER.error(f"获取活跃抽奖失败: {e}")
            return []


def sql_get_lottery_prizes(lottery_id: int) -> List[LotteryPrize]:
    """获取抽奖奖品列表"""
    with Session() as session:
        try:
            return session.query(LotteryPrize).filter(LotteryPrize.lottery_id == lottery_id).all()
        except Exception as e:
            LOGGER.error(f"获取抽奖奖品失败: {e}")
            return []


def sql_get_lottery_participants(lottery_id: int) -> List[LotteryParticipant]:
    """获取抽奖参与者列表"""
    with Session() as session:
        try:
            return session.query(LotteryParticipant).filter(
                LotteryParticipant.lottery_id == lottery_id
            ).all()
        except Exception as e:
            LOGGER.error(f"获取抽奖参与者失败: {e}")
            return []


def sql_check_user_participated(lottery_id: int, user_tg: int) -> bool:
    """检查用户是否已经参与抽奖"""
    with Session() as session:
        try:
            participant = session.query(LotteryParticipant).filter(
                and_(LotteryParticipant.lottery_id == lottery_id,
                     LotteryParticipant.user_tg == user_tg)
            ).first()
            return participant is not None
        except Exception as e:
            LOGGER.error(f"检查用户参与状态失败: {e}")
            return False


def sql_draw_lottery(lottery_id: int) -> Dict[str, Any]:
    """执行抽奖"""
    with Session() as session:
        try:
            # 获取抽奖信息
            lottery = session.query(Lottery).filter(Lottery.id == lottery_id).first()
            if not lottery or lottery.status != 'active':
                return {"success": False, "message": "抽奖不存在或已结束"}
            
            # 获取参与者
            participants = session.query(LotteryParticipant).filter(
                LotteryParticipant.lottery_id == lottery_id
            ).all()
            
            if not participants:
                return {"success": False, "message": "没有参与者"}
            
            # 获取奖品
            prizes = session.query(LotteryPrize).filter(
                LotteryPrize.lottery_id == lottery_id
            ).all()
            
            if not prizes:
                return {"success": False, "message": "没有奖品"}
            
            # 执行抽奖逻辑
            winners = []
            used_participants = set()
            
            for prize in prizes:
                available_participants = [p for p in participants if p.user_tg not in used_participants]
                
                if not available_participants:
                    break  # 没有更多参与者
                
                # 根据数量抽取获奖者
                for _ in range(min(prize.quantity, len(available_participants))):
                    if not available_participants:
                        break
                    
                    # 随机选择获奖者
                    winner_participant = random.choice(available_participants)
                    available_participants.remove(winner_participant)
                    used_participants.add(winner_participant.user_tg)
                    
                    # 记录获奖者
                    winner = LotteryWinner(
                        lottery_id=lottery_id,
                        prize_id=prize.id,
                        user_tg=winner_participant.user_tg,
                        user_name=winner_participant.user_name
                    )
                    session.add(winner)
                    winners.append({
                        "user_tg": winner_participant.user_tg,
                        "user_name": winner_participant.user_name,
                        "prize_name": prize.prize_name,
                        "prize_type": prize.prize_type,
                        "prize_value": prize.prize_value
                    })
            
            # 更新抽奖状态
            lottery.status = 'drawn'
            lottery.drawn_time = datetime.now()
            
            session.commit()
            
            return {
                "success": True,
                "message": "抽奖完成",
                "winners": winners,
                "total_participants": len(participants)
            }
            
        except Exception as e:
            session.rollback()
            LOGGER.error(f"执行抽奖失败: {e}")
            return {"success": False, "message": f"抽奖执行失败: {str(e)}"}


def sql_get_lottery_winners(lottery_id: int) -> List[LotteryWinner]:
    """获取抽奖获奖者列表"""
    with Session() as session:
        try:
            return session.query(LotteryWinner).filter(
                LotteryWinner.lottery_id == lottery_id
            ).all()
        except Exception as e:
            LOGGER.error(f"获取抽奖获奖者失败: {e}")
            return []


def sql_update_lottery_status(lottery_id: int, status: str) -> bool:
    """更新抽奖状态"""
    with Session() as session:
        try:
            lottery = session.query(Lottery).filter(Lottery.id == lottery_id).first()
            if lottery:
                lottery.status = status
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            LOGGER.error(f"更新抽奖状态失败: {e}")
            return False


def sql_claim_prize(lottery_id: int, user_tg: int, prize_id: int) -> bool:
    """标记奖品为已领取"""
    with Session() as session:
        try:
            winner = session.query(LotteryWinner).filter(
                and_(
                    LotteryWinner.lottery_id == lottery_id,
                    LotteryWinner.user_tg == user_tg,
                    LotteryWinner.prize_id == prize_id
                )
            ).first()
            
            if winner:
                winner.claimed = True
                winner.claim_time = datetime.now()
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            LOGGER.error(f"标记奖品领取失败: {e}")
            return False


def sql_check_lottery_ready_to_draw() -> List[Lottery]:
    """检查准备开奖的抽奖"""
    with Session() as session:
        try:
            now = datetime.now()
            
            # 时间触发的抽奖
            time_lotteries = session.query(Lottery).filter(
                and_(
                    Lottery.status == 'active',
                    Lottery.draw_type == 'time',
                    Lottery.draw_time <= now
                )
            ).all()
            
            # 人数触发的抽奖
            count_lotteries = session.query(Lottery).filter(
                and_(
                    Lottery.status == 'active',
                    Lottery.draw_type == 'count',
                    Lottery.total_participants >= Lottery.target_participants
                )
            ).all()
            
            return time_lotteries + count_lotteries
            
        except Exception as e:
            LOGGER.error(f"检查准备开奖的抽奖失败: {e}")
            return []