#!/usr/bin/env python3
"""
数据库验证脚本 - 检查保号方式字段
Database Verification Script - Check preservation mode fields

这个脚本用于验证保号方式相关字段是否正确添加到数据库中
This script verifies that preservation mode fields are correctly added to the database
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(__file__))

try:
    from bot import db_host, db_user, db_pwd, db_name, db_port
    from sqlalchemy import create_engine, text
    import logging
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    def verify_preserve_mode_setup():
        """
        验证保号方式数据库设置
        """
        try:
            engine = create_engine(
                f"mysql+pymysql://{db_user}:{db_pwd}@{db_host}:{db_port}/{db_name}?utf8mb4",
                echo=False
            )
            
            logger.info("🔍 正在验证数据库设置...")
            
            with engine.connect() as conn:
                # 检查表结构
                result = conn.execute(text("""
                    SELECT 
                        COLUMN_NAME,
                        DATA_TYPE,
                        IS_NULLABLE,
                        COLUMN_DEFAULT,
                        COLUMN_COMMENT
                    FROM information_schema.columns 
                    WHERE table_schema = :db_name 
                    AND table_name = 'emby' 
                    AND column_name IN ('preserve_mode', 'preserve_mode_changed')
                    ORDER BY column_name
                """), {"db_name": db_name})
                
                columns = result.fetchall()
                
                print("\n📋 保号方式字段检查结果:")
                print("-" * 80)
                
                if not columns:
                    print("❌ 未发现保号方式相关字段")
                    return False
                
                for col in columns:
                    name, data_type, nullable, default, comment = col
                    print(f"✅ {name}")
                    print(f"   类型: {data_type}")
                    print(f"   可空: {nullable}")
                    print(f"   默认值: {default}")
                    print(f"   注释: {comment or '无'}")
                    print()
                
                # 检查数据完整性
                result = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total_users,
                        COUNT(preserve_mode) as users_with_mode,
                        COUNT(preserve_mode_changed) as users_with_changed,
                        SUM(CASE WHEN preserve_mode = 'active' THEN 1 ELSE 0 END) as active_users,
                        SUM(CASE WHEN preserve_mode = 'expire' THEN 1 ELSE 0 END) as expire_users,
                        SUM(CASE WHEN preserve_mode_changed = 1 THEN 1 ELSE 0 END) as switched_users
                    FROM emby 
                    WHERE embyid IS NOT NULL
                """))
                
                stats = result.fetchone()
                total, with_mode, with_changed, active, expire, switched = stats
                
                print("📊 数据统计:")
                print("-" * 40)
                print(f"总用户数: {total}")
                print(f"有保号方式的用户: {with_mode}")
                print(f"有切换状态的用户: {with_changed}")
                print(f"活跃保号用户: {active}")
                print(f"到期保号用户: {expire}")
                print(f"已切换过的用户: {switched}")
                print()
                
                # 检查是否有NULL值
                result = conn.execute(text("""
                    SELECT COUNT(*) as null_count
                    FROM emby 
                    WHERE embyid IS NOT NULL 
                    AND (preserve_mode IS NULL OR preserve_mode_changed IS NULL)
                """))
                
                null_count = result.fetchone()[0]
                
                if null_count > 0:
                    print(f"⚠️  发现 {null_count} 个用户的保号方式字段为空")
                    print("建议运行: python3 migrate_preserve_mode.py")
                    return False
                else:
                    print("✅ 所有用户都有完整的保号方式数据")
                
                print()
                print("🎉 数据库验证通过！")
                print("✅ Bot 可以正常运行保号方式功能")
                
                return True
                
        except Exception as e:
            logger.error(f"❌ 验证失败: {str(e)}")
            return False
    
    def test_sqlalchemy_integration():
        """
        测试 SQLAlchemy 集成
        """
        try:
            logger.info("🔍 测试 SQLAlchemy 集成...")
            
            from bot.sql_helper.sql_emby import sql_get_emby, Emby
            from bot.sql_helper import Session
            
            # 测试字段访问
            with Session() as session:
                test_user = session.query(Emby).first()
                if test_user:
                    preserve_mode = getattr(test_user, 'preserve_mode', None)
                    preserve_mode_changed = getattr(test_user, 'preserve_mode_changed', None)
                    
                    print("🧪 SQLAlchemy 字段测试:")
                    print(f"   preserve_mode: {preserve_mode}")
                    print(f"   preserve_mode_changed: {preserve_mode_changed}")
                    
                    if preserve_mode is not None and preserve_mode_changed is not None:
                        print("✅ SQLAlchemy 可以正常访问保号方式字段")
                        return True
                    else:
                        print("❌ SQLAlchemy 无法访问保号方式字段")
                        return False
                else:
                    print("ℹ️  数据库中暂无用户数据，无法测试字段访问")
                    return True
                    
        except Exception as e:
            logger.error(f"❌ SQLAlchemy 测试失败: {str(e)}")
            return False
    
    if __name__ == "__main__":
        print("=" * 60)
        print("BavaBot 保号方式数据库验证工具")
        print("BavaBot Preservation Mode Database Verification Tool")
        print("=" * 60)
        
        # 验证数据库
        db_ok = verify_preserve_mode_setup()
        
        # 测试 SQLAlchemy
        sqlalchemy_ok = test_sqlalchemy_integration()
        
        print("\n" + "=" * 60)
        
        if db_ok and sqlalchemy_ok:
            print("🎉 所有检查通过！")
            print("✅ 数据库已正确配置保号方式功能")
            print("✅ Bot 可以安全启动")
        else:
            print("❌ 发现问题，请先运行迁移脚本:")
            print("   python3 migrate_preserve_mode.py")

except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请确保在 bavabot 项目根目录下运行此脚本")
    print("Please run this script from the bavabot project root directory")
    sys.exit(1)