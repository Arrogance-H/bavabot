"""
抽奖系统数据库操作
"""
import datetime
from bot.sql_helper import Base, Session, engine
from sqlalchemy import Column, BigInteger, String, DateTime, Integer, Boolean
from sqlalchemy import func
from bot import LOGGER


class Lottery(Base):
    """
    抽奖参与记录表
    """
    __tablename__ = 'lottery'
    id = Column(Integer, primary_key=True, autoincrement=True)
    tg = Column(BigInteger, nullable=False)  # 用户telegram id
    participation_count = Column(Integer, default=0)  # 总参与次数
    wins_count = Column(Integer, default=0)  # 获奖次数
    consecutive_losses = Column(Integer, default=0)  # 连续未中奖次数
    last_participation = Column(DateTime, nullable=True)  # 最后参与时间
    created_date = Column(DateTime, default=datetime.datetime.now)  # 创建时间


# 创建表
Lottery.__table__.create(bind=engine, checkfirst=True)


def sql_get_lottery_record(tg: int):
    """获取用户抽奖记录"""
    with Session() as session:
        try:
            record = session.query(Lottery).filter(Lottery.tg == tg).first()
            return record
        except Exception as e:
            LOGGER.error(f"获取抽奖记录失败: {e}")
            return None


def sql_create_lottery_record(tg: int):
    """创建用户抽奖记录"""
    with Session() as session:
        try:
            # 检查是否已存在
            existing = session.query(Lottery).filter(Lottery.tg == tg).first()
            if existing:
                return existing
            
            record = Lottery(tg=tg)
            session.add(record)
            session.commit()
            return record
        except Exception as e:
            LOGGER.error(f"创建抽奖记录失败: {e}")
            session.rollback()
            return None


def sql_update_lottery_participation(tg: int, won: bool):
    """更新用户抽奖参与记录"""
    with Session() as session:
        try:
            record = session.query(Lottery).filter(Lottery.tg == tg).first()
            if not record:
                # 如果没有记录，先创建
                record = Lottery(tg=tg)
                session.add(record)
            
            # 更新记录
            record.participation_count += 1
            record.last_participation = datetime.datetime.now()
            
            if won:
                record.wins_count += 1
                record.consecutive_losses = 0  # 重置连续失败次数
            else:
                record.consecutive_losses += 1
            
            session.commit()
            return record
        except Exception as e:
            LOGGER.error(f"更新抽奖记录失败: {e}")
            session.rollback()
            return None


def sql_get_lottery_stats():
    """获取抽奖统计信息"""
    with Session() as session:
        try:
            total_participants = session.query(func.count(Lottery.tg)).scalar() or 0
            total_participations = session.query(func.sum(Lottery.participation_count)).scalar() or 0
            total_wins = session.query(func.sum(Lottery.wins_count)).scalar() or 0
            
            return {
                'total_participants': total_participants,
                'total_participations': total_participations,
                'total_wins': total_wins,
                'win_rate': round(total_wins / max(total_participations, 1) * 100, 2)
            }
        except Exception as e:
            LOGGER.error(f"获取抽奖统计失败: {e}")
            return None