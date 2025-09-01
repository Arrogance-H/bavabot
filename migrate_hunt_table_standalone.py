#!/usr/bin/env python3
"""
独立数据库迁移脚本：为hunt表添加缺失的列
Standalone database migration script: Add missing columns to hunt table

这个脚本解决的问题：
- hunt表缺少hunt_actions列（寻找装备的次数）
- hunt表缺少daily_car_info列（缓存的每日汽车信息）

This script fixes the issue:
- hunt table missing hunt_actions column (hunt action count)  
- hunt table missing daily_car_info column (cached daily car info)

使用方法 / Usage:
python3 migrate_hunt_table_standalone.py --host localhost --user root --password pass --database dbname
"""

import sys
import argparse
import json
import os

def load_config_from_file():
    """从配置文件加载数据库配置"""
    config_file = "config.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return {
                    'host': config.get('db_host', 'localhost'),
                    'user': config.get('db_user', 'root'),
                    'password': config.get('db_pwd', ''),
                    'database': config.get('db_name', 'bavabot'),
                    'port': config.get('db_port', 3306)
                }
        except Exception as e:
            print(f"Warning: Could not load config file: {e}")
    return None

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Hunt table migration script')
    parser.add_argument('--host', help='Database host')
    parser.add_argument('--user', help='Database user')
    parser.add_argument('--password', help='Database password')
    parser.add_argument('--database', help='Database name')
    parser.add_argument('--port', type=int, default=3306, help='Database port')
    parser.add_argument('--config', action='store_true', help='Try to load config from file')
    
    args = parser.parse_args()
    
    # 尝试从配置文件加载
    db_config = None
    if args.config or not any([args.host, args.user, args.password, args.database]):
        db_config = load_config_from_file()
        if db_config:
            print("Loaded database configuration from config file")
        else:
            print("Could not load config from file, please provide database parameters")
    
    # 使用命令行参数覆盖配置文件
    if not db_config:
        db_config = {}
    
    db_config.update({
        'host': args.host or db_config.get('host'),
        'user': args.user or db_config.get('user'), 
        'password': args.password or db_config.get('password'),
        'database': args.database or db_config.get('database'),
        'port': args.port or db_config.get('port', 3306)
    })
    
    # 检查必需参数
    if not all([db_config.get('host'), db_config.get('user'), db_config.get('database')]):
        print("Error: Missing required database parameters")
        print("Please provide --host, --user, --password, --database or use --config")
        return False
    
    try:
        import pymysql
    except ImportError:
        print("Error: PyMySQL is required. Install it with: pip install PyMySQL")
        return False
    
    print("Starting hunt table migration...")
    print("=" * 50)
    
    # 连接数据库
    try:
        connection = pymysql.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config.get('password', ''),
            database=db_config['database'],
            port=db_config['port'],
            charset='utf8mb4'
        )
        print("✓ Database connection successful")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False
    
    try:
        with connection.cursor() as cursor:
            # 检查hunt表是否存在
            cursor.execute("SHOW TABLES LIKE 'hunt'")
            if not cursor.fetchone():
                print("✗ Hunt table does not exist. Please create it first.")
                return False
            print("✓ Hunt table exists")
            
            # 检查hunt_actions列是否存在
            cursor.execute("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'hunt' 
                AND COLUMN_NAME = 'hunt_actions' 
                AND TABLE_SCHEMA = %s
            """, (db_config['database'],))
            
            hunt_actions_exists = cursor.fetchone()[0] > 0
            
            if hunt_actions_exists:
                print("Column 'hunt_actions' already exists, skipping...")
            else:
                # 添加hunt_actions列
                cursor.execute("""
                    ALTER TABLE hunt ADD COLUMN hunt_actions INT DEFAULT 0 COMMENT '寻找装备的次数'
                """)
                print("✓ Successfully added 'hunt_actions' column to hunt table")
            
            # 检查daily_car_info列是否存在
            cursor.execute("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'hunt' 
                AND COLUMN_NAME = 'daily_car_info' 
                AND TABLE_SCHEMA = %s
            """, (db_config['database'],))
            
            daily_car_info_exists = cursor.fetchone()[0] > 0
            
            if daily_car_info_exists:
                print("Column 'daily_car_info' already exists, skipping...")
            else:
                # 添加daily_car_info列
                cursor.execute("""
                    ALTER TABLE hunt ADD COLUMN daily_car_info TEXT NULL COMMENT '缓存的每日汽车信息'
                """)
                print("✓ Successfully added 'daily_car_info' column to hunt table")
            
            # 提交更改
            connection.commit()
            
            # 验证迁移
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'hunt' 
                AND TABLE_SCHEMA = %s
                ORDER BY ORDINAL_POSITION
            """, (db_config['database'],))
            
            columns = cursor.fetchall()
            print("\nCurrent hunt table columns:")
            for col in columns:
                column_name, data_type, is_nullable, default_value, comment = col
                print(f"  - {column_name} ({data_type}, nullable: {is_nullable}, default: {default_value}) - {comment}")
            
            # 检查必需的列是否都存在
            column_names = [col[0] for col in columns]
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
                print("\n" + "=" * 50)
                print("✓ Hunt table migration completed successfully!")
                print("The application should now work without the column errors.")
                return True
                
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        connection.rollback()
        return False
    finally:
        connection.close()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)