"""
初始化数据库
"""
from bot import db_host, db_user, db_pwd, db_name, db_port
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
import logging
import os

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

def auto_migrate_preserve_mode_fields():
    """
    自动迁移保号方式字段（Docker模式下使用）
    """
    try:
        with engine.connect() as conn:
            # 检查是否需要添加 preserve_mode 字段
            result = conn.execute(text("""
                SELECT COUNT(*) as count 
                FROM information_schema.columns 
                WHERE table_schema = :db_name 
                AND table_name = 'emby' 
                AND column_name = 'preserve_mode'
            """), {"db_name": db_name})
            
            preserve_mode_exists = result.fetchone()[0] > 0
            
            if not preserve_mode_exists:
                logger.info("➕ 自动添加 preserve_mode 字段...")
                conn.execute(text("""
                    ALTER TABLE emby 
                    ADD COLUMN preserve_mode VARCHAR(10) DEFAULT 'active' 
                    COMMENT '保号方式: active=活跃保号, expire=到期保号'
                """))
                conn.commit()
                logger.info("✅ preserve_mode 字段自动添加成功")
            
            # 检查是否需要添加 preserve_mode_changed 字段
            result = conn.execute(text("""
                SELECT COUNT(*) as count 
                FROM information_schema.columns 
                WHERE table_schema = :db_name 
                AND table_name = 'emby' 
                AND column_name = 'preserve_mode_changed'
            """), {"db_name": db_name})
            
            preserve_mode_changed_exists = result.fetchone()[0] > 0
            
            if not preserve_mode_changed_exists:
                logger.info("➕ 自动添加 preserve_mode_changed 字段...")
                conn.execute(text("""
                    ALTER TABLE emby 
                    ADD COLUMN preserve_mode_changed INT DEFAULT 0 
                    COMMENT '是否已切换过保号方式: 0=未切换, 1=已切换'
                """))
                conn.commit()
                logger.info("✅ preserve_mode_changed 字段自动添加成功")
            
            # 确保现有记录有默认值
            if not preserve_mode_exists or not preserve_mode_changed_exists:
                logger.info("🔄 更新现有记录的默认值...")
                conn.execute(text("""
                    UPDATE emby 
                    SET preserve_mode = 'active' 
                    WHERE preserve_mode IS NULL
                """))
                conn.execute(text("""
                    UPDATE emby 
                    SET preserve_mode_changed = 0 
                    WHERE preserve_mode_changed IS NULL
                """))
                conn.commit()
                logger.info("✅ 现有记录默认值更新完成")
                
    except Exception as e:
        logger.error(f"❌ 保号方式字段自动迁移失败: {e}")

# 先创建所有表（如果不存在）
try:
    Base.metadata.create_all(bind=engine, checkfirst=True)
    logger.info("✅ 数据库表结构检查完成")
    
    # Docker模式下自动处理保号方式字段迁移
    docker_mode = os.getenv('DOCKER_MODE', '0') == '1'
    if docker_mode:
        logger.info("🐳 Docker模式检测到，执行自动数据库迁移...")
        auto_migrate_preserve_mode_fields()
        logger.info("✅ Docker模式下保号方式字段自动迁移完成")
    
except Exception as e:
    logger.error(f"❌ 数据库初始化失败: {e}")


# 调用sql_start()函数，返回一个Session对象
def sql_start() -> scoped_session:
    return scoped_session(sessionmaker(bind=engine, autoflush=False))


Session = sql_start()
