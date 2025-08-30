"""
抽奖系统数据库操作
"""
from bot.sql_helper import Base, Session, engine
from sqlalchemy import Column, BigInteger, String, DateTime, Integer, Boolean, Text
from sqlalchemy import func
from bot import LOGGER
from datetime import datetime
from typing import List, Optional


class LotteryEvent(Base):
    """
    抽奖活动表
    """
    __tablename__ = 'lottery_events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    creator_tg = Column(BigInteger, nullable=False)  # 创建者TG ID
    name = Column(String(255), nullable=False)  # 抽奖名称
    description = Column(Text, nullable=True)  # 抽奖描述
    lottery_type = Column(Integer, nullable=False, default=1)  # 1:关键字参与 2:按钮参与
    keyword = Column(String(100), nullable=True)  # 参与关键字(type=1时使用)
    draw_type = Column(Integer, nullable=False, default=1)  # 1:指定时间 2:人数达到
    draw_time = Column(DateTime, nullable=True)  # 开奖时间(draw_type=1时使用)
    target_participants = Column(Integer, nullable=True)  # 目标参与人数(draw_type=2时使用)
    participation_type = Column(Integer, nullable=False, default=3)  # 1:付费 2:仅emby用户 3:所有人
    participation_cost = Column(Integer, nullable=True, default=0)  # 参与费用
    status = Column(String(20), nullable=False, default='active')  # active, drawing, finished, cancelled
    message_id = Column(BigInteger, nullable=True)  # 抽奖消息ID
    chat_id = Column(BigInteger, nullable=True)  # 群组ID
    created_at = Column(DateTime, nullable=False, default=func.now())
    finished_at = Column(DateTime, nullable=True)
    
    
class LotteryPrize(Base):
    """
    抽奖奖品表
    """
    __tablename__ = 'lottery_prizes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    lottery_id = Column(Integer, nullable=False)  # 关联抽奖活动ID
    name = Column(String(255), nullable=False)  # 奖品名称
    quantity = Column(Integer, nullable=False, default=1)  # 奖品数量
    description = Column(Text, nullable=True)  # 奖品描述
    prize_type = Column(String(50), nullable=False, default='virtual')  # virtual, physical, coins等


class LotteryParticipant(Base):
    """
    抽奖参与者表
    """
    __tablename__ = 'lottery_participants'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    lottery_id = Column(Integer, nullable=False)  # 关联抽奖活动ID
    participant_tg = Column(BigInteger, nullable=False)  # 参与者TG ID
    participant_name = Column(String(255), nullable=True)  # 参与者名称
    participated_at = Column(DateTime, nullable=False, default=func.now())
    is_winner = Column(Boolean, nullable=False, default=False)
    prize_id = Column(Integer, nullable=True)  # 获得的奖品ID


# 创建表
LotteryEvent.__table__.create(bind=engine, checkfirst=True)
LotteryPrize.__table__.create(bind=engine, checkfirst=True) 
LotteryParticipant.__table__.create(bind=engine, checkfirst=True)


def sql_create_lottery(creator_tg: int, name: str, lottery_type: int, draw_type: int, 
                      participation_type: int, keyword: str = None, draw_time: datetime = None,
                      target_participants: int = None, participation_cost: int = 0,
                      description: str = None) -> Optional[int]:
    """创建抽奖活动"""
    with Session() as session:
        try:
            lottery = LotteryEvent(
                creator_tg=creator_tg,
                name=name,
                description=description,
                lottery_type=lottery_type,
                keyword=keyword,
                draw_type=draw_type,
                draw_time=draw_time,
                target_participants=target_participants,
                participation_type=participation_type,
                participation_cost=participation_cost
            )
            session.add(lottery)
            session.commit()
            return lottery.id
        except Exception as e:
            LOGGER.error(f"创建抽奖失败: {e}")
            session.rollback()
            return None


def sql_add_lottery_prize(lottery_id: int, name: str, quantity: int, 
                         description: str = None, prize_type: str = 'virtual') -> bool:
    """添加抽奖奖品"""
    with Session() as session:
        try:
            prize = LotteryPrize(
                lottery_id=lottery_id,
                name=name,
                quantity=quantity,
                description=description,
                prize_type=prize_type
            )
            session.add(prize)
            session.commit()
            return True
        except Exception as e:
            LOGGER.error(f"添加奖品失败: {e}")
            session.rollback()
            return False


def sql_join_lottery(lottery_id: int, participant_tg: int, participant_name: str) -> bool:
    """参与抽奖"""
    with Session() as session:
        try:
            # 检查是否已经参与
            existing = session.query(LotteryParticipant).filter(
                LotteryParticipant.lottery_id == lottery_id,
                LotteryParticipant.participant_tg == participant_tg
            ).first()
            
            if existing:
                return False  # 已经参与过
                
            participant = LotteryParticipant(
                lottery_id=lottery_id,
                participant_tg=participant_tg,
                participant_name=participant_name
            )
            session.add(participant)
            session.commit()
            return True
        except Exception as e:
            LOGGER.error(f"参与抽奖失败: {e}")
            session.rollback()
            return False


def sql_get_lottery_by_id(lottery_id: int) -> Optional[LotteryEvent]:
    """根据ID获取抽奖活动"""
    with Session() as session:
        try:
            return session.query(LotteryEvent).filter(LotteryEvent.id == lottery_id).first()
        except Exception as e:
            LOGGER.error(f"获取抽奖活动失败: {e}")
            return None


def sql_get_active_lotteries() -> List[LotteryEvent]:
    """获取所有活跃的抽奖活动"""
    with Session() as session:
        try:
            return session.query(LotteryEvent).filter(LotteryEvent.status == 'active').all()
        except Exception as e:
            LOGGER.error(f"获取活跃抽奖失败: {e}")
            return []


def sql_get_lottery_participants(lottery_id: int) -> List[LotteryParticipant]:
    """获取抽奖参与者"""
    with Session() as session:
        try:
            return session.query(LotteryParticipant).filter(
                LotteryParticipant.lottery_id == lottery_id
            ).all()
        except Exception as e:
            LOGGER.error(f"获取参与者失败: {e}")
            return []


def sql_get_lottery_prizes(lottery_id: int) -> List[LotteryPrize]:
    """获取抽奖奖品"""
    with Session() as session:
        try:
            return session.query(LotteryPrize).filter(
                LotteryPrize.lottery_id == lottery_id
            ).all()
        except Exception as e:
            LOGGER.error(f"获取奖品失败: {e}")
            return []


def sql_update_lottery_status(lottery_id: int, status: str) -> bool:
    """更新抽奖状态"""
    with Session() as session:
        try:
            lottery = session.query(LotteryEvent).filter(LotteryEvent.id == lottery_id).first()
            if lottery:
                lottery.status = status
                if status == 'finished':
                    lottery.finished_at = func.now()
                session.commit()
                return True
            return False
        except Exception as e:
            LOGGER.error(f"更新抽奖状态失败: {e}")
            session.rollback()
            return False


def sql_set_lottery_winners(lottery_id: int, winners: List[tuple]) -> bool:
    """设置抽奖获奖者 winners格式: [(participant_tg, prize_id), ...]"""
    with Session() as session:
        try:
            for participant_tg, prize_id in winners:
                participant = session.query(LotteryParticipant).filter(
                    LotteryParticipant.lottery_id == lottery_id,
                    LotteryParticipant.participant_tg == participant_tg
                ).first()
                if participant:
                    participant.is_winner = True
                    participant.prize_id = prize_id
            session.commit()
            return True
        except Exception as e:
            LOGGER.error(f"设置获奖者失败: {e}")
            session.rollback()
            return False


def sql_update_lottery_message(lottery_id: int, message_id: int, chat_id: int) -> bool:
    """更新抽奖消息ID"""
    with Session() as session:
        try:
            lottery = session.query(LotteryEvent).filter(LotteryEvent.id == lottery_id).first()
            if lottery:
                lottery.message_id = message_id
                lottery.chat_id = chat_id
                session.commit()
                return True
            return False
        except Exception as e:
            LOGGER.error(f"更新抽奖消息失败: {e}")
            session.rollback()
            return False


def sql_count_lottery_participants(lottery_id: int) -> int:
    """统计抽奖参与人数"""
    with Session() as session:
        try:
            return session.query(LotteryParticipant).filter(
                LotteryParticipant.lottery_id == lottery_id
            ).count()
        except Exception as e:
            LOGGER.error(f"统计参与人数失败: {e}")
            return 0