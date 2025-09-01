#!/usr/bin/env python3
"""
Hunt Database Validation Script / 寻宝游戏数据库验证脚本

This script checks if the hunt database structure is compatible with the current game code.
Use this to diagnose issues before running reconstruction.

该脚本检查寻宝游戏数据库结构是否与当前游戏代码兼容。
在运行重构之前使用此脚本诊断问题。

Usage:
    python3 validate_hunt_database.py [--config] [--host HOST --user USER --password PASS --database DB]
"""

import sys
import os
import argparse
import json

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def load_config_from_file():
    """Load database configuration from config.json"""
    config_files = ['config.json', 'config_example.json']
    
    for config_file in config_files:
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
                print(f"Error reading {config_file}: {e}")
                continue
    
    return None

def validate_with_bot_dependencies():
    """Validate using bot dependencies"""
    try:
        from bot.sql_helper import engine
        from sqlalchemy import inspect, text
        from bot import LOGGER
        
        print("✓ Bot dependencies loaded successfully")
        
        # Test database connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✓ Database connection successful")
        
        inspector = inspect(engine)
        return validate_database_structure(inspector, engine)
        
    except ImportError as e:
        print(f"✗ Bot dependencies not available: {e}")
        return False
    except Exception as e:
        print(f"✗ Validation with bot dependencies failed: {e}")
        return False

def validate_with_standalone(db_config):
    """Validate using standalone connection"""
    try:
        import pymysql
        
        connection = pymysql.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            charset='utf8mb4'
        )
        
        print("✓ Database connection successful")
        
        result = validate_database_structure_standalone(connection)
        connection.close()
        return result
        
    except ImportError:
        print("✗ PyMySQL not installed. Install with: pip install PyMySQL")
        return False
    except Exception as e:
        print(f"✗ Standalone validation failed: {e}")
        return False

def validate_database_structure(inspector, engine):
    """Validate database structure using SQLAlchemy inspector"""
    print("\nValidating database structure...")
    
    try:
        existing_tables = inspector.get_table_names()
        
        # Required tables and their critical columns
        required_structure = {
            'hunt': ['id', 'tg', 'start_time', 'game_date', 'is_active', 'hunt_actions', 'daily_car_info'],
            'equipment': ['id', 'tg', 'equipment_id', 'obtained_date', 'hunt_session_id'],
            'equipment_definition': ['equipment_id', 'equipment_name', 'category', 'rarity_weight'],
            'car': ['id', 'car_name', 'equipment_ids', 'description'],
            'daily_car': ['date', 'car_id'],
            'assembly_reward': ['id', 'tg', 'car_id', 'reward_type', 'obtained_date'],
            'reward_config': ['id', 'car_id', 'reward_type', 'reward_value'],
            'reward_button': ['id', 'car_id', 'button_text', 'button_url']
        }
        
        validation_passed = True
        issues = []
        
        for table_name, required_columns in required_structure.items():
            if table_name not in existing_tables:
                print(f"  ✗ Missing table: {table_name}")
                issues.append(f"Missing table: {table_name}")
                validation_passed = False
                continue
                
            # Check columns
            columns = inspector.get_columns(table_name)
            column_names = [col['name'] for col in columns]
            
            missing_columns = [col for col in required_columns if col not in column_names]
            if missing_columns:
                print(f"  ✗ Table {table_name} missing columns: {missing_columns}")
                issues.append(f"Table {table_name} missing columns: {missing_columns}")
                validation_passed = False
            else:
                print(f"  ✓ Table {table_name} structure correct")
        
        # Test key functions if possible
        if validation_passed:
            try:
                from bot.sql_helper.sql_hunt import sql_check_and_fix_hunt_table, sql_get_daily_car
                
                if sql_check_and_fix_hunt_table():
                    print("  ✓ sql_check_and_fix_hunt_table() passed")
                else:
                    print("  ✗ sql_check_and_fix_hunt_table() failed")
                    validation_passed = False
                
                daily_car = sql_get_daily_car()
                if daily_car:
                    print(f"  ✓ Daily car found: {daily_car.car_name}")
                else:
                    print("  ⚠️  No daily car configured (not critical)")
                    
            except Exception as e:
                print(f"  ✗ Function test failed: {e}")
                validation_passed = False
        
        return validation_passed, issues
        
    except Exception as e:
        print(f"✗ Structure validation failed: {e}")
        return False, [f"Structure validation failed: {e}"]

def validate_database_structure_standalone(connection):
    """Validate database structure using direct MySQL connection"""
    print("\nValidating database structure...")
    
    try:
        cursor = connection.cursor()
        
        # Check tables exist
        cursor.execute("SHOW TABLES")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = [
            'hunt', 'equipment', 'equipment_definition', 'car', 'daily_car',
            'assembly_reward', 'reward_config', 'reward_button'
        ]
        
        validation_passed = True
        issues = []
        
        for table_name in required_tables:
            if table_name not in existing_tables:
                print(f"  ✗ Missing table: {table_name}")
                issues.append(f"Missing table: {table_name}")
                validation_passed = False
                continue
            else:
                print(f"  ✓ Table {table_name} exists")
        
        # Check hunt table columns specifically
        if 'hunt' in existing_tables:
            cursor.execute("DESCRIBE hunt")
            hunt_columns = [row[0] for row in cursor.fetchall()]
            
            required_hunt_columns = ['id', 'tg', 'start_time', 'game_date', 'is_active', 'hunt_actions', 'daily_car_info']
            missing_hunt_columns = [col for col in required_hunt_columns if col not in hunt_columns]
            
            if missing_hunt_columns:
                print(f"  ✗ Hunt table missing critical columns: {missing_hunt_columns}")
                issues.append(f"Hunt table missing columns: {missing_hunt_columns}")
                validation_passed = False
            else:
                print("  ✓ Hunt table has all required columns")
        
        # Check if basic data exists
        if validation_passed:
            cursor.execute("SELECT COUNT(*) FROM equipment_definition")
            equipment_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM car")
            car_count = cursor.fetchone()[0]
            
            if equipment_count == 0:
                print("  ⚠️  No equipment definitions found (game may not work properly)")
                issues.append("No equipment definitions")
            else:
                print(f"  ✓ Found {equipment_count} equipment definitions")
                
            if car_count == 0:
                print("  ⚠️  No car configurations found (game may not work properly)")
                issues.append("No car configurations")
            else:
                print(f"  ✓ Found {car_count} car configurations")
        
        cursor.close()
        return validation_passed, issues
        
    except Exception as e:
        print(f"✗ Standalone structure validation failed: {e}")
        return False, [f"Standalone validation failed: {e}"]

def main():
    """Main validation function"""
    parser = argparse.ArgumentParser(description='Validate hunt database structure')
    parser.add_argument('--config', action='store_true', help='Use configuration from config.json')
    parser.add_argument('--host', help='MySQL host')
    parser.add_argument('--user', help='MySQL username')
    parser.add_argument('--password', help='MySQL password')
    parser.add_argument('--database', help='MySQL database name')
    parser.add_argument('--port', type=int, default=3306, help='MySQL port')
    
    args = parser.parse_args()
    
    print("Hunt Database Validation Script")
    print("=" * 50)
    
    # Try bot dependencies first
    print("Attempting validation with bot dependencies...")
    if validate_with_bot_dependencies():
        print("\n✅ Validation PASSED - Database structure is compatible!")
        print("The hunt game should work correctly.")
        return True
    
    print("\nBot dependencies validation failed, trying standalone validation...")
    
    # Get database configuration
    if args.config:
        db_config = load_config_from_file()
        if not db_config:
            print("Could not load database configuration")
            return False
    else:
        if not all([args.host, args.user, args.database]):
            print("Error: Must provide --host, --user, --database or use --config")
            return False
        
        db_config = {
            'host': args.host,
            'user': args.user,
            'password': args.password or '',
            'database': args.database,
            'port': args.port
        }
    
    print(f"Database: {db_config['user']}@{db_config['host']}:{db_config['port']}/{db_config['database']}")
    
    validation_passed, issues = validate_with_standalone(db_config)
    
    print("\n" + "=" * 50)
    
    if validation_passed:
        print("✅ Validation PASSED - Database structure is compatible!")
        print("The hunt game should work correctly.")
    else:
        print("❌ Validation FAILED - Database structure needs reconstruction!")
        print("\nIssues found:")
        for issue in issues:
            print(f"  - {issue}")
        
        print("\n🔧 To fix these issues, run the reconstruction script:")
        print("   python3 reconstruct_hunt_database.py --backup")
        print("   OR")
        print("   python3 reconstruct_hunt_database_standalone.py --config --backup")
    
    return validation_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)