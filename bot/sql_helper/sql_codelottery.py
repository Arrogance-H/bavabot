"""
抽奖系统数据库操作 (CodeLottery System)
Enhanced with hunt system patterns for better reliability and performance
"""
import datetime
from bot.sql_helper import Base, Session, engine
from sqlalchemy import Column, BigInteger, String, DateTime, Integer, Boolean, Text, ForeignKey, text
from sqlalchemy.orm import relationship
from sqlalchemy import func, inspect
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
    duration_minutes = Column(Integer, nullable=False)  # 抽奖持续时间（分钟）
    entry_fee = Column(Integer, nullable=False)  # 参与费用
    winner_count = Column(Integer, default=1)  # 获奖人数
    status = Column(String(20), default='active')  # active, completed, cancelled
    created_by = Column(BigInteger, nullable=False)  # 创建者 (管理员)
    created_date = Column(DateTime, default=datetime.datetime.now)  # 创建时间
    end_time = Column(DateTime, nullable=False)  # 抽奖结束时间
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

# 自动检查并修复数据库结构 - 借鉴hunt系统的自动修复机制
try:
    if sql_check_and_fix_codelottery_tables():
        LOGGER.info("🎲 CodeLottery database structure verified and ready")
    else:
        LOGGER.warning("⚠️ CodeLottery database structure check failed - some features may not work")
except Exception as e:
    LOGGER.error(f"❌ CodeLottery database auto-check failed: {e}")


def sql_check_and_fix_codelottery_tables():
    """检查并修复抽奖系统表结构 - 借鉴hunt系统的自动修复机制"""
    try:
        inspector = inspect(engine)
        
        # 检查所有抽奖相关表是否存在
        required_tables = [
            'code_lottery_users', 
            'code_lottery_rounds', 
            'code_lottery_participants', 
            'code_lottery_winners'
        ]
        
        existing_tables = inspector.get_table_names()
        missing_tables = []
        
        for table_name in required_tables:
            if table_name not in existing_tables:
                missing_tables.append(table_name)
        
        if missing_tables:
            LOGGER.error(f"❌ CodeLottery missing tables: {missing_tables}")
            return False
        
        # 检查表结构的完整性 - 可以根据需要添加列检查
        # 这里可以添加类似hunt系统的列检查逻辑
        
        LOGGER.info("✅ CodeLottery table structure is up to date")
        return True
        
    except Exception as e:
        LOGGER.error(f"❌ Error checking CodeLottery table structure: {e}")
        return False


def sql_get_codelottery_user(tg: int):
    """获取用户抽奖记录 - 增强错误处理和日志记录"""
    with Session() as session:
        try:
            user = session.query(CodeLotteryUser).filter(CodeLotteryUser.tg == tg).first()
            if user:
                session.refresh(user)
                LOGGER.debug(f"🎲 获取抽奖用户记录成功: {tg}, 参与次数: {user.total_participations}")
            else:
                LOGGER.debug(f"🎲 用户 {tg} 尚未参与抽奖")
            return user
        except Exception as e:
            LOGGER.error(f"❌ 获取抽奖用户记录失败 (用户 {tg}): {e}")
            return None


def sql_create_codelottery_user(tg: int):
    """创建用户抽奖记录 - 增强事务处理和错误恢复"""
    with Session() as session:
        try:
            # 检查是否已存在
            existing = session.query(CodeLotteryUser).filter(CodeLotteryUser.tg == tg).first()
            if existing:
                session.refresh(existing)
                LOGGER.debug(f"🎲 用户 {tg} 抽奖记录已存在")
                return existing
            
            user = CodeLotteryUser(tg=tg)
            session.add(user)
            session.commit()
            session.refresh(user)
            LOGGER.info(f"🎲 成功创建用户 {tg} 的抽奖记录")
            return user
            
        except Exception as e:
            LOGGER.error(f"❌ 创建抽奖用户记录失败 (用户 {tg}): {e}")
            session.rollback()
            # 尝试再次查找，可能是并发创建导致的
            try:
                existing = session.query(CodeLotteryUser).filter(CodeLotteryUser.tg == tg).first()
                if existing:
                    session.refresh(existing)
                    LOGGER.info(f"🎲 并发创建检测：用户 {tg} 记录已存在")
                    return existing
            except Exception as retry_e:
                LOGGER.error(f"❌ 重试查找用户记录也失败 (用户 {tg}): {retry_e}")
            return None


def sql_get_active_lottery_round():
    """获取当前活跃的抽奖轮次 - 增强会话管理和缓存"""
    with Session() as session:
        try:
            round_obj = session.query(CodeLotteryRound).filter(
                CodeLotteryRound.status == 'active'
            ).first()
            
            if round_obj:
                session.refresh(round_obj)
                # 检查是否已过期但状态仍为活跃
                if datetime.datetime.now() > round_obj.end_time:
                    LOGGER.warning(f"🎲 发现过期但仍活跃的抽奖轮次: {round_obj.id}")
                    # 可以选择在这里自动标记为过期，但保持原有逻辑
                LOGGER.debug(f"🎲 获取活跃抽奖轮次: {round_obj.round_number}, 状态: {round_obj.status}")
            else:
                LOGGER.debug("🎲 当前没有活跃的抽奖轮次")
                
            return round_obj
        except Exception as e:
            LOGGER.error(f"❌ 获取活跃抽奖轮次失败: {e}")
            return None


def sql_create_lottery_round(round_number: int, lottery_name: str, duration_minutes: int, 
                           entry_fee: int, winner_count: int, created_by: int):
    """创建新的抽奖轮次 - 增强参数验证和错误处理"""
    with Session() as session:
        try:
            # 参数验证
            if duration_minutes <= 0:
                LOGGER.error(f"❌ 无效的抽奖持续时间: {duration_minutes} 分钟")
                return None
                
            if winner_count <= 0:
                LOGGER.error(f"❌ 无效的获奖人数: {winner_count}")
                return None
                
            if entry_fee < 0:
                LOGGER.error(f"❌ 无效的参与费用: {entry_fee}")
                return None
            
            # 检查是否已有活跃轮次
            existing_active = session.query(CodeLotteryRound).filter(
                CodeLotteryRound.status == 'active'
            ).first()
            
            if existing_active:
                LOGGER.warning(f"🎲 尝试创建新轮次时发现已有活跃轮次: {existing_active.id}")
                return None
            
            # 计算结束时间
            end_time = datetime.datetime.now() + datetime.timedelta(minutes=duration_minutes)
            
            round_obj = CodeLotteryRound(
                round_number=round_number,
                lottery_name=lottery_name,
                duration_minutes=duration_minutes,
                entry_fee=entry_fee,
                winner_count=winner_count,
                created_by=created_by,
                end_time=end_time
            )
            session.add(round_obj)
            session.commit()
            session.refresh(round_obj)
            
            LOGGER.info(f"🎲 成功创建抽奖轮次: {round_number}, 名称: {lottery_name}, "
                       f"持续: {duration_minutes}分钟, 获奖人数: {winner_count}")
            return round_obj
            
        except Exception as e:
            LOGGER.error(f"❌ 创建抽奖轮次失败: {e}")
            session.rollback()
            return None


def sql_join_lottery_round(round_id: int, tg: int, nickname: str):
    """用户参与抽奖轮次 - 增强参数验证和事务处理"""
    with Session() as session:
        try:
            # 参数验证
            if not nickname or len(nickname.strip()) == 0:
                LOGGER.warning(f"🎲 用户 {tg} 尝试以空昵称参与抽奖轮次 {round_id}")
                return None, "昵称不能为空"
            
            # 检查是否已经参与
            existing = session.query(CodeLotteryParticipant).filter(
                CodeLotteryParticipant.round_id == round_id,
                CodeLotteryParticipant.tg == tg
            ).first()
            
            if existing:
                LOGGER.debug(f"🎲 用户 {tg} 已参与抽奖轮次 {round_id}")
                return None, "已参与"
            
            # 检查轮次是否存在且活跃
            round_obj = session.query(CodeLotteryRound).filter(
                CodeLotteryRound.id == round_id,
                CodeLotteryRound.status == 'active'
            ).first()
            
            if not round_obj:
                LOGGER.warning(f"🎲 用户 {tg} 尝试参与无效的抽奖轮次 {round_id}")
                return None, "抽奖轮次无效"
            
            # 检查抽奖是否已过期
            current_time = datetime.datetime.now()
            if current_time > round_obj.end_time:
                LOGGER.warning(f"🎲 用户 {tg} 尝试参与已结束的抽奖轮次 {round_id}")
                return None, "抽奖已结束"
            
            # 添加参与记录
            participant = CodeLotteryParticipant(
                round_id=round_id,
                tg=tg,
                nickname=nickname.strip()  # 清理昵称
            )
            session.add(participant)
            
            # 更新用户总参与次数 - 确保用户记录存在
            user = session.query(CodeLotteryUser).filter(CodeLotteryUser.tg == tg).first()
            if not user:
                user = CodeLotteryUser(tg=tg)
                session.add(user)
                LOGGER.info(f"🎲 为新用户 {tg} 创建抽奖记录")
                
            user.total_participations += 1
            user.updated_date = current_time
            
            session.commit()
            session.refresh(participant)
            
            LOGGER.info(f"🎲 用户 {tg}({nickname}) 成功参与抽奖轮次 {round_id}")
            return participant, "参与成功"
            
        except Exception as e:
            LOGGER.error(f"❌ 用户 {tg} 参与抽奖轮次 {round_id} 失败: {e}")
            session.rollback()
            return None, "系统错误"


def sql_get_lottery_participants(round_id: int):
    """获取抽奖参与者列表 - 增强错误处理和性能优化"""
    with Session() as session:
        try:
            participants = session.query(CodeLotteryParticipant).filter(
                CodeLotteryParticipant.round_id == round_id
            ).order_by(CodeLotteryParticipant.participation_date).all()
            
            # Refresh all participants to load attributes
            for participant in participants:
                session.refresh(participant)
                
            LOGGER.debug(f"🎲 获取抽奖轮次 {round_id} 的参与者列表: {len(participants)} 人")
            return participants
        except Exception as e:
            LOGGER.error(f"❌ 获取抽奖轮次 {round_id} 参与者列表失败: {e}")
            return []


def sql_complete_lottery_round(round_id: int, winners: list):
    """完成抽奖轮次并记录获奖者 - 增强事务处理和数据一致性"""
    with Session() as session:
        try:
            # 更新轮次状态
            round_obj = session.query(CodeLotteryRound).filter(
                CodeLotteryRound.id == round_id
            ).first()
            
            if not round_obj:
                LOGGER.error(f"❌ 尝试完成不存在的抽奖轮次: {round_id}")
                return False, "轮次不存在"
            
            if round_obj.status != 'active':
                LOGGER.warning(f"🎲 尝试完成非活跃状态的抽奖轮次: {round_id}, 状态: {round_obj.status}")
                return False, "轮次状态无效"
            
            current_time = datetime.datetime.now()
            round_obj.status = 'completed'
            round_obj.completed_date = current_time
            
            # 验证获奖者数量
            if len(winners) > round_obj.winner_count:
                LOGGER.warning(f"🎲 抽奖轮次 {round_id} 获奖者数量 {len(winners)} 超过设定的 {round_obj.winner_count}")
            
            # 记录获奖者
            winners_added = 0
            for winner_info in winners:
                try:
                    tg = winner_info['tg']
                    nickname = winner_info['nickname']
                    
                    # 验证获奖者确实参与了此轮抽奖
                    participant = session.query(CodeLotteryParticipant).filter(
                        CodeLotteryParticipant.round_id == round_id,
                        CodeLotteryParticipant.tg == tg
                    ).first()
                    
                    if not participant:
                        LOGGER.warning(f"🎲 获奖者 {tg} 未参与抽奖轮次 {round_id}")
                        continue
                    
                    # 获取用户总参与次数
                    user = session.query(CodeLotteryUser).filter(CodeLotteryUser.tg == tg).first()
                    if not user:
                        # 创建用户记录（理论上不应该发生）
                        user = CodeLotteryUser(tg=tg, total_participations=1)
                        session.add(user)
                        LOGGER.warning(f"🎲 为获奖者 {tg} 创建缺失的用户记录")
                    
                    total_participations = user.total_participations
                    
                    winner = CodeLotteryWinner(
                        round_id=round_id,
                        tg=tg,
                        nickname=nickname,
                        total_participations_at_win=total_participations,
                        win_date=current_time
                    )
                    session.add(winner)
                    
                    # 更新用户获奖次数
                    user.total_wins += 1
                    user.updated_date = current_time
                    winners_added += 1
                    
                    LOGGER.info(f"🎲 记录获奖者: {tg}({nickname}), 累计参与: {total_participations} 次")
                    
                except Exception as winner_error:
                    LOGGER.error(f"❌ 记录获奖者失败: {winner_error}")
                    continue
            
            session.commit()
            LOGGER.info(f"🎲 抽奖轮次 {round_id} 开奖完成，成功记录 {winners_added} 个获奖者")
            return True, f"开奖完成，{winners_added} 人获奖"
            
        except Exception as e:
            LOGGER.error(f"❌ 完成抽奖轮次 {round_id} 失败: {e}")
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
            if active_round:
                session.refresh(active_round)
            
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
            if participant:
                session.refresh(participant)
            return participant
        except Exception as e:
            LOGGER.error(f"检查用户参与状态失败: {e}")
            return None


def sql_get_expired_lottery_rounds():
    """获取已过期但状态仍为活跃的抽奖轮次 - 增强过期检测和日志记录"""
    with Session() as session:
        try:
            current_time = datetime.datetime.now()
            expired_rounds = session.query(CodeLotteryRound).filter(
                CodeLotteryRound.status == 'active',
                CodeLotteryRound.end_time <= current_time
            ).order_by(CodeLotteryRound.end_time).all()
            
            # Refresh all rounds to load attributes
            for round_obj in expired_rounds:
                session.refresh(round_obj)
                
            if expired_rounds:
                LOGGER.info(f"🎲 发现 {len(expired_rounds)} 个过期的活跃抽奖轮次")
                for round_obj in expired_rounds:
                    expired_minutes = int((current_time - round_obj.end_time).total_seconds() / 60)
                    LOGGER.debug(f"🎲 过期轮次: {round_obj.id} ({round_obj.lottery_name}), "
                               f"过期 {expired_minutes} 分钟")
            else:
                LOGGER.debug("🎲 没有发现过期的抽奖轮次")
                
            return expired_rounds
        except Exception as e:
            LOGGER.error(f"❌ 获取过期抽奖轮次失败: {e}")
            return []


def sql_cleanup_old_lottery_data(days_old: int = 30):
    """清理旧的抽奖数据 - 借鉴hunt系统的清理机制"""
    with Session() as session:
        try:
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_old)
            
            # 获取要清理的轮次
            old_rounds = session.query(CodeLotteryRound).filter(
                CodeLotteryRound.status.in_(['completed', 'cancelled']),
                CodeLotteryRound.created_date < cutoff_date
            ).all()
            
            if not old_rounds:
                LOGGER.debug(f"🎲 没有发现 {days_old} 天前的旧抽奖数据需要清理")
                return 0
            
            total_cleaned = 0
            for round_obj in old_rounds:
                round_id = round_obj.id
                
                # 删除获奖者记录
                winners_deleted = session.query(CodeLotteryWinner).filter(
                    CodeLotteryWinner.round_id == round_id
                ).delete()
                
                # 删除参与者记录
                participants_deleted = session.query(CodeLotteryParticipant).filter(
                    CodeLotteryParticipant.round_id == round_id
                ).delete()
                
                # 删除轮次记录
                session.delete(round_obj)
                total_cleaned += 1
                
                LOGGER.debug(f"🎲 清理轮次 {round_id}: {participants_deleted} 参与者, {winners_deleted} 获奖者")
            
            session.commit()
            LOGGER.info(f"🎲 成功清理 {total_cleaned} 个 {days_old} 天前的抽奖轮次")
            return total_cleaned
            
        except Exception as e:
            LOGGER.error(f"❌ 清理旧抽奖数据失败: {e}")
            session.rollback()
            return 0


def sql_get_codelottery_health_status():
    """获取抽奖系统健康状态 - 借鉴hunt系统的监控功能"""
    with Session() as session:
        try:
            current_time = datetime.datetime.now()
            
            # 基础统计
            total_users = session.query(func.count(CodeLotteryUser.id)).scalar() or 0
            total_rounds = session.query(func.count(CodeLotteryRound.id)).scalar() or 0
            active_rounds = session.query(func.count(CodeLotteryRound.id)).filter(
                CodeLotteryRound.status == 'active'
            ).scalar() or 0
            
            # 过期但仍活跃的轮次
            expired_active_rounds = session.query(func.count(CodeLotteryRound.id)).filter(
                CodeLotteryRound.status == 'active',
                CodeLotteryRound.end_time <= current_time
            ).scalar() or 0
            
            # 最近一周的活动
            week_ago = current_time - datetime.timedelta(days=7)
            recent_participations = session.query(func.count(CodeLotteryParticipant.id)).filter(
                CodeLotteryParticipant.participation_date >= week_ago
            ).scalar() or 0
            
            recent_rounds = session.query(func.count(CodeLotteryRound.id)).filter(
                CodeLotteryRound.created_date >= week_ago
            ).scalar() or 0
            
            health_status = {
                'total_users': total_users,
                'total_rounds': total_rounds,
                'active_rounds': active_rounds,
                'expired_active_rounds': expired_active_rounds,
                'recent_participations_7d': recent_participations,
                'recent_rounds_7d': recent_rounds,
                'health_score': 'healthy' if expired_active_rounds == 0 else 'warning',
                'last_check': current_time.isoformat()
            }
            
            LOGGER.debug(f"🎲 抽奖系统健康检查: {health_status}")
            return health_status
            
        except Exception as e:
            LOGGER.error(f"❌ 获取抽奖系统健康状态失败: {e}")
            return None


def sql_get_user_lottery_summary(tg: int):
    """获取用户抽奖总结 - 类似hunt系统的用户统计"""
    with Session() as session:
        try:
            # 用户基础信息
            user = session.query(CodeLotteryUser).filter(CodeLotteryUser.tg == tg).first()
            if not user:
                return None
                
            # 最近参与的轮次
            recent_participations = session.query(CodeLotteryParticipant).filter(
                CodeLotteryParticipant.tg == tg
            ).order_by(CodeLotteryParticipant.participation_date.desc()).limit(5).all()
            
            # 获奖记录
            wins = session.query(CodeLotteryWinner).filter(
                CodeLotteryWinner.tg == tg
            ).order_by(CodeLotteryWinner.win_date.desc()).all()
            
            # 胜率计算
            win_rate = (user.total_wins / user.total_participations * 100) if user.total_participations > 0 else 0
            
            summary = {
                'user_id': tg,
                'total_participations': user.total_participations,
                'total_wins': user.total_wins,
                'win_rate': round(win_rate, 2),
                'recent_participations': len(recent_participations),
                'recent_wins': len([w for w in wins if w.win_date >= datetime.datetime.now() - datetime.timedelta(days=30)]),
                'created_date': user.created_date,
                'last_activity': user.updated_date
            }
            
            return summary
            
        except Exception as e:
            LOGGER.error(f"❌ 获取用户 {tg} 抽奖总结失败: {e}")
            return None