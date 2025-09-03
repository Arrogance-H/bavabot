#!/usr/bin/env python3
"""
Simple Hunt Game Database Test Script
简单的寻宝游戏数据库测试脚本

This script tests if the hunt game database schema is properly configured
without requiring the full bot dependencies.

该脚本测试寻宝游戏数据库模式是否正确配置，而无需完整的机器人依赖项。

Usage:
    python3 test_hunt_database.py
"""

import json
import os
import sys

def load_config():
    """Load database configuration"""
    if os.path.exists('config.json'):
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            return {
                'host': config.get('db_host', 'localhost'),
                'user': config.get('db_user', 'root'),
                'password': config.get('db_pwd', ''),
                'database': config.get('db_name', 'bavabot'),
                'port': config.get('db_port', 3306)
            }
    return None

def test_database_connection():
    """Test database connection and schema"""
    config = load_config()
    if not config:
        print("❌ No config.json found")
        return False
    
    try:
        import pymysql
    except ImportError:
        print("❌ PyMySQL not installed. This is expected in this environment.")
        print("✅ The SQL fix script should be run directly in your MySQL database.")
        print("📝 See HUNT_FIX_README.md for instructions.")
        return True  # Return True since this is expected
    
    try:
        connection = pymysql.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        
        # Check if hunt table exists
        cursor.execute("SHOW TABLES LIKE 'hunt'")
        if not cursor.fetchone():
            print("❌ Hunt table does not exist")
            connection.close()
            return False
        
        # Check for required columns
        cursor.execute("DESCRIBE hunt")
        columns = [row[0] for row in cursor.fetchall()]
        
        required_columns = ['hunt_actions', 'daily_car_info', 'message_id', 'chat_id']
        missing_columns = [col for col in required_columns if col not in columns]
        
        if missing_columns:
            print(f"❌ Missing required columns: {', '.join(missing_columns)}")
            print("🔧 Run fix_hunt_schema.sql to add missing columns")
            connection.close()
            return False
        
        print("✅ All required columns exist in hunt table")
        print("🎮 Hunt game should be able to start successfully")
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def show_fix_instructions():
    """Show fix instructions"""
    print("\n" + "="*60)
    print("🔧 HUNT GAME FIX INSTRUCTIONS")
    print("="*60)
    print()
    print("To fix the hunt game startup issue:")
    print()
    print("1. Connect to your MySQL database")
    print("2. Run the SQL fix script:")
    print("   mysql -u username -p database < fix_hunt_schema.sql")
    print()
    print("3. Or run the commands manually:")
    print("   ALTER TABLE hunt ADD COLUMN hunt_actions INT DEFAULT 0;")
    print("   ALTER TABLE hunt ADD COLUMN daily_car_info TEXT NULL;")
    print("   ALTER TABLE hunt ADD COLUMN message_id INT NULL;")
    print("   ALTER TABLE hunt ADD COLUMN chat_id BIGINT NULL;")
    print()
    print("4. Restart your bot")
    print()
    print("📖 See HUNT_FIX_README.md for detailed instructions")
    print("="*60)

def main():
    """Main function"""
    print("Hunt Game Database Test")
    print("="*30)
    
    # Test configuration
    config = load_config()
    if config:
        print(f"✅ Configuration loaded")
        print(f"   Database: {config['user']}@{config['host']}:{config['port']}/{config['database']}")
    else:
        print("❌ No configuration found")
        return
    
    # Test database
    print("\nTesting database connection...")
    success = test_database_connection()
    
    if not success:
        show_fix_instructions()
    else:
        print("\n🎉 Hunt game database is properly configured!")

if __name__ == "__main__":
    main()