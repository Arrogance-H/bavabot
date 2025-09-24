#!/usr/bin/env python3
"""
数据库迁移脚本 - 添加保号方式相关字段
Database Migration Script - Add preservation mode fields

这个脚本用于安全地向现有的 emby 表添加新的保号方式字段
This script safely adds new preservation mode fields to the existing emby table
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(__file__))

try:
    from bot import db_host, db_user, db_pwd, db_name, db_port
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import OperationalError, ProgrammingError
    import logging
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    def migrate_preserve_mode_fields():
        """
        安全地添加保号方式字段到 emby 表
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
                
                logger.info("✅ emby 表存在，检查保号方式字段...")
                
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
                
                logger.info("🎉 保号方式字段迁移完成！")
                return True
                
        except Exception as e:
            logger.error(f"❌ 迁移失败: {str(e)}")
            return False
    
    if __name__ == "__main__":
        print("=" * 60)
        print("BavaBot 保号方式数据库迁移工具")
        print("BavaBot Preservation Mode Database Migration Tool")
        print("=" * 60)
        print()
        
        success = migrate_preserve_mode_fields()
        
        if success:
            print()
            print("🎉 迁移完成！")
            print("✅ 数据库已准备好支持保号方式功能")
            print("✅ Bot 现在可以正常运行")
            print()
            print("📋 新增字段说明:")
            print("• preserve_mode: 用户保号方式 ('active'=活跃保号, 'expire'=到期保号)")
            print("• preserve_mode_changed: 是否已切换过 (0=未切换, 1=已切换)")
        else:
            print()
            print("❌ 迁移失败")
            print("请检查数据库连接和权限设置")
            sys.exit(1)

except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请确保在 bavabot 项目根目录下运行此脚本")
    print("Please run this script from the bavabot project root directory")
    sys.exit(1)