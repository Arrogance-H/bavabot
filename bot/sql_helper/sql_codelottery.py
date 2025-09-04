"""
抽奖系统数据库操作 (CodeLottery System)
"""
import datetime
from bot.sql_helper import Base, Session, engine
from sqlalchemy import Column, BigInteger, String, DateTime, Integer, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy import func
from bot import LOGGER


class CodeLotteryUser(Base):
    """
    抽奖用户记录表 - 跟踪用户的总参与次数和资格
    """
    __tablename__ = 'code_lottery_users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    tg = Column(BigInteger, unique=True, nullable=False)  # 用户telegram id
    total_participations = Column(Integer, default=0)  # 总参与次数
    total_wins = Column(Integer, default=0)  # 总获奖次数
    created_date = Column(DateTime, default=datetime.datetime.now)  # 创建时间
    updated_date = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)


class CodeLotteryRound(Base):
    """
    抽奖轮次表 - 每次开启的抽奖活动
    """
    __tablename__ = 'code_lottery_rounds'
    id = Column(Integer, primary_key=True, autoincrement=True)
    round_number = Column(Integer, nullable=False)  # 第几次抽奖
    lottery_name = Column(String(100), nullable=False)  # 抽奖名称
    max_participants = Column(Integer, nullable=False)  # 最大参与人数
    entry_fee = Column(Integer, nullable=False)  # 参与费用
    winner_count = Column(Integer, default=1)  # 获奖人数
    status = Column(String(20), default='active')  # active, completed, cancelled
    created_by = Column(BigInteger, nullable=False)  # 创建者 (管理员)
    created_date = Column(DateTime, default=datetime.datetime.now)  # 创建时间
    completed_date = Column(DateTime, nullable=True)  # 完成时间
    
    # 关联关系
    participants = relationship("CodeLotteryParticipant", back_populates="round")
    winners = relationship("CodeLotteryWinner", back_populates="round")


class CodeLotteryParticipant(Base):
    """
    抽奖参与者表 - 每轮抽奖的参与记录
    """
    __tablename__ = 'code_lottery_participants'
    id = Column(Integer, primary_key=True, autoincrement=True)
    round_id = Column(Integer, ForeignKey('code_lottery_rounds.id'), nullable=False)
    tg = Column(BigInteger, nullable=False)  # 参与者 telegram id
    nickname = Column(String(100), nullable=True)  # 参与者昵称
    participation_date = Column(DateTime, default=datetime.datetime.now)  # 参与时间
    
    # 关联关系
    round = relationship("CodeLotteryRound", back_populates="participants")


class CodeLotteryWinner(Base):
    """
    抽奖获奖者表 - 每轮抽奖的获奖记录
    """
    __tablename__ = 'code_lottery_winners'
    id = Column(Integer, primary_key=True, autoincrement=True)
    round_id = Column(Integer, ForeignKey('code_lottery_rounds.id'), nullable=False)
    tg = Column(BigInteger, nullable=False)  # 获奖者 telegram id
    nickname = Column(String(100), nullable=True)  # 获奖者昵称
    total_participations_at_win = Column(Integer, nullable=False)  # 获奖时的累计参与次数
    win_date = Column(DateTime, default=datetime.datetime.now)  # 获奖时间
    notified = Column(Boolean, default=False)  # 是否已通知
    
    # 关联关系
    round = relationship("CodeLotteryRound", back_populates="winners")


# 创建表
CodeLotteryUser.__table__.create(bind=engine, checkfirst=True)
CodeLotteryRound.__table__.create(bind=engine, checkfirst=True)
CodeLotteryParticipant.__table__.create(bind=engine, checkfirst=True)
CodeLotteryWinner.__table__.create(bind=engine, checkfirst=True)


def sql_get_codelottery_user(tg: int):
    """获取用户抽奖记录"""
    with Session() as session:
        try:
            user = session.query(CodeLotteryUser).filter(CodeLotteryUser.tg == tg).first()
            return user
        except Exception as e:
            LOGGER.error(f"获取抽奖用户记录失败: {e}")
            return None


def sql_create_codelottery_user(tg: int):
    """创建用户抽奖记录"""
    with Session() as session:
        try:
            # 检查是否已存在
            existing = session.query(CodeLotteryUser).filter(CodeLotteryUser.tg == tg).first()
            if existing:
                return existing
            
            user = CodeLotteryUser(tg=tg)
            session.add(user)
            session.commit()
            return user
        except Exception as e:
            LOGGER.error(f"创建抽奖用户记录失败: {e}")
            session.rollback()
            return None


def sql_get_active_lottery_round():
    """获取当前活跃的抽奖轮次"""
    with Session() as session:
        try:
            round_obj = session.query(CodeLotteryRound).filter(
                CodeLotteryRound.status == 'active'
            ).first()
            return round_obj
        except Exception as e:
            LOGGER.error(f"获取活跃抽奖轮次失败: {e}")
            return None


def sql_create_lottery_round(round_number: int, lottery_name: str, max_participants: int, 
                           entry_fee: int, winner_count: int, created_by: int):
    """创建新的抽奖轮次"""
    with Session() as session:
        try:
            round_obj = CodeLotteryRound(
                round_number=round_number,
                lottery_name=lottery_name,
                max_participants=max_participants,
                entry_fee=entry_fee,
                winner_count=winner_count,
                created_by=created_by
            )
            session.add(round_obj)
            session.commit()
            return round_obj
        except Exception as e:
            LOGGER.error(f"创建抽奖轮次失败: {e}")
            session.rollback()
            return None


def sql_join_lottery_round(round_id: int, tg: int, nickname: str):
    """用户参与抽奖轮次"""
    with Session() as session:
        try:
            # 检查是否已经参与
            existing = session.query(CodeLotteryParticipant).filter(
                CodeLotteryParticipant.round_id == round_id,
                CodeLotteryParticipant.tg == tg
            ).first()
            
            if existing:
                return None, "已参与"
            
            # 检查轮次是否存在且活跃
            round_obj = session.query(CodeLotteryRound).filter(
                CodeLotteryRound.id == round_id,
                CodeLotteryRound.status == 'active'
            ).first()
            
            if not round_obj:
                return None, "抽奖轮次无效"
            
            # 检查参与人数是否已满
            participant_count = session.query(func.count(CodeLotteryParticipant.id)).filter(
                CodeLotteryParticipant.round_id == round_id
            ).scalar()
            
            if participant_count >= round_obj.max_participants:
                return None, "参与人数已满"
            
            # 添加参与记录
            participant = CodeLotteryParticipant(
                round_id=round_id,
                tg=tg,
                nickname=nickname
            )
            session.add(participant)
            
            # 更新用户总参与次数
            user = session.query(CodeLotteryUser).filter(CodeLotteryUser.tg == tg).first()
            if not user:
                user = CodeLotteryUser(tg=tg)
                session.add(user)
            user.total_participations += 1
            user.updated_date = datetime.datetime.now()
            
            session.commit()
            return participant, "参与成功"
            
        except Exception as e:
            LOGGER.error(f"参与抽奖失败: {e}")
            session.rollback()
            return None, "系统错误"


def sql_get_lottery_participants(round_id: int):
    """获取抽奖参与者列表"""
    with Session() as session:
        try:
            participants = session.query(CodeLotteryParticipant).filter(
                CodeLotteryParticipant.round_id == round_id
            ).all()
            return participants
        except Exception as e:
            LOGGER.error(f"获取参与者列表失败: {e}")
            return []


def sql_complete_lottery_round(round_id: int, winners: list):
    """完成抽奖轮次并记录获奖者"""
    with Session() as session:
        try:
            # 更新轮次状态
            round_obj = session.query(CodeLotteryRound).filter(
                CodeLotteryRound.id == round_id
            ).first()
            
            if not round_obj:
                return False, "轮次不存在"
            
            round_obj.status = 'completed'
            round_obj.completed_date = datetime.datetime.now()
            
            # 记录获奖者
            for winner_info in winners:
                tg = winner_info['tg']
                nickname = winner_info['nickname']
                
                # 获取用户总参与次数
                user = session.query(CodeLotteryUser).filter(CodeLotteryUser.tg == tg).first()
                total_participations = user.total_participations if user else 0
                
                winner = CodeLotteryWinner(
                    round_id=round_id,
                    tg=tg,
                    nickname=nickname,
                    total_participations_at_win=total_participations
                )
                session.add(winner)
                
                # 更新用户获奖次数
                if user:
                    user.total_wins += 1
                    user.updated_date = datetime.datetime.now()
            
            session.commit()
            return True, "开奖完成"
            
        except Exception as e:
            LOGGER.error(f"完成抽奖失败: {e}")
            session.rollback()
            return False, "系统错误"


def sql_get_lottery_statistics():
    """获取抽奖统计信息"""
    with Session() as session:
        try:
            # 全局统计
            total_users = session.query(func.count(CodeLotteryUser.id)).scalar() or 0
            total_rounds = session.query(func.count(CodeLotteryRound.id)).scalar() or 0
            total_participations = session.query(func.sum(CodeLotteryUser.total_participations)).scalar() or 0
            total_wins = session.query(func.sum(CodeLotteryUser.total_wins)).scalar() or 0
            
            # 当前活跃轮次
            active_round = session.query(CodeLotteryRound).filter(
                CodeLotteryRound.status == 'active'
            ).first()
            
            return {
                'total_users': total_users,
                'total_rounds': total_rounds,
                'total_participations': total_participations,
                'total_wins': total_wins,
                'active_round': active_round
            }
        except Exception as e:
            LOGGER.error(f"获取抽奖统计失败: {e}")
            return None


def sql_get_user_in_round(round_id: int, tg: int):
    """检查用户是否已参与指定轮次"""
    with Session() as session:
        try:
            participant = session.query(CodeLotteryParticipant).filter(
                CodeLotteryParticipant.round_id == round_id,
                CodeLotteryParticipant.tg == tg
            ).first()
            return participant
        except Exception as e:
            LOGGER.error(f"检查用户参与状态失败: {e}")
            return None