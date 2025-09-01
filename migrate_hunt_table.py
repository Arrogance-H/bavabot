#!/usr/bin/env python3
"""
数据库迁移脚本：为hunt表添加缺失的列
Database migration script: Add missing columns to hunt table

这个脚本解决的问题：
- hunt表缺少hunt_actions列（寻找装备的次数）
- hunt表缺少daily_car_info列（缓存的每日汽车信息）

This script fixes the issue:
- hunt table missing hunt_actions column (hunt action count)
- hunt table missing daily_car_info column (cached daily car info)
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from bot.sql_helper import engine
    from sqlalchemy import text, inspect
    print("Successfully imported database engine")
except ImportError as e:
    print(f"Failed to import database engine: {e}")
    print("Please make sure you have installed the required dependencies:")
    print("pip install PyMySQL SQLAlchemy")
    sys.exit(1)


def check_column_exists(table_name, column_name):
    """检查表中是否存在指定列"""
    try:
        inspector = inspect(engine)
        columns = inspector.get_columns(table_name)
        column_names = [col['name'] for col in columns]
        return column_name in column_names
    except Exception as e:
        print(f"Error checking column {column_name} in table {table_name}: {e}")
        return False


def add_hunt_actions_column():
    """添加hunt_actions列"""
    if check_column_exists('hunt', 'hunt_actions'):
        print("Column 'hunt_actions' already exists, skipping...")
        return True
    
    try:
        with engine.connect() as conn:
            # 添加hunt_actions列，默认值为0
            sql = text("ALTER TABLE hunt ADD COLUMN hunt_actions INT DEFAULT 0 COMMENT '寻找装备的次数'")
            conn.execute(sql)
            conn.commit()
            print("✓ Successfully added 'hunt_actions' column to hunt table")
            return True
    except Exception as e:
        print(f"✗ Failed to add 'hunt_actions' column: {e}")
        return False


def add_daily_car_info_column():
    """添加daily_car_info列"""
    if check_column_exists('hunt', 'daily_car_info'):
        print("Column 'daily_car_info' already exists, skipping...")
        return True
    
    try:
        with engine.connect() as conn:
            # 添加daily_car_info列，允许NULL
            sql = text("ALTER TABLE hunt ADD COLUMN daily_car_info TEXT NULL COMMENT '缓存的每日汽车信息'")
            conn.execute(sql)
            conn.commit()
            print("✓ Successfully added 'daily_car_info' column to hunt table")
            return True
    except Exception as e:
        print(f"✗ Failed to add 'daily_car_info' column: {e}")
        return False


def verify_migration():
    """验证迁移是否成功"""
    try:
        inspector = inspect(engine)
        columns = inspector.get_columns('hunt')
        column_names = [col['name'] for col in columns]
        
        print("\nCurrent hunt table columns:")
        for col in columns:
            print(f"  - {col['name']} ({col['type']})")
        
        missing_columns = []
        if 'hunt_actions' not in column_names:
            missing_columns.append('hunt_actions')
        if 'daily_car_info' not in column_names:
            missing_columns.append('daily_car_info')
        
        if missing_columns:
            print(f"\n✗ Migration verification failed. Missing columns: {missing_columns}")
            return False
        else:
            print("\n✓ Migration verification successful. All required columns are present.")
            return True
            
    except Exception as e:
        print(f"✗ Migration verification failed: {e}")
        return False


def main():
    """主函数"""
    print("Starting hunt table migration...")
    print("=" * 50)
    
    try:
        # 测试数据库连接
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✓ Database connection successful")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        print("\nPlease check your database configuration in bot/__init__.py")
        return False
    
    # 检查hunt表是否存在
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        if 'hunt' not in tables:
            print("✗ Hunt table does not exist. Please create it first.")
            return False
        print("✓ Hunt table exists")
    except Exception as e:
        print(f"✗ Failed to check if hunt table exists: {e}")
        return False
    
    # 执行迁移
    success = True
    success &= add_hunt_actions_column()
    success &= add_daily_car_info_column()
    
    if success:
        # 验证迁移
        if verify_migration():
            print("\n" + "=" * 50)
            print("✓ Hunt table migration completed successfully!")
            print("The application should now work without the column errors.")
            return True
        else:
            print("\n" + "=" * 50)
            print("✗ Migration completed but verification failed.")
            return False
    else:
        print("\n" + "=" * 50)
        print("✗ Migration failed.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)