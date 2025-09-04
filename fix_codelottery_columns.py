#!/usr/bin/env python3
"""
CodeLottery Database Column Migration Fix

This script fixes the missing column issue in the code_lottery_rounds and code_lottery_users tables.
Run this script to add the missing 'creator_tg' and other columns.

Usage:
    python3 fix_codelottery_columns.py [--host HOST] [--port PORT] [--user USER] [--password PASS] [--database DB]

Or if you have the bot configuration:
    python3 fix_codelottery_columns.py --use-bot-config
"""
import argparse
import sys
import os

def fix_codelottery_database(host, port, user, password, database):
    """Fix the code_lottery_rounds and code_lottery_users tables by adding missing columns"""
    try:
        import pymysql
        
        print(f"🔍 Connecting to {host}:{port}/{database} as {user}")
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4'
        )
        
        success = True
        
        # Fix code_lottery_rounds table
        success &= fix_code_lottery_rounds_table(connection)
        
        # Fix code_lottery_users table
        success &= fix_code_lottery_users_table(connection)
        
        connection.close()
        return success
        
    except ImportError:
        print("❌ PyMySQL library not found. Please install it: pip install pymysql")
        return False
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def fix_code_lottery_rounds_table(connection):
    """Fix the code_lottery_rounds table by adding missing columns"""
    try:
        with connection.cursor() as cursor:
            # Check if table exists
            cursor.execute("SHOW TABLES LIKE 'code_lottery_rounds'")
            if not cursor.fetchone():
                print("✅ Table code_lottery_rounds does not exist yet - will be created by bot")
                return True
                
            print("📋 Checking code_lottery_rounds table structure...")
            cursor.execute("DESCRIBE code_lottery_rounds")
            existing_columns = [row[0] for row in cursor.fetchall()]
            print(f"   Current columns: {existing_columns}")
            
            # Define the required columns
            required_columns = {
                'creator_tg': 'BIGINT NOT NULL DEFAULT 0 COMMENT "创建者TG ID"'
            }
            
            # Add missing columns
            columns_added = []
            for col_name, col_definition in required_columns.items():
                if col_name not in existing_columns:
                    print(f"🔧 Adding missing column: {col_name}")
                    alter_sql = f"ALTER TABLE code_lottery_rounds ADD COLUMN {col_name} {col_definition}"
                    cursor.execute(alter_sql)
                    columns_added.append(col_name)
                else:
                    print(f"✅ Column {col_name} already exists")
            
            if columns_added:
                connection.commit()
                print(f"✅ Successfully added columns to code_lottery_rounds: {columns_added}")
            else:
                print("✅ code_lottery_rounds table structure is already correct")
                
            return True
            
    except Exception as e:
        print(f"❌ Failed to fix code_lottery_rounds table: {e}")
        connection.rollback()
        return False


def fix_code_lottery_users_table(connection):
    """Fix the code_lottery_users table by adding missing columns"""
    try:
        with connection.cursor() as cursor:
            # Check if table exists
            cursor.execute("SHOW TABLES LIKE 'code_lottery_users'")
            if not cursor.fetchone():
                print("✅ Table code_lottery_users does not exist yet - will be created by bot")
                return True
                
            print("📋 Checking code_lottery_users table structure...")
            cursor.execute("DESCRIBE code_lottery_users")
            existing_columns = [row[0] for row in cursor.fetchall()]
            print(f"   Current columns: {existing_columns}")
            
            # Define the required columns
            required_columns = {
                'total_participation': 'INT DEFAULT 0 COMMENT "总参与次数"',
                'total_wins': 'INT DEFAULT 0 COMMENT "总获奖次数"',
                'guaranteed_count': 'INT DEFAULT 0 COMMENT "当前保底次数"',
                'last_participation': 'DATETIME NULL COMMENT "最后参与时间"',
                'last_win': 'DATETIME NULL COMMENT "最后获奖时间"'
            }
            
            # Add missing columns
            columns_added = []
            for col_name, col_definition in required_columns.items():
                if col_name not in existing_columns:
                    print(f"🔧 Adding missing column: {col_name}")
                    alter_sql = f"ALTER TABLE code_lottery_users ADD COLUMN {col_name} {col_definition}"
                    cursor.execute(alter_sql)
                    columns_added.append(col_name)
                else:
                    print(f"✅ Column {col_name} already exists")
            
            if columns_added:
                connection.commit()
                print(f"✅ Successfully added columns to code_lottery_users: {columns_added}")
            else:
                print("✅ code_lottery_users table structure is already correct")
                
            return True
            
    except Exception as e:
        print(f"❌ Failed to fix code_lottery_users table: {e}")
        connection.rollback()
        return False

def load_bot_config():
    """Load database settings from bot configuration"""
    try:
        import json
        
        config_files = [
            'config.json',
            'config_example.json'
        ]
        
        for config_file in config_files:
            if os.path.exists(config_file):
                print(f"📂 Loading config from {config_file}")
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                return {
                    'host': config.get('db_host', 'localhost'),
                    'port': config.get('db_port', 3306),
                    'user': config.get('db_user', ''),
                    'password': config.get('db_pwd', ''),
                    'database': config.get('db_name', '')
                }
                
        print("❌ No config file found (config.json or config_example.json)")
        return None
        
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Fix CodeLottery database columns')
    parser.add_argument('--host', default='localhost', help='Database host')
    parser.add_argument('--port', type=int, default=3306, help='Database port')
    parser.add_argument('--user', help='Database user')
    parser.add_argument('--password', default='', help='Database password')
    parser.add_argument('--database', help='Database name')
    parser.add_argument('--use-bot-config', action='store_true', 
                       help='Load database settings from bot config')
    
    args = parser.parse_args()
    
    print("🚀 CodeLottery Database Column Migration")
    print("=" * 50)
    
    if args.use_bot_config:
        config = load_bot_config()
        if not config:
            return False
            
        # Use config values
        host = config['host']
        port = config['port']
        user = config['user']
        password = config['password']
        database = config['database']
    else:
        # Use command line arguments
        host = args.host
        port = args.port
        user = args.user
        password = args.password
        database = args.database
    
    # Validate required parameters
    if not user or not database:
        print("❌ Database user and database name are required")
        print("💡 Use --user and --database arguments, or --use-bot-config")
        return False
    
    success = fix_codelottery_database(host, port, user, password, database)
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Migration completed successfully!")
        print("✅ The codelottery_stats command should now work without errors")
    else:
        print("❌ Migration failed!")
        print("💡 Please check the error messages above")
    print("=" * 50)
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)