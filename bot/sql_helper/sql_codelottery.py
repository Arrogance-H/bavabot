"""
抽奖系统SQL操作模块
"""
import random
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from bot.sql_helper import Base, Session, engine
from sqlalchemy import (
    Column,
    BigInteger,
    String,
    DateTime,
    Integer,
    Boolean,
    Text,
    func,
    and_,
    or_,
)


class CodeLotteryRound(Base):
    """
    抽奖轮次表
    """
    __tablename__ = "code_lottery_rounds"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    lottery_name = Column(String(200), nullable=False)  # 抽奖名称
    creator_tg = Column(BigInteger, nullable=False)     # 创建者TG ID
    start_time = Column(DateTime, nullable=False)       # 开始时间
    end_time = Column(DateTime, nullable=False)         # 结束时间
    entry_fee = Column(Integer, default=3)              # 参与费用
    winner_count = Column(Integer, default=1)           # 获奖人数
    status = Column(String(20), default='active')       # 状态：active, completed, cancelled
    draw_time = Column(DateTime, nullable=True)         # 实际开奖时间
    created_at = Column(DateTime, default=datetime.now)


class CodeLotteryParticipant(Base):
    """
    抽奖参与者表
    """
    __tablename__ = "code_lottery_participants"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    round_id = Column(Integer, nullable=False)          # 抽奖轮次ID
    tg = Column(BigInteger, nullable=False)             # 参与者TG ID
    username = Column(String(255), nullable=True)      # 用户名
    entry_time = Column(DateTime, default=datetime.now) # 参与时间
    guaranteed_count = Column(Integer, default=0)       # 保底次数


class CodeLotteryWinner(Base):
    """
    抽奖获奖者表
    """
    __tablename__ = "code_lottery_winners"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    round_id = Column(Integer, nullable=False)          # 抽奖轮次ID
    tg = Column(BigInteger, nullable=False)             # 获奖者TG ID
    username = Column(String(255), nullable=True)      # 用户名
    prize_name = Column(String(200), nullable=False)   # 奖品名称
    win_time = Column(DateTime, default=datetime.now)  # 获奖时间
    notified = Column(Boolean, default=False)          # 是否已通知


class CodeLotteryUser(Base):
    """
    用户抽奖统计表
    """
    __tablename__ = "code_lottery_users"
    
    tg = Column(BigInteger, primary_key=True, autoincrement=False)
    total_participation = Column(Integer, default=0)    # 总参与次数
    total_wins = Column(Integer, default=0)             # 总获奖次数
    guaranteed_count = Column(Integer, default=0)       # 当前保底次数
    last_participation = Column(DateTime, nullable=True) # 最后参与时间
    last_win = Column(DateTime, nullable=True)          # 最后获奖时间


# 创建表
CodeLotteryRound.__table__.create(bind=engine, checkfirst=True)
CodeLotteryParticipant.__table__.create(bind=engine, checkfirst=True)
CodeLotteryWinner.__table__.create(bind=engine, checkfirst=True)
CodeLotteryUser.__table__.create(bind=engine, checkfirst=True)


def _migrate_code_lottery_rounds_table():
    """
    检查并修复 code_lottery_rounds 表结构
    确保所有必需的列都存在
    """
    from sqlalchemy import inspect, text
    
    try:
        with Session() as session:
            inspector = inspect(engine)
            
            # 检查表是否存在
            if 'code_lottery_rounds' not in inspector.get_table_names():
                return  # 表不存在，create 会处理
                
            # 获取现有列
            existing_columns = [col['name'] for col in inspector.get_columns('code_lottery_rounds')]
            
            # 需要添加的列定义
            required_columns = {
                'creator_tg': 'BIGINT NOT NULL DEFAULT 0 COMMENT "创建者TG ID"'
            }
            
            # 检查并添加缺失的列
            columns_added = False
            for col_name, col_definition in required_columns.items():
                if col_name not in existing_columns:
                    alter_sql = f"ALTER TABLE code_lottery_rounds ADD COLUMN {col_name} {col_definition}"
                    session.execute(text(alter_sql))
                    columns_added = True
                    
            if columns_added:
                session.commit()
                    
    except Exception as e:
        # Silently handle migration errors to avoid breaking the module import
        # Errors will surface when functions are actually called
        pass


def _migrate_code_lottery_users_table():
    """
    检查并修复 code_lottery_users 表结构
    确保所有必需的列都存在
    """
    from sqlalchemy import inspect, text
    
    try:
        with Session() as session:
            inspector = inspect(engine)
            
            # 检查表是否存在
            if 'code_lottery_users' not in inspector.get_table_names():
                return  # 表不存在，create 会处理
                
            # 获取现有列
            existing_columns = [col['name'] for col in inspector.get_columns('code_lottery_users')]
            
            # 需要添加的列定义
            required_columns = {
                'total_participation': 'INT DEFAULT 0 COMMENT "总参与次数"',
                'total_wins': 'INT DEFAULT 0 COMMENT "总获奖次数"',  
                'guaranteed_count': 'INT DEFAULT 0 COMMENT "当前保底次数"',
                'last_participation': 'DATETIME NULL COMMENT "最后参与时间"',
                'last_win': 'DATETIME NULL COMMENT "最后获奖时间"'
            }
            
            # 检查并添加缺失的列
            columns_added = False
            for col_name, col_definition in required_columns.items():
                if col_name not in existing_columns:
                    alter_sql = f"ALTER TABLE code_lottery_users ADD COLUMN {col_name} {col_definition}"
                    session.execute(text(alter_sql))
                    columns_added = True
                    
            if columns_added:
                session.commit()
                    
    except Exception as e:
        # Silently handle migration errors to avoid breaking the module import
        # Errors will surface when functions are actually called
        pass


# 执行迁移（仅在模块加载时运行一次）
_migrate_code_lottery_rounds_table()
_migrate_code_lottery_users_table()


def sql_create_lottery_round(creator_tg: int, lottery_name: str, duration_minutes: int, 
                           entry_fee: int, winner_count: int) -> Optional[int]:
    """创建新的抽奖轮次"""
    with Session() as session:
        try:
            start_time = datetime.now()
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            round_obj = CodeLotteryRound(
                lottery_name=lottery_name,
                creator_tg=creator_tg,
                start_time=start_time,
                end_time=end_time,
                entry_fee=entry_fee,
                winner_count=winner_count,
                status='active'
            )
            session.add(round_obj)
            session.commit()
            return round_obj.id
        except Exception as e:
            session.rollback()
            return None


def sql_get_active_lottery() -> Optional[CodeLotteryRound]:
    """获取当前活跃的抽奖轮次"""
    with Session() as session:
        return session.query(CodeLotteryRound).filter(
            CodeLotteryRound.status == 'active'
        ).first()


def sql_join_lottery(round_id: int, tg: int, username: str) -> bool:
    """用户参与抽奖"""
    with Session() as session:
        try:
            # 检查是否已经参与
            existing = session.query(CodeLotteryParticipant).filter(
                and_(
                    CodeLotteryParticipant.round_id == round_id,
                    CodeLotteryParticipant.tg == tg
                )
            ).first()
            
            if existing:
                return False  # 已经参与过
            
            # 获取用户统计信息
            user_stats = session.query(CodeLotteryUser).filter(
                CodeLotteryUser.tg == tg
            ).first()
            
            if not user_stats:
                user_stats = CodeLotteryUser(tg=tg)
                session.add(user_stats)
            
            # 添加参与记录
            participant = CodeLotteryParticipant(
                round_id=round_id,
                tg=tg,
                username=username,
                guaranteed_count=user_stats.guaranteed_count
            )
            session.add(participant)
            
            # 更新用户统计
            user_stats.total_participation += 1
            user_stats.last_participation = datetime.now()
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            return False


def sql_get_lottery_participants(round_id: int) -> List[CodeLotteryParticipant]:
    """获取抽奖参与者列表"""
    with Session() as session:
        return session.query(CodeLotteryParticipant).filter(
            CodeLotteryParticipant.round_id == round_id
        ).all()


def sql_draw_lottery(round_id: int, lottery_name: str) -> List[CodeLotteryWinner]:
    """执行抽奖"""
    with Session() as session:
        try:
            # 获取抽奖轮次信息
            lottery_round = session.query(CodeLotteryRound).filter(
                CodeLotteryRound.id == round_id
            ).first()
            
            if not lottery_round or lottery_round.status != 'active':
                return []
            
            # 获取所有参与者
            participants = session.query(CodeLotteryParticipant).filter(
                CodeLotteryParticipant.round_id == round_id
            ).all()
            
            if not participants:
                return []
            
            winners = []
            winner_count = min(lottery_round.winner_count, len(participants))
            
            # 首先处理保底用户
            guaranteed_participants = [p for p in participants if p.guaranteed_count >= 10]
            guaranteed_winners = []
            
            if guaranteed_participants:
                guaranteed_winner_count = min(len(guaranteed_participants), winner_count)
                guaranteed_winners = random.sample(guaranteed_participants, guaranteed_winner_count)
                winners.extend(guaranteed_winners)
            
            # 如果还有名额，从剩余用户中抽取
            remaining_count = winner_count - len(winners)
            if remaining_count > 0:
                remaining_participants = [p for p in participants if p not in guaranteed_winners]
                if remaining_participants:
                    additional_winners = random.sample(
                        remaining_participants, 
                        min(remaining_count, len(remaining_participants))
                    )
                    winners.extend(additional_winners)
            
            # 记录获奖者
            winner_records = []
            for winner in winners:
                winner_record = CodeLotteryWinner(
                    round_id=round_id,
                    tg=winner.tg,
                    username=winner.username,
                    prize_name=lottery_name
                )
                session.add(winner_record)
                winner_records.append(winner_record)
                
                # 更新用户统计
                user_stats = session.query(CodeLotteryUser).filter(
                    CodeLotteryUser.tg == winner.tg
                ).first()
                if user_stats:
                    user_stats.total_wins += 1
                    user_stats.guaranteed_count = 0  # 重置保底次数
                    user_stats.last_win = datetime.now()
            
            # 更新未中奖用户的保底次数
            for participant in participants:
                if participant not in winners:
                    user_stats = session.query(CodeLotteryUser).filter(
                        CodeLotteryUser.tg == participant.tg
                    ).first()
                    if user_stats:
                        user_stats.guaranteed_count += 1
            
            # 更新抽奖状态
            lottery_round.status = 'completed'
            lottery_round.draw_time = datetime.now()
            
            session.commit()
            return winner_records
        
        except Exception as e:
            session.rollback()
            return []


def sql_cancel_lottery(round_id: int) -> bool:
    """取消抽奖"""
    with Session() as session:
        try:
            lottery_round = session.query(CodeLotteryRound).filter(
                CodeLotteryRound.id == round_id
            ).first()
            
            if lottery_round:
                lottery_round.status = 'cancelled'
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            return False


def sql_get_lottery_stats(tg: int) -> dict:
    """获取用户抽奖统计"""
    with Session() as session:
        user_stats = session.query(CodeLotteryUser).filter(
            CodeLotteryUser.tg == tg
        ).first()
        
        if not user_stats:
            return {
                'total_participation': 0,
                'total_wins': 0,
                'guaranteed_count': 0,
                'win_rate': '0%'
            }
        
        win_rate = (user_stats.total_wins / user_stats.total_participation * 100) if user_stats.total_participation > 0 else 0
        
        return {
            'total_participation': user_stats.total_participation,
            'total_wins': user_stats.total_wins,
            'guaranteed_count': user_stats.guaranteed_count,
            'win_rate': f'{win_rate:.1f}%'
        }


def sql_get_expired_lotteries() -> List[CodeLotteryRound]:
    """获取已过期但未开奖的抽奖"""
    with Session() as session:
        return session.query(CodeLotteryRound).filter(
            and_(
                CodeLotteryRound.status == 'active',
                CodeLotteryRound.end_time <= datetime.now()
            )
        ).all()


def sql_mark_winner_notified(winner_id: int) -> bool:
    """标记获奖者已通知"""
    with Session() as session:
        try:
            winner = session.query(CodeLotteryWinner).filter(
                CodeLotteryWinner.id == winner_id
            ).first()
            if winner:
                winner.notified = True
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            return False