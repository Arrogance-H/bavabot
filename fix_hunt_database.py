#!/usr/bin/env python3
"""
Hunt Database Auto-Fix Tool / 寻宝游戏数据库自动修复工具

This script automatically detects and fixes hunt database issues in Docker environment.
该脚本自动检测并修复Docker环境中的寻宝游戏数据库问题。

Usage: python3 fix_hunt_database.py
"""

import sys
import os
import datetime

def print_banner():
    """Print banner"""
    print("=" * 60)
    print("🎮 Hunt Database Auto-Fix Tool / 寻宝游戏数据库自动修复工具")
    print("=" * 60)
    print()

def check_bot_environment():
    """检查bot运行环境"""
    print("🔍 检测运行环境...")
    
    # 检查是否在Docker环境中
    is_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_MODE') == '1'
    if is_docker:
        print("✅ 检测到Docker环境")
    else:
        print("💡 检测到非Docker环境")
    
    # 检查PyMySQL是否可用
    try:
        import pymysql
        print("✅ PyMySQL可用")
        pymysql_available = True
    except ImportError:
        print("❌ PyMySQL不可用")
        pymysql_available = False
    
    return is_docker, pymysql_available

def check_bot_dependencies():
    """检查bot依赖是否可用"""
    try:
        # 添加bot目录到路径
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from bot.sql_helper import engine
        from bot import LOGGER
        print("✅ Bot数据库引擎可用")
        return True, engine, LOGGER
    except ImportError as e:
        print(f"❌ Bot依赖不可用: {e}")
        return False, None, None

def automatic_database_fix():
    """自动修复数据库结构"""
    print("\n🔧 开始自动数据库修复...")
    print("-" * 40)
    
    # 检查bot依赖
    bot_available, engine, LOGGER = check_bot_dependencies()
    
    if not bot_available:
        print("❌ 无法访问bot数据库引擎，自动修复失败")
        return False
    
    try:
        # 导入hunt数据库修复函数
        from bot.sql_helper.sql_hunt import sql_check_and_fix_hunt_table
        
        print("🔍 检查hunt表结构...")
        fix_result = sql_check_and_fix_hunt_table()
        
        if fix_result:
            print("✅ 数据库结构检查和修复完成！")
            print("\n🎉 自动修复成功！")
            print("📝 建议重启bot以确保所有更改生效")
            return True
        else:
            print("❌ 数据库结构修复失败")
            return False
            
    except Exception as e:
        print(f"❌ 自动修复过程中出现错误: {e}")
        return False

def validate_database_structure():
    """验证数据库结构"""
    print("\n🔍 验证数据库结构...")
    print("-" * 40)
    
    # 检查bot依赖
    bot_available, engine, LOGGER = check_bot_dependencies()
    
    if not bot_available:
        print("❌ 无法访问bot数据库引擎")
        return False
    
    try:
        from sqlalchemy import inspect
        inspector = inspect(engine)
        
        # 检查hunt表是否存在
        if 'hunt' not in inspector.get_table_names():
            print("❌ hunt表不存在")
            return False
        
        print("✅ hunt表存在")
        
        # 检查必要的列
        columns = inspector.get_columns('hunt')
        column_names = [col['name'] for col in columns]
        
        required_columns = ['hunt_actions', 'daily_car_info', 'message_id', 'chat_id']
        missing_columns = []
        
        print("\n📋 数据库列检查结果:")
        for col_name in required_columns:
            if col_name in column_names:
                print(f"✅ {col_name} - 存在")
            else:
                print(f"❌ {col_name} - 缺失")
                missing_columns.append(col_name)
        
        if missing_columns:
            print(f"\n⚠️ 发现{len(missing_columns)}个缺失的列: {missing_columns}")
            print("💡 建议运行自动修复功能")
            return False
        else:
            print("\n✅ 所有必要的列都存在")
            return True
            
    except Exception as e:
        print(f"❌ 数据库验证过程中出现错误: {e}")
        return False

def test_hunt_game_startup():
    """测试hunt游戏启动功能"""
    print("\n🎮 测试hunt游戏启动...")
    print("-" * 40)
    
    # 检查bot依赖
    bot_available, engine, LOGGER = check_bot_dependencies()
    
    if not bot_available:
        print("❌ 无法访问bot数据库引擎")
        return False
    
    try:
        from bot.sql_helper.sql_hunt import sql_check_and_fix_hunt_table
        
        # 测试表结构检查
        check_result = sql_check_and_fix_hunt_table()
        
        if check_result:
            print("✅ Hunt表结构检查通过")
            print("✅ Hunt游戏应该可以正常启动")
            return True
        else:
            print("❌ Hunt表结构检查失败")
            print("💡 建议先运行自动修复功能")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        return False

def show_help():
    """显示帮助信息"""
    print("\n📚 Hunt Database Auto-Fix 帮助文档")
    print("-" * 40)
    
    print("\n🎯 工具用途:")
    print("• 自动检测和修复hunt游戏数据库结构问题")
    print("• 适用于Docker环境，无需手动执行SQL脚本")  
    print("• 解决hunt游戏启动时的数据库错误")
    
    print("\n🛠️ 功能说明:")
    print("\n1. 🔧 自动数据库修复")
    print("   • 自动检查hunt表结构")
    print("   • 自动添加缺失的数据库列")
    print("   • 无需手动干预，适合Docker环境")
    
    print("\n2. 🔍 数据库结构验证")
    print("   • 检查hunt表是否存在")
    print("   • 验证所有必要列是否存在")
    print("   • 提供详细的检查报告")
    
    print("\n3. 🎮 Hunt游戏启动测试")
    print("   • 测试hunt游戏是否可以正常启动")
    print("   • 验证数据库修复效果")
    
    print("\n🔧 常见问题解决:")
    print("• 如果遇到'PyMySQL not installed'错误 → 运行自动修复")
    print("• 如果hunt游戏无法启动 → 先验证数据库，再运行修复")
    print("• 如果修复失败 → 检查数据库连接和权限")
    
    print("\n💡 Docker环境说明:")
    print("• 本工具专为Docker环境设计")
    print("• 自动使用bot的数据库连接")
    print("• 无需手动执行SQL脚本")
    print("• 修复后建议重启bot容器")
    
    print("\n📝 使用建议:")
    print("1. 首次使用建议按顺序运行：验证 → 修复 → 测试")
    print("2. 定期运行验证功能确保数据库结构正常")
    print("3. 如果遇到问题，查看详细错误信息并联系开发者")

def get_user_choice():
    """获取用户选择"""
    print("\n🔍 请选择操作:")
    print("1. 🔧 自动修复数据库结构 (推荐)")
    print("2. 🔍 验证数据库结构") 
    print("3. 🎮 测试hunt游戏启动")
    print("4. 📚 显示帮助文档")
    print("5. ❌ 退出")
    
    while True:
        try:
            choice = input("\n请输入选择 (1-5): ").strip()
            if choice in ['1', '2', '3', '4', '5']:
                return int(choice)
            else:
                print("请输入1, 2, 3, 4, 或 5")
        except (KeyboardInterrupt, EOFError):
            print("\n\n👋 退出...")
            sys.exit(0)

def main():
    """主函数"""
    print_banner()
    
    # 检查环境
    is_docker, pymysql_available = check_bot_environment()
    
    if is_docker:
        print("\n🐳 Docker环境检测到 - 使用自动修复模式")
    
    if not pymysql_available:
        print("\n⚠️ PyMySQL不可用，但不用担心！")
        print("💡 本工具可以直接使用bot的数据库连接进行自动修复")
    
    print("\n" + "=" * 60)
    
    while True:
        choice = get_user_choice()
        
        if choice == 1:
            # 自动修复数据库结构
            success = automatic_database_fix()
            if success:
                print("\n🎉 修复完成！建议重启bot以确保更改生效")
            else:
                print("\n❌ 修复失败，请检查错误信息或联系开发者")
        
        elif choice == 2:
            # 验证数据库结构
            success = validate_database_structure()
            if success:
                print("\n✅ 数据库结构验证通过！")
            else:
                print("\n❌ 数据库结构需要修复，建议运行选项1")
        
        elif choice == 3:
            # 测试hunt游戏启动
            success = test_hunt_game_startup()
            if success:
                print("\n✅ Hunt游戏应该可以正常启动！")
            else:
                print("\n❌ Hunt游戏启动可能有问题，建议先运行修复")
        
        elif choice == 4:
            # 显示帮助
            show_help()
        
        elif choice == 5:
            # 退出
            break
        
        # 询问是否继续
        print("\n" + "-" * 40)
        try:
            continue_choice = input("返回主菜单? (Y/n): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            continue_choice = 'n'
            print("n")
            
        if continue_choice in ['n', 'no']:
            break
    
    print("\n👋 感谢使用hunt数据库自动修复工具！")
    print("💡 如果修复了数据库，请重启bot以确保更改生效")
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 再见！")
        sys.exit(0)