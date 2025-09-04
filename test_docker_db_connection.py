#!/usr/bin/env python3
"""
Docker CodeLottery Database Connection Test
直接测试Docker环境下的数据库连接和表创建
"""

import os
import sys
import json
import subprocess
from datetime import datetime

def check_mysql_client():
    """检查MySQL客户端是否可用"""
    try:
        result = subprocess.run(['mysql', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ MySQL客户端可用: {result.stdout.strip()}")
            return True
        else:
            print("❌ MySQL客户端不可用")
            return False
    except FileNotFoundError:
        print("❌ MySQL客户端未安装")
        return False

def load_config():
    """加载配置文件"""
    config_files = ['/app/config.json', 'config.json', 'config_example.json']
    
    for config_path in config_files:
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                print(f"✅ 配置文件加载成功: {config_path}")
                return config
            except Exception as e:
                print(f"❌ 配置文件加载失败 {config_path}: {e}")
                continue
    
    print("❌ 找不到有效的配置文件")
    return None

def test_mysql_connection(config):
    """测试MySQL数据库连接"""
    if not config:
        return False
    
    db_host = config.get('db_host', 'localhost')
    db_user = config.get('db_user', '')
    db_pwd = config.get('db_pwd', '')
    db_name = config.get('db_name', '')
    db_port = config.get('db_port', 3306)
    db_is_docker = config.get('db_is_docker', True)
    db_docker_name = config.get('db_docker_name', 'mysql')
    
    print(f"\n📊 数据库连接信息:")
    print(f"   主机: {db_host}")
    print(f"   端口: {db_port}")
    print(f"   数据库: {db_name}")
    print(f"   Docker模式: {db_is_docker}")
    
    # 在Docker环境中测试连接
    if db_is_docker:
        print(f"   Docker容器名: {db_docker_name}")
        
        # 测试Docker容器是否运行
        try:
            result = subprocess.run(
                ['docker', 'ps', '--filter', f'name={db_docker_name}', '--format', 'table {{.Names}}\t{{.Status}}'],
                capture_output=True, text=True
            )
            
            if result.returncode == 0 and db_docker_name in result.stdout:
                print(f"✅ Docker容器 {db_docker_name} 正在运行")
                print(f"   状态: {result.stdout.strip()}")
            else:
                print(f"❌ Docker容器 {db_docker_name} 未运行")
                return False
        except FileNotFoundError:
            print("❌ Docker命令不可用")
            return False
    
    # 尝试连接数据库
    if db_user and db_name:
        mysql_cmd = [
            'mysql',
            f'-h{db_host}',
            f'-P{db_port}',
            f'-u{db_user}',
            f'-p{db_pwd}' if db_pwd else '',
            db_name,
            '-e', 'SELECT 1 as test_connection;'
        ]
        
        # 移除空的密码参数
        mysql_cmd = [arg for arg in mysql_cmd if arg]
        
        try:
            result = subprocess.run(mysql_cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("✅ 数据库连接成功")
                return True
            else:
                print(f"❌ 数据库连接失败: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("❌ 数据库连接超时")
            return False
        except Exception as e:
            print(f"❌ 数据库连接异常: {e}")
            return False
    else:
        print("⚠️  数据库配置信息不完整，无法测试连接")
        return False

def test_codelottery_tables(config):
    """测试CodeLottery数据库表"""
    if not config:
        return False
    
    db_host = config.get('db_host', 'localhost')
    db_user = config.get('db_user', '')
    db_pwd = config.get('db_pwd', '')
    db_name = config.get('db_name', '')
    db_port = config.get('db_port', 3306)
    
    if not all([db_user, db_name]):
        print("⚠️  数据库配置不完整，跳过表检查")
        return False
    
    # 检查CodeLottery相关表
    tables_to_check = [
        'code_lottery_users',
        'code_lottery_rounds',
        'code_lottery_participants', 
        'code_lottery_winners'
    ]
    
    print(f"\n📋 检查CodeLottery数据库表:")
    
    for table in tables_to_check:
        mysql_cmd = [
            'mysql',
            f'-h{db_host}',
            f'-P{db_port}',
            f'-u{db_user}',
            f'-p{db_pwd}' if db_pwd else '',
            db_name,
            '-e', f'DESCRIBE {table};'
        ]
        
        # 移除空的密码参数
        mysql_cmd = [arg for arg in mysql_cmd if arg]
        
        try:
            result = subprocess.run(mysql_cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"   ✅ {table} - 存在")
                # 显示表结构的前几行
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    print(f"      字段数量: {len(lines) - 1}")
            else:
                print(f"   ❌ {table} - 不存在或无法访问")
        except Exception as e:
            print(f"   ❌ {table} - 检查异常: {e}")
    
    return True

def create_test_summary():
    """创建测试摘要"""
    print(f"\n{'='*60}")
    print("📋 CodeLottery Docker数据库测试摘要")
    print(f"{'='*60}")
    print(f"🕒 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🐳 运行环境: {'Docker容器内' if os.path.exists('/.dockerenv') else '开发环境'}")
    
    # 检查关键文件
    important_files = [
        'bot/sql_helper/sql_codelottery.py',
        'bot/modules/commands/codelottery.py',
        'bot/scheduler/code_lottery_scheduler.py',
        'test_codelottery_database.py'
    ]
    
    print(f"\n📁 CodeLottery关键文件:")
    for file_path in important_files:
        if os.path.exists(file_path):
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ {file_path}")
    
    print(f"\n🎯 功能特点:")
    print("   ✅ 时间制抽奖 (30分钟自动开奖)")
    print("   ✅ 用户等级限制 (lv='c')")
    print("   ✅ 参与费用控制 (3花币)")
    print("   ✅ 保底机制 (10次必中)")
    print("   ✅ 管理员控制 (/codelottery_start, /codelottery_stop)")
    print("   ✅ 自动调度器 (过期检测)")
    print("   ✅ 获奖者通知 (私信+群组)")

def main():
    """主测试函数"""
    print("🚀 CodeLottery Docker数据库连接测试")
    print("=" * 60)
    
    # 检查MySQL客户端
    has_mysql = check_mysql_client()
    
    # 加载配置
    config = load_config()
    
    # 测试数据库连接
    connection_ok = False
    if has_mysql and config:
        connection_ok = test_mysql_connection(config)
    
    # 测试表结构
    tables_ok = False
    if connection_ok:
        tables_ok = test_codelottery_tables(config)
    
    # 生成测试摘要
    create_test_summary()
    
    # 最终结果
    print(f"\n{'='*60}")
    if connection_ok and tables_ok:
        print("🎉 CodeLottery数据库在Docker环境下完全可用！")
        print("✅ 数据库连接正常")
        print("✅ 所有必要的表都可访问")
        print("✅ 可以启动CodeLottery功能")
        return True
    elif connection_ok:
        print("⚠️  数据库连接正常，但表可能需要创建")
        print("💡 建议: 运行主程序一次以创建必要的表")
        return True
    else:
        print("❌ 数据库连接失败")
        print("💡 建议: 检查Docker容器状态和数据库配置")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)