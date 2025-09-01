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

注意：如果遇到依赖问题，请使用独立版本：
Note: If you encounter dependency issues, use the standalone version:
python3 migrate_hunt_table_standalone.py --config
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def try_standalone_migration():
    """尝试运行独立迁移脚本"""
    standalone_script = os.path.join(os.path.dirname(__file__), 'migrate_hunt_table_standalone.py')
    if os.path.exists(standalone_script):
        print(f"Trying to run standalone migration script: {standalone_script}")
        import subprocess
        try:
            result = subprocess.run([sys.executable, standalone_script, '--config'], 
                                  capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print("Errors:", result.stderr)
            return result.returncode == 0
        except Exception as e:
            print(f"Failed to run standalone script: {e}")
            return False
    return False

try:
    from bot.sql_helper import engine
    from sqlalchemy import text, inspect
    print("Successfully imported database engine")
except ImportError as e:
    print(f"Failed to import database engine: {e}")
    print("This usually happens when:")
    print("1. Required dependencies are not installed")
    print("2. Configuration files are missing")
    print("3. Database connection parameters are not set")
    print()
    print("Attempting to use standalone migration script...")
    
    if try_standalone_migration():
        print("Standalone migration completed successfully!")
        sys.exit(0)
    else:
        print()
        print("Standalone migration also failed. Manual steps:")
        print("1. Install dependencies: pip install PyMySQL SQLAlchemy loguru pydantic")
        print("2. Or run standalone migration with database parameters:")
        print("   python3 migrate_hunt_table_standalone.py --host HOST --user USER --password PASS --database DB")
        print("3. Or execute the SQL script manually:")
        print("   mysql -u username -p database_name < migrate_hunt_table.sql")
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
        print("\nThis might be because:")
        print("1. Database server is not running")
        print("2. Database configuration is incorrect")
        print("3. Network connectivity issues")
        print("\nPlease check your database configuration in bot/__init__.py")
        print("\nTrying standalone migration as fallback...")
        if try_standalone_migration():
            return True
        return False
    
    # 检查hunt表是否存在
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        if 'hunt' not in tables:
            print("✗ Hunt table does not exist. Please create it first.")
            print("You can create it by running the application once, which will auto-create tables.")
            return False
        print("✓ Hunt table exists")
    except Exception as e:
        print(f"✗ Failed to check if hunt table exists: {e}")
        return False
    
    # 执行迁移
    success = True
    try:
        success &= add_hunt_actions_column()
        success &= add_daily_car_info_column()
    except Exception as e:
        print(f"✗ Migration execution failed: {e}")
        success = False
    
    if success:
        # 验证迁移
        try:
            if verify_migration():
                print("\n" + "=" * 50)
                print("✓ Hunt table migration completed successfully!")
                print("The application should now work without the column errors.")
                print("You can now restart your bot application.")
                return True
            else:
                print("\n" + "=" * 50)
                print("✗ Migration completed but verification failed.")
                print("Please check the database manually or contact support.")
                return False
        except Exception as e:
            print(f"\n✗ Migration verification failed: {e}")
            return False
    else:
        print("\n" + "=" * 50)
        print("✗ Migration failed.")
        print("\nTrying standalone migration as fallback...")
        if try_standalone_migration():
            return True
        print("Please check MIGRATION_README.md for manual migration steps.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)