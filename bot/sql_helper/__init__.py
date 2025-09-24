"""
初始化数据库
"""
from bot import db_host, db_user, db_pwd, db_name, db_port
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
import logging

logger = logging.getLogger(__name__)

# 创建engine对象
engine = create_engine(f"mysql+pymysql://{db_user}:{db_pwd}@{db_host}:{db_port}/{db_name}?utf8mb4", echo=False,
                       echo_pool=False,
                       pool_size=16,
                       pool_recycle=60 * 30,
                       )

# 创建Base对象
Base = declarative_base()
Base.metadata.bind = engine

# 先创建所有表（如果不存在），然后手动处理可能的字段添加
try:
    Base.metadata.create_all(bind=engine, checkfirst=True)
    logger.info("✅ 数据库表结构检查完成")
except Exception as e:
    logger.error(f"❌ 数据库表创建失败: {e}")


# 调用sql_start()函数，返回一个Session对象
def sql_start() -> scoped_session:
    return scoped_session(sessionmaker(bind=engine, autoflush=False))


Session = sql_start()
