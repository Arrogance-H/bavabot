"""
寻宝游戏数据库操作
"""
import datetime
from bot.sql_helper import Base, Session, engine
from sqlalchemy import Column, BigInteger, String, DateTime, Integer, Boolean, Text, and_
from sqlalchemy import func
from bot import LOGGER


class Hunt(Base):
    """
    寻宝游戏会话表
    """
    __tablename__ = 'hunt'
    id = Column(Integer, primary_key=True, autoincrement=True)
    tg = Column(BigInteger, nullable=False)  # 用户telegram id
    start_time = Column(DateTime, nullable=False)  # 游戏开始时间
    end_time = Column(DateTime, nullable=True)  # 游戏结束时间
    game_date = Column(String(10), nullable=False)  # 游戏日期 YYYY-MM-DD
    is_active = Column(Boolean, default=True)  # 游戏是否进行中
    fragments_found = Column(Integer, default=0)  # 找到的碎片数量
    coins_spent = Column(Integer, default=0)  # 消耗的金币数量
    last_hunt_time = Column(DateTime, nullable=True)  # 上次寻宝时间


class Fragment(Base):
    """
    宝物碎片表
    """
    __tablename__ = 'fragment'
    id = Column(Integer, primary_key=True, autoincrement=True)
    tg = Column(BigInteger, nullable=False)  # 用户telegram id
    fragment_id = Column(Integer, nullable=False)  # 碎片id (1-6)
    obtained_date = Column(String(10), nullable=False)  # 获得日期 YYYY-MM-DD
    obtained_time = Column(DateTime, nullable=False)  # 获得时间
    hunt_session_id = Column(Integer, nullable=False)  # 对应的寻宝会话id


class Treasure(Base):
    """
    宝物配置表
    """
    __tablename__ = 'treasure'
    id = Column(Integer, primary_key=True, autoincrement=True)
    treasure_name = Column(String(50), nullable=False)  # 宝物名称
    fragment_ids = Column(String(20), nullable=False)  # 需要的碎片id，逗号分隔
    description = Column(Text, nullable=True)  # 宝物描述


class DailyTreasure(Base):
    """
    每日宝物表
    """
    __tablename__ = 'daily_treasure'
    date = Column(String(10), primary_key=True)  # 日期 YYYY-MM-DD
    treasure_id = Column(Integer, nullable=False)  # 当日宝物id


# 创建表
Hunt.__table__.create(bind=engine, checkfirst=True)
Fragment.__table__.create(bind=engine, checkfirst=True)
Treasure.__table__.create(bind=engine, checkfirst=True)
DailyTreasure.__table__.create(bind=engine, checkfirst=True)


def init_treasures():
    """初始化宝物配置"""
    with Session() as session:
        try:
            # 检查是否已经初始化
            existing = session.query(Treasure).first()
            if existing:
                return
            
            # 添加默认宝物
            treasures = [
                Treasure(treasure_name="m", fragment_ids="1,2,3", description="神秘宝物m"),
                Treasure(treasure_name="l", fragment_ids="4,5,6", description="传说宝物l")
            ]
            
            for treasure in treasures:
                session.add(treasure)
            
            session.commit()
            LOGGER.info("宝物配置初始化完成")
        except Exception as e:
            session.rollback()
            LOGGER.error(f"初始化宝物配置失败: {e}")


def sql_start_hunt(tg: int) -> int:
    """开始寻宝游戏"""
    with Session() as session:
        try:
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            
            # 检查今日游戏次数
            today_games = session.query(Hunt).filter(
                and_(Hunt.tg == tg, Hunt.game_date == today)
            ).count()
            
            if today_games >= 5:
                return -1  # 超过每日限制
            
            # 检查是否有进行中的游戏
            active_hunt = session.query(Hunt).filter(
                and_(Hunt.tg == tg, Hunt.is_active == True)
            ).first()
            
            if active_hunt:
                return -2  # 已有进行中的游戏
            
            # 创建新游戏会话
            hunt = Hunt(
                tg=tg,
                start_time=datetime.datetime.now(),
                game_date=today,
                is_active=True
            )
            session.add(hunt)
            session.commit()
            
            return hunt.id
        except Exception as e:
            session.rollback()
            LOGGER.error(f"开始寻宝失败: {e}")
            return 0


def sql_end_hunt(hunt_id: int) -> bool:
    """结束寻宝游戏"""
    with Session() as session:
        try:
            hunt = session.query(Hunt).filter(Hunt.id == hunt_id).first()
            if hunt and hunt.is_active:
                hunt.end_time = datetime.datetime.now()
                hunt.is_active = False
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            LOGGER.error(f"结束寻宝失败: {e}")
            return False


def sql_get_active_hunt(tg: int):
    """获取用户当前进行中的寻宝游戏"""
    with Session() as session:
        try:
            hunt = session.query(Hunt).filter(
                and_(Hunt.tg == tg, Hunt.is_active == True)
            ).first()
            return hunt
        except Exception as e:
            LOGGER.error(f"获取活跃寻宝会话失败: {e}")
            return None


def sql_add_fragment(tg: int, hunt_session_id: int, fragment_id: int) -> bool:
    """添加碎片"""
    with Session() as session:
        try:
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            current_time = datetime.datetime.now()
            
            fragment = Fragment(
                tg=tg,
                fragment_id=fragment_id,
                obtained_date=today,
                obtained_time=current_time,
                hunt_session_id=hunt_session_id
            )
            session.add(fragment)
            
            # 更新hunt会话的碎片计数和最后寻宝时间
            hunt = session.query(Hunt).filter(Hunt.id == hunt_session_id).first()
            if hunt:
                hunt.fragments_found += 1
                hunt.coins_spent += 1
                hunt.last_hunt_time = current_time
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            LOGGER.error(f"添加碎片失败: {e}")
            return False


def sql_get_user_fragments(tg: int, today_only: bool = True):
    """获取用户碎片"""
    with Session() as session:
        try:
            query = session.query(Fragment).filter(Fragment.tg == tg)
            
            if today_only:
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                query = query.filter(Fragment.obtained_date == today)
            
            fragments = query.all()
            return fragments
        except Exception as e:
            LOGGER.error(f"获取用户碎片失败: {e}")
            return []


def sql_get_today_hunt_count(tg: int) -> int:
    """获取今日寻宝次数"""
    with Session() as session:
        try:
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            count = session.query(Hunt).filter(
                and_(Hunt.tg == tg, Hunt.game_date == today)
            ).count()
            return count
        except Exception as e:
            LOGGER.error(f"获取今日寻宝次数失败: {e}")
            return 0


def sql_get_daily_treasure(date: str = None):
    """获取每日宝物"""
    if not date:
        date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    with Session() as session:
        try:
            daily_treasure = session.query(DailyTreasure).filter(
                DailyTreasure.date == date
            ).first()
            
            if not daily_treasure:
                # 随机选择一个宝物作为今日宝物
                import random
                treasures = session.query(Treasure).all()
                if treasures:
                    selected_treasure = random.choice(treasures)
                    daily_treasure = DailyTreasure(
                        date=date,
                        treasure_id=selected_treasure.id
                    )
                    session.add(daily_treasure)
                    session.commit()
                    return selected_treasure
            else:
                treasure = session.query(Treasure).filter(
                    Treasure.id == daily_treasure.treasure_id
                ).first()
                return treasure
            
            return None
        except Exception as e:
            session.rollback()
            LOGGER.error(f"获取每日宝物失败: {e}")
            return None


def sql_check_treasure_synthesis(tg: int, treasure_id: int) -> bool:
    """检查是否可以合成宝物"""
    with Session() as session:
        try:
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            
            # 获取宝物所需碎片
            treasure = session.query(Treasure).filter(Treasure.id == treasure_id).first()
            if not treasure:
                return False
            
            required_fragments = [int(x) for x in treasure.fragment_ids.split(',')]
            
            # 检查用户是否拥有所需碎片
            user_fragments = session.query(Fragment).filter(
                and_(Fragment.tg == tg, Fragment.obtained_date == today)
            ).all()
            
            user_fragment_counts = {}
            for frag in user_fragments:
                user_fragment_counts[frag.fragment_id] = user_fragment_counts.get(frag.fragment_id, 0) + 1
            
            # 检查是否有足够的碎片
            for required_id in required_fragments:
                if user_fragment_counts.get(required_id, 0) < 1:
                    return False
            
            return True
        except Exception as e:
            LOGGER.error(f"检查宝物合成失败: {e}")
            return False


def sql_synthesize_treasure(tg: int, treasure_id: int) -> bool:
    """合成宝物"""
    with Session() as session:
        try:
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            
            # 获取宝物所需碎片
            treasure = session.query(Treasure).filter(Treasure.id == treasure_id).first()
            if not treasure:
                return False
            
            required_fragments = [int(x) for x in treasure.fragment_ids.split(',')]
            
            # 删除用户的对应碎片
            for required_id in required_fragments:
                fragment = session.query(Fragment).filter(
                    and_(Fragment.tg == tg, Fragment.fragment_id == required_id, Fragment.obtained_date == today)
                ).first()
                if fragment:
                    session.delete(fragment)
                else:
                    session.rollback()
                    return False
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            LOGGER.error(f"合成宝物失败: {e}")
            return False


def sql_cleanup_expired_fragments():
    """清理过期碎片"""
    with Session() as session:
        try:
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            deleted = session.query(Fragment).filter(Fragment.obtained_date != today).delete()
            session.commit()
            if deleted > 0:
                LOGGER.info(f"清理了 {deleted} 个过期碎片")
        except Exception as e:
            session.rollback()
            LOGGER.error(f"清理过期碎片失败: {e}")


# 初始化宝物配置
init_treasures()