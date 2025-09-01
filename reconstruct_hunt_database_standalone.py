#!/usr/bin/env python3
"""
Standalone Hunt Database Reconstruction Script / 独立寻宝游戏数据库重构脚本

This is a standalone version that doesn't require the bot dependencies.
It directly connects to MySQL and rebuilds the hunt database structure.

这是一个独立版本，不需要机器人依赖项。
它直接连接到MySQL并重构寻宝游戏数据库结构。

Usage:
    python3 reconstruct_hunt_database_standalone.py --config
    python3 reconstruct_hunt_database_standalone.py --host HOST --user USER --password PASS --database DB

Options:
    --config                    Use configuration from config.json
    --host HOST                 MySQL host
    --user USER                 MySQL username  
    --password PASS             MySQL password
    --database DB               MySQL database name
    --port PORT                 MySQL port (default: 3306)
    --backup                    Create backup before reconstruction
    --force                     Force reconstruction even if tables exist
"""

import sys
import argparse
import json
import os
import datetime
import subprocess

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
    
    print("Could not load database configuration from config files")
    return None

def create_backup(db_config):
    """Create a database backup"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"hunt_database_backup_{timestamp}.sql"
        
        print(f"Creating backup: {backup_file}")
        
        cmd = [
            'mysqldump',
            f'--host={db_config["host"]}',
            f'--port={db_config["port"]}',
            f'--user={db_config["user"]}',
            f'--password={db_config["password"]}',
            '--single-transaction',
            '--routines',
            '--triggers',
            db_config['database'],
            '--tables',
            'hunt', 'equipment', 'equipment_definition', 'car', 'daily_car',
            'assembly_reward', 'reward_config', 'reward_button'
        ]
        
        with open(backup_file, 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
            
        if result.returncode == 0:
            print(f"✓ Backup created: {backup_file}")
            return True
        else:
            print(f"✗ Backup failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Backup failed: {e}")
        return False

def get_database_connection(db_config):
    """Get database connection"""
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
        return connection
        
    except ImportError:
        print("✗ PyMySQL not installed. Install it with: pip install PyMySQL")
        return None
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return None

def drop_hunt_tables(connection):
    """Drop all hunt-related tables"""
    print("\nDropping existing hunt tables...")
    
    try:
        cursor = connection.cursor()
        
        # Drop tables in reverse dependency order
        hunt_tables = [
            'reward_button', 'assembly_reward', 'daily_car', 'equipment',
            'hunt', 'reward_config', 'car', 'equipment_definition'
        ]
        
        for table in hunt_tables:
            print(f"  Dropping table: {table}")
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
        
        connection.commit()
        cursor.close()
        
        print("✓ All hunt tables dropped")
        return True
        
    except Exception as e:
        print(f"✗ Failed to drop tables: {e}")
        return False

def create_hunt_tables(connection):
    """Create all hunt tables with correct structure"""
    print("\nCreating hunt tables...")
    
    try:
        cursor = connection.cursor()
        
        # Table creation SQL statements
        table_sqls = [
            # Equipment Definition table
            """
            CREATE TABLE equipment_definition (
                equipment_id INT PRIMARY KEY,
                equipment_name VARCHAR(100) NOT NULL,
                description TEXT,
                category VARCHAR(20) NOT NULL,
                rarity_weight INT NOT NULL DEFAULT 1
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='装备定义表'
            """,
            
            # Car table
            """
            CREATE TABLE car (
                id INT PRIMARY KEY AUTO_INCREMENT,
                car_name VARCHAR(50) NOT NULL,
                equipment_ids VARCHAR(200) NOT NULL,
                description TEXT
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='汽车配置表'
            """,
            
            # Hunt table
            """
            CREATE TABLE hunt (
                id INT PRIMARY KEY AUTO_INCREMENT,
                tg BIGINT NOT NULL,
                start_time DATETIME NOT NULL,
                end_time DATETIME,
                game_date VARCHAR(10) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                equipment_found INT DEFAULT 0,
                coins_spent INT DEFAULT 0,
                last_hunt_time DATETIME,
                hunt_actions INT DEFAULT 0 COMMENT '寻找装备的次数',
                daily_car_info TEXT COMMENT '缓存的每日汽车信息'
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='车库游戏会话表'
            """,
            
            # Equipment table
            """
            CREATE TABLE equipment (
                id INT PRIMARY KEY AUTO_INCREMENT,
                tg BIGINT NOT NULL,
                equipment_id INT NOT NULL,
                obtained_date VARCHAR(10) NOT NULL,
                obtained_time DATETIME NOT NULL,
                hunt_session_id INT NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='装备表'
            """,
            
            # Daily Car table
            """
            CREATE TABLE daily_car (
                date VARCHAR(10) PRIMARY KEY,
                car_id INT NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='每日汽车表'
            """,
            
            # Assembly Reward table
            """
            CREATE TABLE assembly_reward (
                id INT PRIMARY KEY AUTO_INCREMENT,
                tg BIGINT NOT NULL,
                car_id INT NOT NULL,
                car_name VARCHAR(50) NOT NULL,
                reward_type VARCHAR(20) NOT NULL,
                reward_value VARCHAR(100) NOT NULL,
                reward_description TEXT,
                obtained_date VARCHAR(10) NOT NULL,
                obtained_time DATETIME NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='组装奖励表'
            """,
            
            # Reward Config table
            """
            CREATE TABLE reward_config (
                id INT PRIMARY KEY AUTO_INCREMENT,
                car_id INT NOT NULL UNIQUE,
                reward_type VARCHAR(20) NOT NULL,
                reward_value VARCHAR(100) NOT NULL,
                reward_description TEXT,
                is_active BOOLEAN DEFAULT TRUE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='奖励配置表'
            """,
            
            # Reward Button table
            """
            CREATE TABLE reward_button (
                id INT PRIMARY KEY AUTO_INCREMENT,
                car_id INT NOT NULL,
                button_text VARCHAR(100) NOT NULL,
                button_url VARCHAR(500) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='自定义奖励按钮配置表'
            """
        ]
        
        table_names = [
            'equipment_definition', 'car', 'hunt', 'equipment', 'daily_car',
            'assembly_reward', 'reward_config', 'reward_button'
        ]
        
        for i, sql in enumerate(table_sqls):
            print(f"  Creating table: {table_names[i]}")
            cursor.execute(sql)
        
        connection.commit()
        cursor.close()
        
        print("✓ All hunt tables created")
        return True
        
    except Exception as e:
        print(f"✗ Failed to create tables: {e}")
        return False

def initialize_game_data(connection):
    """Initialize default game data"""
    print("\nInitializing default game data...")
    
    try:
        cursor = connection.cursor()
        
        # Insert equipment definitions
        print("  Inserting equipment definitions...")
        equipment_data = [
            # Purple equipment (extremely rare)
            (1, "赞德福特蓝车漆", "赞德福特蓝M2专属车漆", "purple", 1),
            (2, "曼岛绿车漆", "曼岛绿M3专属车漆", "purple", 1),
            (3, "圣保罗黄车漆", "圣保罗黄M4专属车漆", "purple", 1),
            (4, "风暴灰车漆", "风暴灰M5专属车漆", "purple", 1),
            
            # Gold equipment (high-end components)
            (5, "S58发动机", "高性能S58双涡轮增压发动机", "gold", 3),
            (6, "赤金色轮毂", "限量版赤金色轮毂", "gold", 3),
            (7, "xDrive智能全轮驱动系统", "BMW xDrive智能全轮驱动系统", "gold", 3),
            (8, "碳纤维赛道桶椅", "轻量化碳纤维赛道桶椅", "gold", 3),
            (9, "主动M差速器", "M主动差速器", "gold", 3),
            (10, "V8双涡轮增压发动机", "强劲的V8双涡轮增压发动机", "gold", 3),
            (11, "自适应M运动悬架", "可调节自适应M运动悬架", "gold", 3),
            (12, "碳陶瓷刹车系统", "高性能碳陶瓷刹车系统", "gold", 3),
            (13, "M精英驾驶模式", "M精英驾驶模式系统", "gold", 3),
            (14, "整体主动转向系统", "BMW整体主动转向系统", "gold", 3),
            
            # Green equipment (paint variants)
            (15, "磨砂纯灰车漆", "高档磨砂纯灰车漆", "green", 6),
            (16, "布鲁克林灰车漆", "经典布鲁克林灰车漆", "green", 6),
            (17, "多伦多红车漆", "亮丽多伦多红车漆", "green", 6),
            (18, "海滨湾蓝车漆", "深邃海滨湾蓝车漆", "green", 6),
            
            # Blue equipment (common items)
            (19, "98#汽油", "高品质98号汽油", "blue", 10),
            (20, "玻璃水", "汽车玻璃清洗液", "blue", 10),
            (21, "车钥匙", "汽车遥控钥匙", "blue", 10),
            (22, "漏气的轮胎", "需要修理的轮胎", "blue", 10),
            (23, "空气", "轮胎充气用空气", "blue", 10),
            (24, "空调滤芯", "汽车空调滤芯", "blue", 10),
            (25, "刹车盘", "汽车刹车盘", "blue", 10)
        ]
        
        cursor.executemany(
            "INSERT INTO equipment_definition (equipment_id, equipment_name, description, category, rarity_weight) VALUES (%s, %s, %s, %s, %s)",
            equipment_data
        )
        
        # Insert car configurations
        print("  Inserting car configurations...")
        car_data = [
            ("赞德福特蓝M2", "5,12,6,15,1", "BMW M2 Competition 赞德福特蓝限量版"),
            ("曼岛绿M3", "5,7,8,2,16", "BMW M3 Competition 曼岛绿限量版"),
            ("圣保罗黄M4", "5,9,13,3,17", "BMW M4 Competition 圣保罗黄限量版"),
            ("风暴灰M5", "10,11,14,4,18", "BMW M5 Competition 风暴灰限量版")
        ]
        
        cursor.executemany(
            "INSERT INTO car (car_name, equipment_ids, description) VALUES (%s, %s, %s)",
            car_data
        )
        
        # Insert reward configurations
        print("  Inserting reward configurations...")
        reward_data = [
            (1, "coins", "100", "组装赞德福特蓝M2获得100金币奖励", True),
            (2, "coins", "1916", "组装曼岛绿M3获得1916金币奖励", True),
            (3, "code", "1", "组装圣保罗黄M4获得1个注册码", True),
            (4, "white", "1", "组装风暴灰M5获得1个白名单", True)
        ]
        
        cursor.executemany(
            "INSERT INTO reward_config (car_id, reward_type, reward_value, reward_description, is_active) VALUES (%s, %s, %s, %s, %s)",
            reward_data
        )
        
        # Set today's daily car
        print("  Setting today's daily car...")
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        cursor.execute("INSERT INTO daily_car (date, car_id) VALUES (%s, %s) ON DUPLICATE KEY UPDATE car_id = VALUES(car_id)", (today, 1))
        
        connection.commit()
        cursor.close()
        
        print("✓ Default game data initialized")
        return True
        
    except Exception as e:
        print(f"✗ Failed to initialize game data: {e}")
        return False

def verify_database_structure(connection):
    """Verify database structure"""
    print("\nVerifying database structure...")
    
    try:
        cursor = connection.cursor()
        
        # Check all required tables exist
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = [
            'hunt', 'equipment', 'equipment_definition', 'car', 'daily_car',
            'assembly_reward', 'reward_config', 'reward_button'
        ]
        
        missing_tables = [table for table in required_tables if table not in tables]
        if missing_tables:
            print(f"  ✗ Missing tables: {missing_tables}")
            return False
        
        # Check hunt table has required columns
        cursor.execute("DESCRIBE hunt")
        hunt_columns = [row[0] for row in cursor.fetchall()]
        
        required_hunt_columns = ['id', 'tg', 'start_time', 'game_date', 'is_active', 'hunt_actions', 'daily_car_info']
        missing_hunt_columns = [col for col in required_hunt_columns if col not in hunt_columns]
        
        if missing_hunt_columns:
            print(f"  ✗ Hunt table missing columns: {missing_hunt_columns}")
            return False
        
        # Check data was inserted
        cursor.execute("SELECT COUNT(*) FROM equipment_definition")
        equipment_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM car")
        car_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM reward_config")
        reward_count = cursor.fetchone()[0]
        
        cursor.close()
        
        if equipment_count == 0:
            print("  ✗ No equipment definitions found")
            return False
            
        if car_count == 0:
            print("  ✗ No car configurations found")
            return False
            
        if reward_count == 0:
            print("  ✗ No reward configurations found")
            return False
        
        print(f"  ✓ All tables exist with correct structure")
        print(f"  ✓ Found {equipment_count} equipment definitions")
        print(f"  ✓ Found {car_count} car configurations")
        print(f"  ✓ Found {reward_count} reward configurations")
        
        return True
        
    except Exception as e:
        print(f"✗ Verification failed: {e}")
        return False

def main():
    """Main reconstruction function"""
    parser = argparse.ArgumentParser(description='Standalone hunt database reconstruction')
    parser.add_argument('--config', action='store_true', help='Use configuration from config.json')
    parser.add_argument('--host', help='MySQL host')
    parser.add_argument('--user', help='MySQL username')
    parser.add_argument('--password', help='MySQL password')
    parser.add_argument('--database', help='MySQL database name')
    parser.add_argument('--port', type=int, default=3306, help='MySQL port')
    parser.add_argument('--backup', action='store_true', help='Create backup before reconstruction')
    parser.add_argument('--force', action='store_true', help='Force reconstruction')
    
    args = parser.parse_args()
    
    print("Standalone Hunt Database Reconstruction Script")
    print("=" * 50)
    
    # Get database configuration
    if args.config:
        db_config = load_config_from_file()
        if not db_config:
            return False
    else:
        if not all([args.host, args.user, args.database]):
            print("Error: Must provide --host, --user, --password, --database or use --config")
            return False
        
        db_config = {
            'host': args.host,
            'user': args.user,
            'password': args.password or '',
            'database': args.database,
            'port': args.port
        }
    
    print(f"Database: {db_config['user']}@{db_config['host']}:{db_config['port']}/{db_config['database']}")
    
    # Get database connection
    connection = get_database_connection(db_config)
    if not connection:
        return False
    
    try:
        # Check if tables exist
        cursor = connection.cursor()
        cursor.execute("SHOW TABLES LIKE 'hunt%' OR SHOW TABLES LIKE 'equipment%' OR SHOW TABLES LIKE 'car%'")
        existing_hunt_tables = cursor.fetchall()
        cursor.close()
        
        if existing_hunt_tables and not args.force:
            print(f"\n⚠️  Hunt-related tables already exist: {[row[0] for row in existing_hunt_tables]}")
            response = input("Continue with reconstruction? This will DROP all hunt data! (yes/no): ")
            if response.lower() != 'yes':
                print("Reconstruction cancelled")
                return False
        
        # Create backup if requested
        if args.backup:
            if not create_backup(db_config):
                print("Backup failed - aborting")
                return False
        
        # Start reconstruction
        print(f"\n🔧 Starting hunt database reconstruction...")
        
        if not drop_hunt_tables(connection):
            return False
        
        if not create_hunt_tables(connection):
            return False
        
        if not initialize_game_data(connection):
            return False
        
        if not verify_database_structure(connection):
            return False
        
        print("\n" + "=" * 50)
        print("✅ Hunt database reconstruction completed successfully!")
        print("\n🎮 The hunt game should now be fully functional.")
        print("You can now start the bot and test the /hunt command.")
        
        return True
        
    finally:
        connection.close()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)