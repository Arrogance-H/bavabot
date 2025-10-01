#!/usr/bin/env python3
"""
数据库迁移脚本 - 添加保号方式及M欢迎相关字段 (手动模式)
Database Migration Script - Add preservation mode and M-welcome fields (Manual Mode)

注意：此脚本用于非 Docker 环境。Docker 用户无需手动运行此脚本，
因为 Docker 模式下会自动执行数据库迁移。

Note: This script is for non-Docker environments. Docker users don't need 
to run this script manually as Docker mode performs automatic migration.

这个脚本用于安全地向现有的 emby 表添加新的字段
This script safely adds new fields to the existing emby table
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(__file__))

def check_docker_mode():
    """检查是否在 Docker 模式下运行"""
    docker_mode = os.getenv('DOCKER_MODE', '0') == '1'
    if docker_mode:
        print("🐳 检测到 Docker 模式！")
        print("📋 Docker 模式下数据库迁移是自动的，无需手动运行此脚本。")
        print("✅ 请直接启动 Bot，迁移会自动完成。")
        print()
        response = input("确定要继续手动迁移吗？(y/N): ")
        if response.lower() != 'y':
            print("操作已取消。")
            sys.exit(0)

try:
    from bot import db_host, db_user, db_pwd, db_name, db_port
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import OperationalError, ProgrammingError
    import logging
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    def migrate_preserve_mode_fields():
        """
        安全地添加保号方式及M欢迎字段到 emby 表
        """
        try:
            # 创建新的引擎连接 (不依赖现有的 Base)
            engine = create_engine(
                f"mysql+pymysql://{db_user}:{db_pwd}@{db_host}:{db_port}/{db_name}?utf8mb4",
                echo=False
            )
            
            logger.info("🔍 正在检查数据库连接...")
            
            with engine.connect() as conn:
                # 检查 emby 表是否存在
                result = conn.execute(text("""
                    SELECT COUNT(*) as count 
                    FROM information_schema.tables 
                    WHERE table_schema = :db_name AND table_name = 'emby'
                """), {"db_name": db_name})
                
                table_exists = result.fetchone()[0] > 0
                
                if not table_exists:
                    logger.info("📋 emby 表不存在，将由 SQLAlchemy 自动创建")
                    return True
                
                logger.info("✅ emby 表存在，检查字段...")
                
                # 检查 preserve_mode 字段
                result = conn.execute(text("""
                    SELECT COUNT(*) as count 
                    FROM information_schema.columns 
                    WHERE table_schema = :db_name 
                    AND table_name = 'emby' 
                    AND column_name = 'preserve_mode'
                """), {"db_name": db_name})
                
                preserve_mode_exists = result.fetchone()[0] > 0
                
                # 检查 preserve_mode_changed 字段
                result = conn.execute(text("""
                    SELECT COUNT(*) as count 
                    FROM information_schema.columns 
                    WHERE table_schema = :db_name 
                    AND table_name = 'emby' 
                    AND column_name = 'preserve_mode_changed'
                """), {"db_name": db_name})
                
                preserve_mode_changed_exists = result.fetchone()[0] > 0
                
                # 检查 m_welcome_date 字段
                result = conn.execute(text("""
                    SELECT COUNT(*) as count 
                    FROM information_schema.columns 
                    WHERE table_schema = :db_name 
                    AND table_name = 'emby' 
                    AND column_name = 'm_welcome_date'
                """), {"db_name": db_name})
                
                m_welcome_date_exists = result.fetchone()[0] > 0
                
                # 添加缺失的字段
                if not preserve_mode_exists:
                    logger.info("➕ 添加 preserve_mode 字段...")
                    conn.execute(text("""
                        ALTER TABLE emby 
                        ADD COLUMN preserve_mode VARCHAR(10) DEFAULT 'active' 
                        COMMENT '保号方式: active=活跃保号, expire=到期保号'
                    """))
                    conn.commit()
                    logger.info("✅ preserve_mode 字段添加成功")
                else:
                    logger.info("✅ preserve_mode 字段已存在")
                
                if not preserve_mode_changed_exists:
                    logger.info("➕ 添加 preserve_mode_changed 字段...")
                    conn.execute(text("""
                        ALTER TABLE emby 
                        ADD COLUMN preserve_mode_changed INT DEFAULT 0 
                        COMMENT '是否已切换过保号方式: 0=未切换, 1=已切换'
                    """))
                    conn.commit()
                    logger.info("✅ preserve_mode_changed 字段添加成功")
                else:
                    logger.info("✅ preserve_mode_changed 字段已存在")
                
                if not m_welcome_date_exists:
                    logger.info("➕ 添加 m_welcome_date 字段...")
                    conn.execute(text("""
                        ALTER TABLE emby 
                        ADD COLUMN m_welcome_date DATETIME DEFAULT NULL 
                        COMMENT 'M尊享用户最后欢迎日期时间'
                    """))
                    conn.commit()
                    logger.info("✅ m_welcome_date 字段添加成功")
                else:
                    logger.info("✅ m_welcome_date 字段已存在")
                
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
                
                logger.info("🎉 字段迁移完成！")
                return True
                
        except Exception as e:
            logger.error(f"❌ 迁移失败: {str(e)}")
            return False
    
    if __name__ == "__main__":
        print("=" * 60)
        print("BavaBot 数据库迁移工具 (手动模式)")
        print("BavaBot Database Migration Tool (Manual Mode)")
        print("=" * 60)
        print()
        
        # 检查 Docker 模式
        check_docker_mode()
        
        success = migrate_preserve_mode_fields()
        
        if success:
            print()
            print("🎉 迁移完成！")
            print("✅ 数据库已准备好支持新功能")
            print("✅ Bot 现在可以正常运行")
            print()
            print("📋 新增字段说明:")
            print("• preserve_mode: 用户保号方式 ('active'=活跃保号, 'expire'=到期保号)")
            print("• preserve_mode_changed: 是否已切换过 (0=未切换, 1=已切换)")
            print("• m_welcome_date: M尊享用户最后欢迎日期时间")
            print()
            print("🐳 Docker 用户提示：")
            print("如果您使用 Docker 部署，下次可以直接启动容器，")
            print("系统会自动处理数据库迁移，无需手动运行此脚本。")
        else:
            print()
            print("❌ 迁移失败")
            print("请检查数据库连接和权限设置")
            sys.exit(1)

except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请确保在 bavabot 项目根目录下运行此脚本")
    print("Please run this script from the bavabot project root directory")
    print()
    print("🐳 Docker 用户注意：")
    print("如果您使用 Docker，无需运行此脚本。")
    print("直接启动 Docker 容器即可，迁移会自动完成。")
    sys.exit(1)