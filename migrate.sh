#!/bin/bash

# 数据库迁移助手脚本
# Database Migration Helper Script

echo "==================================================="
echo "BavaBot Hunt Table Migration Helper"
echo "==================================================="
echo

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed or not in PATH"
    exit 1
fi

# 检查是否在正确的目录
if [ ! -f "migrate_hunt_table.py" ] || [ ! -f "migrate_hunt_table_standalone.py" ]; then
    echo "❌ Migration scripts not found. Please run this script from the bavabot directory."
    exit 1
fi

echo "🔍 Checking migration scripts..."
echo "✅ Found migration scripts"
echo

# 尝试运行主迁移脚本
echo "🚀 Attempting to run main migration script..."
python3 migrate_hunt_table.py
migration_result=$?

if [ $migration_result -eq 0 ]; then
    echo
    echo "🎉 Migration completed successfully!"
    echo "✅ Your hunt table should now have the required columns."
    echo "✅ The hunt_actions column error should be resolved."
else
    echo
    echo "⚠️  Main migration script failed. Let's try alternative methods..."
    echo
    
    # 询问用户是否要尝试独立脚本
    read -p "Do you want to try the standalone migration script? (y/n): " try_standalone
    
    if [[ $try_standalone =~ ^[Yy] ]]; then
        echo
        echo "📋 Please provide your database connection details:"
        read -p "Database host (default: localhost): " db_host
        db_host=${db_host:-localhost}
        
        read -p "Database user (default: root): " db_user
        db_user=${db_user:-root}
        
        read -s -p "Database password: " db_password
        echo
        
        read -p "Database name (default: bavabot): " db_name
        db_name=${db_name:-bavabot}
        
        read -p "Database port (default: 3306): " db_port
        db_port=${db_port:-3306}
        
        echo
        echo "🔄 Running standalone migration script..."
        python3 migrate_hunt_table_standalone.py \
            --host "$db_host" \
            --user "$db_user" \
            --password "$db_password" \
            --database "$db_name" \
            --port "$db_port"
        
        standalone_result=$?
        
        if [ $standalone_result -eq 0 ]; then
            echo
            echo "🎉 Standalone migration completed successfully!"
        else
            echo
            echo "❌ Standalone migration also failed."
            echo
            echo "📋 Manual options:"
            echo "1. Check your database connection parameters"
            echo "2. Install required dependencies: pip install PyMySQL SQLAlchemy"
            echo "3. Run SQL migration manually:"
            echo "   mysql -u $db_user -p $db_name < migrate_hunt_table.sql"
            echo
            echo "📖 For detailed instructions, see MIGRATION_README.md"
        fi
    else
        echo
        echo "📋 Manual migration options:"
        echo "1. Fix dependency issues and run: python3 migrate_hunt_table.py"
        echo "2. Run SQL migration manually: mysql -u username -p database < migrate_hunt_table.sql"
        echo "3. Check MIGRATION_README.md for detailed instructions"
    fi
fi

echo
echo "==================================================="
echo "Migration process completed."
echo "==================================================="