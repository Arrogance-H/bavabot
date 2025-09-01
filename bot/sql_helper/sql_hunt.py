"""
车库游戏数据库操作
"""
import datetime
from bot.sql_helper import Base, Session, engine
from sqlalchemy import Column, BigInteger, String, DateTime, Integer, Boolean, Text, and_
from sqlalchemy import func
from bot import LOGGER, config


class Hunt(Base):
    """
    车库游戏会话表
    """
    __tablename__ = 'hunt'
    id = Column(Integer, primary_key=True, autoincrement=True)
    tg = Column(BigInteger, nullable=False)  # 用户telegram id
    start_time = Column(DateTime, nullable=False)  # 游戏开始时间
    end_time = Column(DateTime, nullable=True)  # 游戏结束时间
    game_date = Column(String(10), nullable=False)  # 游戏日期 YYYY-MM-DD
    is_active = Column(Boolean, default=True)  # 游戏是否进行中
    equipment_found = Column(Integer, default=0)  # 找到的装备数量
    coins_spent = Column(Integer, default=0)  # 消耗的金币数量
    last_hunt_time = Column(DateTime, nullable=True)  # 上次寻找时间
    hunt_actions = Column(Integer, default=0)  # 寻找装备的次数
    daily_car_info = Column(Text, nullable=True)  # 缓存的每日汽车信息


class Equipment(Base):
    """
    装备表
    """
    __tablename__ = 'equipment'
    id = Column(Integer, primary_key=True, autoincrement=True)
    tg = Column(BigInteger, nullable=False)  # 用户telegram id
    equipment_id = Column(Integer, nullable=False)  # 装备id
    obtained_date = Column(String(10), nullable=False)  # 获得日期 YYYY-MM-DD
    obtained_time = Column(DateTime, nullable=False)  # 获得时间
    hunt_session_id = Column(Integer, nullable=False)  # 对应的车库会话id


class Car(Base):
    """
    汽车配置表
    """
    __tablename__ = 'car'
    id = Column(Integer, primary_key=True, autoincrement=True)
    car_name = Column(String(50), nullable=False)  # 汽车名称
    equipment_ids = Column(String(200), nullable=False)  # 需要的装备id，逗号分隔
    description = Column(Text, nullable=True)  # 汽车描述


class EquipmentDefinition(Base):
    """
    装备定义表
    """
    __tablename__ = 'equipment_definition'
    equipment_id = Column(Integer, primary_key=True)  # 装备id
    equipment_name = Column(String(100), nullable=False)  # 装备名称
    description = Column(Text, nullable=True)  # 装备描述
    category = Column(String(20), nullable=False)  # 装备类别 (blue/green/gold/purple)
    rarity_weight = Column(Integer, nullable=False, default=1)  # 稀有度权重，数值越大越容易获得


class AssemblyReward(Base):
    """
    组装奖励表
    """
    __tablename__ = 'assembly_reward'
    id = Column(Integer, primary_key=True, autoincrement=True)
    tg = Column(BigInteger, nullable=False)  # 用户telegram id
    car_id = Column(Integer, nullable=False)  # 汽车id
    car_name = Column(String(50), nullable=False)  # 汽车名称
    reward_type = Column(String(20), nullable=False)  # 奖励类型 (coins/title/badge)
    reward_value = Column(String(100), nullable=False)  # 奖励数值/内容
    reward_description = Column(Text, nullable=True)  # 奖励描述
    obtained_date = Column(String(10), nullable=False)  # 获得日期 YYYY-MM-DD
    obtained_time = Column(DateTime, nullable=False)  # 获得时间


class RewardConfig(Base):
    """
    奖励配置表
    """
    __tablename__ = 'reward_config'
    id = Column(Integer, primary_key=True, autoincrement=True)
    car_id = Column(Integer, nullable=False, unique=True)  # 汽车id
    reward_type = Column(String(20), nullable=False)  # 奖励类型 (coins/title/badge)
    reward_value = Column(String(100), nullable=False)  # 奖励数值/内容
    reward_description = Column(Text, nullable=True)  # 奖励描述
    is_active = Column(Boolean, default=True)  # 是否激活


class DailyCar(Base):
    """
    每日汽车表
    """
    __tablename__ = 'daily_car'
    date = Column(String(10), primary_key=True)  # 日期 YYYY-MM-DD
    car_id = Column(Integer, nullable=False)  # 当日汽车id


class RewardButton(Base):
    """
    自定义奖励按钮配置表
    """
    __tablename__ = 'reward_button'
    id = Column(Integer, primary_key=True, autoincrement=True)
    car_id = Column(Integer, nullable=False)  # 汽车id
    button_text = Column(String(100), nullable=False)  # 按钮文字
    button_url = Column(String(500), nullable=False)  # 跳转URL
    is_active = Column(Boolean, default=True)  # 是否激活


# 为了向后兼容，保留旧表结构但标记为废弃
Fragment = Equipment  # 别名，向后兼容
Treasure = Car  # 别名，向后兼容  
FragmentDefinition = EquipmentDefinition  # 别名，向后兼容
DailyTreasure = DailyCar  # 别名，向后兼容


# 创建表
Hunt.__table__.create(bind=engine, checkfirst=True)
Equipment.__table__.create(bind=engine, checkfirst=True)
EquipmentDefinition.__table__.create(bind=engine, checkfirst=True)
Car.__table__.create(bind=engine, checkfirst=True)
DailyCar.__table__.create(bind=engine, checkfirst=True)
AssemblyReward.__table__.create(bind=engine, checkfirst=True)
RewardConfig.__table__.create(bind=engine, checkfirst=True)
RewardButton.__table__.create(bind=engine, checkfirst=True)


def init_cars_and_equipment():
    """初始化汽车配置和装备定义"""
    with Session() as session:
        try:
            # 检查是否已经初始化
            existing = session.query(Car).first()
            if existing:
                return
            
            # 首先添加装备定义
            equipment_definitions = [
                # 紫色装备 (极稀有，权重极低) - 专属车漆
                EquipmentDefinition(equipment_id=1, equipment_name="赞德福特蓝车漆", description="赞德福特蓝M2专属车漆", category="purple", rarity_weight=1),
                EquipmentDefinition(equipment_id=2, equipment_name="曼岛绿车漆", description="曼岛绿M3专属车漆", category="purple", rarity_weight=1),
                EquipmentDefinition(equipment_id=3, equipment_name="圣保罗黄车漆", description="圣保罗黄M4专属车漆", category="purple", rarity_weight=1),
                EquipmentDefinition(equipment_id=4, equipment_name="风暴灰车漆", description="风暴灰M5专属车漆", category="purple", rarity_weight=1),
                
                # 金色装备 (高级组件)
                EquipmentDefinition(equipment_id=5, equipment_name="S58发动机", description="高性能S58双涡轮增压发动机", category="gold", rarity_weight=3),
                EquipmentDefinition(equipment_id=6, equipment_name="赤金色轮毂", description="限量版赤金色轮毂", category="gold", rarity_weight=3),
                EquipmentDefinition(equipment_id=7, equipment_name="xDrive智能全轮驱动系统", description="BMW xDrive智能全轮驱动系统", category="gold", rarity_weight=3),
                EquipmentDefinition(equipment_id=8, equipment_name="碳纤维赛道桶椅", description="轻量化碳纤维赛道桶椅", category="gold", rarity_weight=3),
                EquipmentDefinition(equipment_id=9, equipment_name="主动M差速器", description="M主动差速器", category="gold", rarity_weight=3),
                EquipmentDefinition(equipment_id=10, equipment_name="V8双涡轮增压发动机", description="强劲的V8双涡轮增压发动机", category="gold", rarity_weight=3),
                EquipmentDefinition(equipment_id=11, equipment_name="自适应M运动悬架", description="可调节自适应M运动悬架", category="gold", rarity_weight=3),
                EquipmentDefinition(equipment_id=12, equipment_name="碳陶瓷刹车系统", description="高性能碳陶瓷刹车系统", category="gold", rarity_weight=3),
                EquipmentDefinition(equipment_id=13, equipment_name="M精英驾驶模式", description="M精英驾驶模式系统", category="gold", rarity_weight=3),
                EquipmentDefinition(equipment_id=14, equipment_name="整体主动转向系统", description="BMW整体主动转向系统", category="gold", rarity_weight=3),
                
                # 绿色装备 (车漆变体)
                EquipmentDefinition(equipment_id=15, equipment_name="磨砂纯灰车漆", description="高档磨砂纯灰车漆", category="green", rarity_weight=6),
                EquipmentDefinition(equipment_id=16, equipment_name="布鲁克林灰车漆", description="经典布鲁克林灰车漆", category="green", rarity_weight=6),
                EquipmentDefinition(equipment_id=17, equipment_name="多伦多红车漆", description="亮丽多伦多红车漆", category="green", rarity_weight=6),
                EquipmentDefinition(equipment_id=18, equipment_name="海滨湾蓝车漆", description="深邃海滨湾蓝车漆", category="green", rarity_weight=6),
                
                # 蓝色装备 (常见物品)
                EquipmentDefinition(equipment_id=19, equipment_name="98#汽油", description="高品质98号汽油", category="blue", rarity_weight=10),
                EquipmentDefinition(equipment_id=20, equipment_name="玻璃水", description="汽车玻璃清洗液", category="blue", rarity_weight=10),
                EquipmentDefinition(equipment_id=21, equipment_name="车钥匙", description="汽车遥控钥匙", category="blue", rarity_weight=10),
                EquipmentDefinition(equipment_id=22, equipment_name="漏气的轮胎", description="需要修理的轮胎", category="blue", rarity_weight=10),
                EquipmentDefinition(equipment_id=23, equipment_name="空气", description="轮胎充气用空气", category="blue", rarity_weight=10),
                EquipmentDefinition(equipment_id=24, equipment_name="空调滤芯", description="汽车空调滤芯", category="blue", rarity_weight=10),
                EquipmentDefinition(equipment_id=25, equipment_name="刹车盘", description="汽车刹车盘", category="blue", rarity_weight=10),
            ]
            
            for equipment_def in equipment_definitions:
                session.add(equipment_def)
            
            # 然后添加汽车配置
            cars = [
                Car(car_name="赞德福特蓝M2", equipment_ids="5,12,6,15,1", description="BMW M2 Competition 赞德福特蓝限量版"),
                Car(car_name="曼岛绿M3", equipment_ids="5,7,8,2,16", description="BMW M3 Competition 曼岛绿限量版"),
                Car(car_name="圣保罗黄M4", equipment_ids="5,9,13,3,17", description="BMW M4 Competition 圣保罗黄限量版"),
                Car(car_name="风暴灰M5", equipment_ids="10,11,14,4,18", description="BMW M5 Competition 风暴灰限量版")
            ]
            
            for car in cars:
                session.add(car)
            
            # 添加更新的奖励配置
            reward_configs = [
                RewardConfig(car_id=1, reward_type="coins", reward_value="100", reward_description="组装赞德福特蓝M2获得100金币奖励"),
                RewardConfig(car_id=2, reward_type="coins", reward_value="1916", reward_description="组装曼岛绿M3获得1916金币奖励"),
                RewardConfig(car_id=3, reward_type="code", reward_value="1", reward_description="组装圣保罗黄M4获得1个注册码"),
                RewardConfig(car_id=4, reward_type="white", reward_value="1", reward_description="组装风暴灰M5获得1个白名单"),
            ]
            
            for reward_config in reward_configs:
                session.add(reward_config)
            
            session.commit()
        except:
            pass


def add_car_with_equipment(car_name: str, equipment_ids: str, description: str = None, equipment_definitions: list = None):
    """添加汽车并确保相应的装备定义存在"""
    with Session() as session:
        try:
            # 解析需要的装备ID
            required_equipment_ids = [int(x.strip()) for x in equipment_ids.split(',')]
            
            # 确保所有需要的装备定义都存在
            for equipment_id in required_equipment_ids:
                existing_equipment = session.query(EquipmentDefinition).filter(
                    EquipmentDefinition.equipment_id == equipment_id
                ).first()
                
                if not existing_equipment:
                    # 如果提供了装备定义，使用提供的；否则创建默认的
                    if equipment_definitions:
                        equipment_def = next((e for e in equipment_definitions if e['id'] == equipment_id), None)
                        if equipment_def:
                            new_equipment = EquipmentDefinition(
                                equipment_id=equipment_id,
                                equipment_name=equipment_def['name'],
                                description=equipment_def.get('description', f"装备 {equipment_id}"),
                                category=equipment_def.get('category', 'blue'),
                                rarity_weight=equipment_def.get('rarity_weight', 5)
                            )
                        else:
                            new_equipment = EquipmentDefinition(
                                equipment_id=equipment_id,
                                equipment_name=f"装备 {equipment_id}",
                                description=f"装备 {equipment_id} 的描述",
                                category='blue',
                                rarity_weight=5
                            )
                    else:
                        new_equipment = EquipmentDefinition(
                            equipment_id=equipment_id,
                            equipment_name=f"装备 {equipment_id}",
                            description=f"装备 {equipment_id} 的描述",
                            category='blue',
                            rarity_weight=5
                        )
                    
                    session.add(new_equipment)
            
            # 添加汽车
            car = Car(
                car_name=car_name,
                equipment_ids=equipment_ids,
                description=description or f"汽车 {car_name}"
            )
            session.add(car)
            
            session.commit()
            return True
        except:
            return False


def sql_check_and_fix_hunt_table():
    """检查并修复hunt表结构"""
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        
        # 检查hunt表是否存在
        if 'hunt' not in inspector.get_table_names():
            LOGGER.error("Hunt table does not exist")
            return False
            
        # 检查必要的列
        columns = inspector.get_columns('hunt')
        column_names = [col['name'] for col in columns]
        
        missing_columns = []
        if 'hunt_actions' not in column_names:
            missing_columns.append('hunt_actions')
        if 'daily_car_info' not in column_names:
            missing_columns.append('daily_car_info')
            
        if missing_columns:
            LOGGER.warning(f"Hunt table missing columns: {missing_columns}")
            # 尝试添加缺失的列
            with engine.connect() as conn:
                for column in missing_columns:
                    try:
                        if column == 'hunt_actions':
                            sql = text("ALTER TABLE hunt ADD COLUMN hunt_actions INT DEFAULT 0")
                        elif column == 'daily_car_info':
                            sql = text("ALTER TABLE hunt ADD COLUMN daily_car_info TEXT NULL")
                        conn.execute(sql)
                        conn.commit()
                        LOGGER.info(f"Successfully added column: {column}")
                    except Exception as e:
                        LOGGER.error(f"Failed to add column {column}: {e}")
                        return False
            return True
        
        return True  # 所有列都存在
    except Exception as e:
        LOGGER.error(f"Error checking hunt table structure: {e}")
        return False


def sql_start_hunt(tg: int) -> int:
    """开始车库游戏"""
    with Session() as session:
        try:
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            
            # 检查今日游戏次数
            today_games = session.query(Hunt).filter(
                and_(Hunt.tg == tg, Hunt.game_date == today)
            ).count()
            
            if today_games >= config.hunt_daily_limit:
                return -1  # 超过每日限制
            
            # 检查活跃游戏
            active_hunt = session.query(Hunt).filter(
                and_(Hunt.tg == tg, Hunt.is_active == True)
            ).first()
            
            if active_hunt:
                # 检查是否超时，如果超时则自动结束
                current_time = datetime.datetime.now()
                if (current_time - active_hunt.start_time).total_seconds() > 1800:  # 30分钟
                    active_hunt.end_time = current_time
                    active_hunt.is_active = False
                    session.commit()
                else:
                    return -2  # 已有进行中的游戏
            
            # 获取并缓存今日汽车信息
            daily_car = sql_get_daily_car()
            daily_car_info = None
            if daily_car:
                import json
                daily_car_info = json.dumps({
                    'id': daily_car.id,
                    'car_name': daily_car.car_name,
                    'equipment_ids': daily_car.equipment_ids,
                    'description': daily_car.description
                })
            
            # 创建新游戏会话
            hunt = Hunt(
                tg=tg,
                start_time=datetime.datetime.now(),
                game_date=today,
                is_active=True,
                daily_car_info=daily_car_info
            )
            session.add(hunt)
            session.commit()
            
            return hunt.id
        except Exception as e:
            LOGGER.error(f"Error starting hunt for user {tg}: {e}")
            # 检查是否是数据库结构问题
            if "Unknown column" in str(e) or "doesn't exist" in str(e):
                return -3  # 数据库结构问题
            return 0  # 其他未知错误


def sql_get_equipment_definition(equipment_id: int):
    """获取装备定义"""
    with Session() as session:
        try:
            equipment_def = session.query(EquipmentDefinition).filter(
                EquipmentDefinition.equipment_id == equipment_id
            ).first()
            return equipment_def
        except:
            return None


def sql_get_all_equipment_definitions():
    """获取所有装备定义"""
    with Session() as session:
        try:
            equipment_defs = session.query(EquipmentDefinition).order_by(EquipmentDefinition.equipment_id).all()
            return equipment_defs
        except:
            return []


def sql_get_equipment_by_category(category: str):
    """根据类别获取装备定义"""
    with Session() as session:
        try:
            equipment_defs = session.query(EquipmentDefinition).filter(
                EquipmentDefinition.category == category
            ).all()
            return equipment_defs
        except:
            return []


def sql_count_user_equipment(tg: int, today_only: bool = True) -> int:
    """统计用户装备数量"""
    with Session() as session:
        try:
            query = session.query(Equipment).filter(Equipment.tg == tg)
            
            if today_only:
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                query = query.filter(Equipment.obtained_date == today)
            
            count = query.count()
            return count
        except:
            return 0


def sql_end_hunt(hunt_id: int) -> bool:
    """结束车库游戏"""
    with Session() as session:
        try:
            hunt = session.query(Hunt).filter(Hunt.id == hunt_id).first()
            if hunt and hunt.is_active:
                hunt.end_time = datetime.datetime.now()
                hunt.is_active = False
                session.commit()
                return True
            return False
        except:
            return False


def sql_get_active_hunt(tg: int):
    """获取用户当前进行中的车库游戏"""
    with Session() as session:
        try:
            hunt = session.query(Hunt).filter(
                and_(Hunt.tg == tg, Hunt.is_active == True)
            ).first()
            return hunt
        except:
            return None


def sql_get_hunt_by_id(hunt_id: int):
    """根据hunt_id获取游戏会话（任何用户）"""
    with Session() as session:
        try:
            hunt = session.query(Hunt).filter(
                and_(Hunt.id == hunt_id, Hunt.is_active == True)
            ).first()
            return hunt
        except:
            return None


def sql_get_cached_daily_car(hunt):
    """获取游戏会话中缓存的每日汽车信息"""
    if not hunt or not hunt.daily_car_info:
        return None
    
    try:
        import json
        car_data = json.loads(hunt.daily_car_info)
        
        # 创建一个简单的对象来模拟Car对象
        class CachedCar:
            def __init__(self, data):
                self.id = data['id']
                self.car_name = data['car_name']
                self.equipment_ids = data['equipment_ids']
                self.description = data['description']
        
        return CachedCar(car_data)
    except:
        return None


def sql_add_equipment(tg: int, hunt_session_id: int, equipment_id: int) -> bool:
    """添加装备 - 检查背包容量限制"""
    with Session() as session:
        try:
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            current_time = datetime.datetime.now()
            
            # 检查用户今日装备数量是否已达到150个上限
            current_count = sql_count_user_equipment(tg, today_only=True)
            if current_count >= 150:
                return False  # 背包已满
            
            equipment = Equipment(
                tg=tg,
                equipment_id=equipment_id,
                obtained_date=today,
                obtained_time=current_time,
                hunt_session_id=hunt_session_id
            )
            session.add(equipment)
            
            # 更新hunt会话的装备计数和最后寻找时间
            hunt = session.query(Hunt).filter(Hunt.id == hunt_session_id).first()
            if hunt:
                hunt.equipment_found += 1
                hunt.coins_spent += 1
                hunt.last_hunt_time = current_time
            
            session.commit()
            return True
        except:
            return False


def sql_get_user_equipment(tg: int, today_only: bool = True):
    """获取用户装备"""
    with Session() as session:
        try:
            query = session.query(Equipment).filter(Equipment.tg == tg)
            
            if today_only:
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                query = query.filter(Equipment.obtained_date == today)
            
            equipment_list = query.all()
            return equipment_list
        except:
            return []


def sql_get_today_hunt_count(tg: int) -> int:
    """获取今日车库游戏次数"""
    with Session() as session:
        try:
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            count = session.query(Hunt).filter(
                and_(Hunt.tg == tg, Hunt.game_date == today)
            ).count()
            return count
        except:
            return 0


def sql_get_total_hunt_count(tg: int) -> int:
    """获取用户总寻宝次数"""
    with Session() as session:
        try:
            count = session.query(Hunt).filter(Hunt.tg == tg).count()
            return count
        except:
            return 0


def sql_get_total_hunt_actions(tg: int) -> int:
    """获取用户总寻找装备次数(实际操作次数)"""
    with Session() as session:
        try:
            # 汇总所有hunt会话的hunt_actions
            result = session.query(func.sum(Hunt.hunt_actions)).filter(Hunt.tg == tg).scalar()
            return result if result else 0
        except:
            return 0


def sql_get_daily_car(date: str = None):
    """获取每日汽车"""
    if not date:
        date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    with Session() as session:
        try:
            daily_car = session.query(DailyCar).filter(
                DailyCar.date == date
            ).first()
            
            if not daily_car:
                # 确保每日汽车的多样性
                import random
                cars = session.query(Car).all()
                if cars:
                    # 获取前一天的汽车ID，避免连续重复
                    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                    yesterday_car = session.query(DailyCar).filter(
                        DailyCar.date == yesterday
                    ).first()
                    
                    yesterday_car_id = yesterday_car.car_id if yesterday_car else None
                    
                    # 如果有多辆车，避免选择昨天的车
                    available_cars = cars
                    if len(cars) > 1 and yesterday_car_id:
                        available_cars = [car for car in cars if car.id != yesterday_car_id]
                    
                    # 使用基于日期的种子以确保同一天相同结果，但不同天不同结果
                    import hashlib
                    date_seed = int(hashlib.md5(date.encode()).hexdigest()[:8], 16)
                    random.seed(date_seed)
                    
                    selected_car = random.choice(available_cars)
                    daily_car = DailyCar(
                        date=date,
                        car_id=selected_car.id
                    )
                    session.add(daily_car)
                    session.commit()
                    return selected_car
                else:
                    return None
            else:
                car = session.query(Car).filter(
                    Car.id == daily_car.car_id
                ).first()
                return car
        except:
            return None


def sql_check_car_assembly(tg: int, car_id: int) -> bool:
    """检查是否可以组装汽车"""
    with Session() as session:
        try:
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            
            # 获取汽车所需装备
            car = session.query(Car).filter(Car.id == car_id).first()
            if not car:
                return False
            
            required_equipment = [int(x.strip()) for x in car.equipment_ids.split(',')]
            
            # 检查用户是否拥有所需装备
            user_equipment = session.query(Equipment).filter(
                and_(Equipment.tg == tg, Equipment.obtained_date == today)
            ).all()
            
            user_equipment_counts = {}
            for equip in user_equipment:
                user_equipment_counts[equip.equipment_id] = user_equipment_counts.get(equip.equipment_id, 0) + 1
            
            # 检查是否有足够的装备 - 每种装备至少需要1个
            for required_id in required_equipment:
                have_count = user_equipment_counts.get(required_id, 0)
                if have_count < 1:
                    return False
            
            return True
        except:
            return False


def sql_assemble_car(tg: int, car_id: int) -> dict:
    """组装汽车并发放奖励"""
    with Session() as session:
        try:
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            
            # 获取汽车所需装备
            car = session.query(Car).filter(Car.id == car_id).first()
            if not car:
                return {"success": False, "message": "汽车不存在"}
            
            required_equipment = [int(x.strip()) for x in car.equipment_ids.split(',')]
            
            # 检查用户是否有足够的装备
            user_equipment = session.query(Equipment).filter(
                and_(Equipment.tg == tg, Equipment.obtained_date == today)
            ).all()
            
            user_equipment_counts = {}
            user_equipment_by_id = {}
            for equip in user_equipment:
                if equip.equipment_id not in user_equipment_by_id:
                    user_equipment_by_id[equip.equipment_id] = []
                user_equipment_by_id[equip.equipment_id].append(equip)
                user_equipment_counts[equip.equipment_id] = user_equipment_counts.get(equip.equipment_id, 0) + 1
            
            # 检查是否有足够装备
            for required_id in required_equipment:
                have_count = user_equipment_counts.get(required_id, 0)
                if have_count < 1:
                    return {"success": False, "message": f"装备不足：缺少装备 {required_id}"}
            
            # 删除用户的对应装备
            for required_id in required_equipment:
                if required_id in user_equipment_by_id and user_equipment_by_id[required_id]:
                    equipment_to_remove = user_equipment_by_id[required_id][0]
                    session.delete(equipment_to_remove)
                else:
                    return {"success": False, "message": f"装备不足：无法找到装备 {required_id}"}
            
            session.commit()
            
            # 发放奖励
            reward_result = sql_give_assembly_reward(tg, car_id)
            
            return {
                "success": True,
                "message": "组装成功",
                "car_name": car.car_name,
                "description": car.description,
                "reward": reward_result
            }
        except:
            return {"success": False, "message": "组装失败"}


# 向后兼容的组装函数
def sql_assemble_car_legacy(tg: int, car_id: int) -> bool:
    """向后兼容的组装汽车函数"""
    result = sql_assemble_car(tg, car_id)
    return result["success"]


def sql_cleanup_expired_equipment():
    """清理过期装备"""
    with Session() as session:
        try:
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            deleted = session.query(Equipment).filter(Equipment.obtained_date != today).delete()
            session.commit()
        except:
            pass


def sql_clear_user_equipment(tg: int, today_only: bool = True) -> bool:
    """清空用户的所有装备 - 用于完成寻宝后重置"""
    with Session() as session:
        try:
            query = session.query(Equipment).filter(Equipment.tg == tg)
            
            if today_only:
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                query = query.filter(Equipment.obtained_date == today)
            
            deleted_count = query.delete()
            session.commit()
            return True
        except Exception as e:
            LOGGER.error(f"清空用户装备失败: {e}")
            return False


def sql_cleanup_timed_out_hunts():
    """清理超时的车库游戏"""
    with Session() as session:
        try:
            current_time = datetime.datetime.now()
            timeout_threshold = current_time - datetime.timedelta(seconds=1800)  # 30分钟前
            
            # 查找超时的活跃游戏
            timed_out_hunts = session.query(Hunt).filter(
                and_(Hunt.is_active == True, Hunt.start_time < timeout_threshold)
            ).all()
            
            for hunt in timed_out_hunts:
                hunt.end_time = current_time
                hunt.is_active = False
            
            if timed_out_hunts:
                session.commit()
        except:
            pass


def sql_update_hunt_stats(hunt_id: int, last_hunt_time: datetime.datetime) -> bool:
    """更新车库游戏统计信息"""
    with Session() as session:
        try:
            hunt = session.query(Hunt).filter(Hunt.id == hunt_id).first()
            if hunt:
                hunt.last_hunt_time = last_hunt_time
                hunt.equipment_found = (hunt.equipment_found or 0) + 1
                hunt.hunt_actions = (hunt.hunt_actions or 0) + 1  # 增加寻找次数
                session.commit()
                return True
            return False
        except:
            return False


def sql_update_bulk_hunt_stats(hunt_id: int, last_hunt_time: datetime.datetime, action_count: int = 10) -> bool:
    """更新批量车库游戏统计信息"""
    with Session() as session:
        try:
            hunt = session.query(Hunt).filter(Hunt.id == hunt_id).first()
            if hunt:
                hunt.last_hunt_time = last_hunt_time
                hunt.hunt_actions = (hunt.hunt_actions or 0) + action_count  # 增加批量寻找次数
                hunt.coins_spent = (hunt.coins_spent or 0) + action_count  # 增加金币消耗记录
                session.commit()
                return True
            return False
        except:
            return False


def sql_cleanup_idle_hunts():
    """清理超过5分钟无活动的游戏会话"""
    with Session() as session:
        try:
            current_time = datetime.datetime.now()
            idle_threshold = current_time - datetime.timedelta(minutes=5)  # 5分钟前
            
            # 查找超过5分钟无活动的活跃游戏
            idle_hunts = session.query(Hunt).filter(
                and_(
                    Hunt.is_active == True, 
                    Hunt.last_hunt_time < idle_threshold,
                    Hunt.last_hunt_time.isnot(None)
                )
            ).all()
            
            for hunt in idle_hunts:
                hunt.end_time = current_time
                hunt.is_active = False
            
            if idle_hunts:
                session.commit()
        except:
            pass


def sql_get_reward_button(car_id: int):
    """获取汽车的自定义奖励按钮配置"""
    with Session() as session:
        try:
            button_config = session.query(RewardButton).filter(
                and_(RewardButton.car_id == car_id, RewardButton.is_active == True)
            ).first()
            return button_config
        except:
            return None


def sql_set_reward_button(car_id: int, button_text: str, button_url: str) -> bool:
    """设置汽车的自定义奖励按钮"""
    with Session() as session:
        try:
            # 查找现有配置
            existing_button = session.query(RewardButton).filter(RewardButton.car_id == car_id).first()
            
            if existing_button:
                # 更新现有配置
                existing_button.button_text = button_text
                existing_button.button_url = button_url
                existing_button.is_active = True
            else:
                # 创建新配置
                new_button = RewardButton(
                    car_id=car_id,
                    button_text=button_text,
                    button_url=button_url,
                    is_active=True
                )
                session.add(new_button)
            
            session.commit()
            return True
        except:
            return False


# 概率配置常量 - 修改概率时只需更改这里
PROBABILITY_THRESHOLDS = {
    'M5_PURPLE': 0.02,    # M5风暴灰车漆: 0.02%
    'M4_PURPLE': 0.25,    # M4圣保罗黄车漆: 0.23% (0.02-0.25)
    'M3_PURPLE': 1.55,    # M3曼岛绿车漆: 1.3% (0.25-1.55)
    'M2_PURPLE': 3.9,     # M2赞德福特蓝车漆: 2.35% (1.55-3.9)
    'GOLD': 8.91,         # 金色装备: 5.01% (3.9-8.91)
    'GREEN': 15.92,       # 绿色装备: 7.01% (8.91-15.92)
    # 蓝色装备: 84.08% (15.92-100)
}

def sql_random_equipment_by_rarity():
    """根据稀有度权重随机选择装备"""
    with Session() as session:
        try:
            import random
            
            # 优化概率分布，按从高到低排序: 蓝色 > 绿色 > 金色 > 紫色
            rand_value = random.random() * 100  # 0-100的随机数
            
            # 紫色装备个别概率判断 
            if rand_value < PROBABILITY_THRESHOLDS['M5_PURPLE']:  # M5紫色装备
                return 4  
            elif rand_value < PROBABILITY_THRESHOLDS['M4_PURPLE']:  # M4紫色装备
               return 3  
            elif rand_value < PROBABILITY_THRESHOLDS['M3_PURPLE']:  # M3紫色装备
               return 2  
            elif rand_value < PROBABILITY_THRESHOLDS['M2_PURPLE']:  # M2紫色装备
                return 1  
            elif rand_value < PROBABILITY_THRESHOLDS['GOLD']:  # 概率获得金色装备
                category = 'gold'
            elif rand_value < PROBABILITY_THRESHOLDS['GREEN']:  # 概率获得绿色装备
                category = 'green'
            else:  # 概率获得蓝色装备
                category = 'blue'
            
            # 从选定类别中随机选择装备
            equipment_defs = session.query(EquipmentDefinition).filter(
                EquipmentDefinition.category == category
            ).all()
            
            if equipment_defs:
                selected_equipment = random.choice(equipment_defs)
                return selected_equipment.equipment_id
            
            # 如果选定类别没有装备，fallback到蓝色装备
            blue_equipment = session.query(EquipmentDefinition).filter(
                EquipmentDefinition.category == 'blue'
            ).all()
            
            if blue_equipment:
                selected_equipment = random.choice(blue_equipment)
                return selected_equipment.equipment_id
            
            return None
        except:
            return None


def sql_discard_equipment(tg: int, equipment_id: int, today_only: bool = True) -> bool:
    """丢弃装备"""
    with Session() as session:
        try:
            query = session.query(Equipment).filter(
                and_(Equipment.tg == tg, Equipment.equipment_id == equipment_id)
            )
            
            if today_only:
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                query = query.filter(Equipment.obtained_date == today)
            
            equipment = query.first()
            if equipment:
                session.delete(equipment)
                session.commit()
                return True
            return False
        except:
            return False


def sql_get_reward_config(car_id: int):
    """获取汽车的奖励配置"""
    with Session() as session:
        try:
            reward_config = session.query(RewardConfig).filter(
                and_(RewardConfig.car_id == car_id, RewardConfig.is_active == True)
            ).first()
            return reward_config
        except:
            return None


def sql_give_assembly_reward(tg: int, car_id: int) -> dict:
    """给用户发放组装奖励"""
    with Session() as session:
        try:
            # 获取奖励配置
            reward_config = sql_get_reward_config(car_id)
            if not reward_config:
                return {"success": False, "message": "未找到奖励配置"}
            
            # 获取汽车信息
            car = session.query(Car).filter(Car.id == car_id).first()
            if not car:
                return {"success": False, "message": "汽车不存在"}
            
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            current_time = datetime.datetime.now()
            
            # 检查是否已经获得过奖励
            existing_reward = session.query(AssemblyReward).filter(
                and_(
                    AssemblyReward.tg == tg,
                    AssemblyReward.car_id == car_id,
                    AssemblyReward.obtained_date == today
                )
            ).first()
            
            if existing_reward:
                return {"success": False, "message": "今日已获得此汽车的奖励"}
            
            # 处理不同类型的奖励
            if reward_config.reward_type == "coins":
                # 金币奖励 - 直接给用户增加金币
                from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby
                user = sql_get_emby(tg)
                if user:
                    coin_amount = int(reward_config.reward_value)
                    if sql_update_emby(Emby.tg == tg, iv=user.iv + coin_amount):
                        # 记录奖励
                        reward_record = AssemblyReward(
                            tg=tg,
                            car_id=car_id,
                            car_name=car.car_name,
                            reward_type=reward_config.reward_type,
                            reward_value=reward_config.reward_value,
                            reward_description=reward_config.reward_description,
                            obtained_date=today,
                            obtained_time=current_time
                        )
                        session.add(reward_record)
                        session.commit()
                        
                        return {
                            "success": True,
                            "reward_type": "coins",
                            "reward_value": coin_amount,
                            "description": reward_config.reward_description,
                            "message": f"已自动添加{coin_amount}金币到您的账户！"
                        }
                    else:
                        return {"success": False, "message": "发放金币奖励失败"}
                else:
                    return {"success": False, "message": "用户不存在"}
            
            # 注册码奖励
            elif reward_config.reward_type == "code":
                reward_record = AssemblyReward(
                    tg=tg,
                    car_id=car_id,
                    car_name=car.car_name,
                    reward_type=reward_config.reward_type,
                    reward_value=reward_config.reward_value,
                    reward_description=reward_config.reward_description,
                    obtained_date=today,
                    obtained_time=current_time
                )
                session.add(reward_record)
                session.commit()
                
                return {
                    "success": True,
                    "reward_type": "code",
                    "reward_value": reward_config.reward_value,
                    "description": reward_config.reward_description,
                    "message": f"恭喜获得{reward_config.reward_value}个注册码！请联系 @MEBimmerSupportBot 领取"
                }
            
            # 白名单奖励
            elif reward_config.reward_type == "white":
                reward_record = AssemblyReward(
                    tg=tg,
                    car_id=car_id,
                    car_name=car.car_name,
                    reward_type=reward_config.reward_type,
                    reward_value=reward_config.reward_value,
                    reward_description=reward_config.reward_description,
                    obtained_date=today,
                    obtained_time=current_time
                )
                session.add(reward_record)
                session.commit()
                
                return {
                    "success": True,
                    "reward_type": "white",
                    "reward_value": reward_config.reward_value,
                    "description": reward_config.reward_description,
                    "message": f"恭喜获得{reward_config.reward_value}个白名单！请联系 @MEBimmerSupportBot 领取"
                }
            
            return {"success": False, "message": "未知的奖励类型"}
            
        except:
            return {"success": False, "message": "发放奖励失败"}


def sql_get_user_assembly_rewards(tg: int, today_only: bool = True):
    """获取用户的组装奖励记录"""
    with Session() as session:
        try:
            query = session.query(AssemblyReward).filter(AssemblyReward.tg == tg)
            
            if today_only:
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                query = query.filter(AssemblyReward.obtained_date == today)
            
            rewards = query.order_by(AssemblyReward.obtained_time.desc()).all()
            return rewards
        except:
            return []


def sql_update_reward_config(car_id: int, reward_type: str, reward_value: str, reward_description: str = None) -> bool:
    """更新奖励配置"""
    with Session() as session:
        try:
            reward_config = session.query(RewardConfig).filter(RewardConfig.car_id == car_id).first()
            
            if reward_config:
                # 更新现有配置
                reward_config.reward_type = reward_type
                reward_config.reward_value = reward_value
                if reward_description:
                    reward_config.reward_description = reward_description
            else:
                # 创建新配置
                reward_config = RewardConfig(
                    car_id=car_id,
                    reward_type=reward_type,
                    reward_value=reward_value,
                    reward_description=reward_description,
                    is_active=True
                )
                session.add(reward_config)
            
            session.commit()
            return True
        except:
            return False


def sql_get_probability_stats():
    """获取装备抽取概率统计信息 - 自动从概率配置计算"""
    # 计算各个装备的实际概率
    m5_prob = PROBABILITY_THRESHOLDS['M5_PURPLE']
    m4_prob = PROBABILITY_THRESHOLDS['M4_PURPLE'] - PROBABILITY_THRESHOLDS['M5_PURPLE']
    m3_prob = PROBABILITY_THRESHOLDS['M3_PURPLE'] - PROBABILITY_THRESHOLDS['M4_PURPLE']
    m2_prob = PROBABILITY_THRESHOLDS['M2_PURPLE'] - PROBABILITY_THRESHOLDS['M3_PURPLE']
    
    # 计算各个稀有度的总概率
    total_purple = PROBABILITY_THRESHOLDS['M2_PURPLE']
    gold_prob = PROBABILITY_THRESHOLDS['GOLD'] - PROBABILITY_THRESHOLDS['M2_PURPLE']
    green_prob = PROBABILITY_THRESHOLDS['GREEN'] - PROBABILITY_THRESHOLDS['GOLD']
    blue_prob = 100.0 - PROBABILITY_THRESHOLDS['GREEN']
    
    return {
        "purple": {
            "probability": f"{total_purple:.1f}%", 
            "description": "专属车漆奖励",
            "details": {
                "M2_赞德福特蓝车漆": f"{m2_prob:.1f}%",
                "M3_曼岛绿车漆": f"{m3_prob:.1f}%", 
                "M4_圣保罗黄车漆": f"{m4_prob:.2f}%",
                "M5_风暴灰车漆": f"{m5_prob:.2f}%"
            }
        },
        "gold": {"probability": f"{gold_prob:.1f}%", "description": "高级组件"},
        "green": {"probability": f"{green_prob:.1f}%", "description": "车漆变体"},
        "blue": {"probability": f"{blue_prob:.1f}%", "description": "常见物品"}
    }


# 初始化汽车配置
init_cars_and_equipment()

# 为向后兼容保留旧函数名
def init_treasures():
    """向后兼容的初始化函数"""
    return init_cars_and_equipment()

def sql_get_fragment_definition(fragment_id: int):
    """向后兼容的获取碎片定义函数"""
    return sql_get_equipment_definition(fragment_id)

def sql_get_all_fragment_definitions():
    """向后兼容的获取所有碎片定义函数"""
    return sql_get_all_equipment_definitions()

def sql_add_fragment(tg: int, hunt_session_id: int, fragment_id: int) -> bool:
    """向后兼容的添加碎片函数"""
    return sql_add_equipment(tg, hunt_session_id, fragment_id)

def sql_get_user_fragments(tg: int, today_only: bool = True):
    """向后兼容的获取用户碎片函数"""
    return sql_get_user_equipment(tg, today_only)

def sql_get_daily_treasure(date: str = None):
    """向后兼容的获取每日宝物函数"""
    return sql_get_daily_car(date)

def sql_check_treasure_synthesis(tg: int, treasure_id: int) -> bool:
    """向后兼容的检查宝物合成函数"""
    return sql_check_car_assembly(tg, treasure_id)

def sql_synthesize_treasure(tg: int, treasure_id: int) -> bool:
    """向后兼容的合成宝物函数"""
    return sql_assemble_car_legacy(tg, treasure_id)

def sql_cleanup_expired_fragments():
    """向后兼容的清理过期碎片函数"""
    return sql_cleanup_expired_equipment()
