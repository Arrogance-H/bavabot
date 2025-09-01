#!/usr/bin/env python3
"""
Hunt Database Fix Launcher / 寻宝游戏数据库修复启动器

This script helps users choose the right method to fix hunt database issues.
该脚本帮助用户选择正确的方法来修复寻宝游戏数据库问题。

Usage: python3 fix_hunt_database.py
"""

import sys
import os
import subprocess

def print_banner():
    """Print banner"""
    print("=" * 60)
    print("🎮 Hunt Database Fix Launcher / 寻宝游戏数据库修复启动器")
    print("=" * 60)
    print()

def check_dependencies():
    """Check if bot dependencies are available"""
    try:
        # Try to import bot modules
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from bot.sql_helper import engine
        from bot import db_host
        print("✓ Bot dependencies available")
        return True
    except ImportError:
        print("✗ Bot dependencies not available")
        return False

def check_pymysql():
    """Check if PyMySQL is available"""
    try:
        import pymysql
        print("✓ PyMySQL available")
        return True
    except ImportError:
        print("✗ PyMySQL not available")
        return False

def get_user_choice():
    """Get user choice for action"""
    print("\n🔍 What would you like to do?")
    print("1. Validate current database structure (recommended first step)")
    print("2. Reconstruct hunt database (full rebuild)")
    print("3. Show help and documentation")
    print("4. Exit")
    
    while True:
        try:
            choice = input("\nEnter your choice (1-4): ").strip()
            if choice in ['1', '2', '3', '4']:
                return int(choice)
            else:
                print("Please enter 1, 2, 3, or 4")
        except KeyboardInterrupt:
            print("\n\nExiting...")
            sys.exit(0)

def run_validation():
    """Run database validation"""
    print("\n🔍 Running database validation...")
    print("-" * 40)
    
    bot_deps = check_dependencies()
    
    if bot_deps:
        # Try with bot dependencies first
        cmd = [sys.executable, "validate_hunt_database.py"]
    else:
        # Fall back to standalone
        print("Using standalone validation...")
        cmd = [sys.executable, "validate_hunt_database.py", "--config"]
    
    try:
        result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
        return result.returncode == 0
    except Exception as e:
        print(f"Error running validation: {e}")
        return False

def run_reconstruction():
    """Run database reconstruction"""
    print("\n🔧 Running database reconstruction...")
    print("-" * 40)
    
    # Ask for backup
    backup = input("Create backup before reconstruction? (Y/n): ").strip().lower()
    create_backup = backup in ['', 'y', 'yes']
    
    # Ask for force
    force = input("Force reconstruction even if tables exist? (y/N): ").strip().lower()
    force_rebuild = force in ['y', 'yes']
    
    bot_deps = check_dependencies()
    
    if bot_deps:
        # Use main reconstruction script
        cmd = [sys.executable, "reconstruct_hunt_database.py"]
        if create_backup:
            cmd.append("--backup")
        if force_rebuild:
            cmd.append("--force")
    else:
        # Use standalone script
        print("Using standalone reconstruction...")
        if not check_pymysql():
            print("\n❌ PyMySQL is required for standalone reconstruction.")
            print("Install it with: pip install PyMySQL")
            return False
        
        cmd = [sys.executable, "reconstruct_hunt_database_standalone.py", "--config"]
        if create_backup:
            cmd.append("--backup")
        if force_rebuild:
            cmd.append("--force")
    
    print(f"\nRunning: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
        return result.returncode == 0
    except Exception as e:
        print(f"Error running reconstruction: {e}")
        return False

def show_help():
    """Show help and documentation"""
    print("\n📚 Hunt Database Fix Documentation")
    print("-" * 40)
    
    print("\n🎯 Purpose:")
    print("This fix resolves the '❌ 数据库已修复，但游戏启动仍失败' error")
    print("by completely reconstructing the hunt database structure.")
    
    print("\n🛠️ Available Scripts:")
    print("1. validate_hunt_database.py - Check database structure")
    print("2. reconstruct_hunt_database.py - Full reconstruction (with bot deps)")
    print("3. reconstruct_hunt_database_standalone.py - Standalone reconstruction")
    
    print("\n📖 Documentation:")
    print("- HUNT_RECONSTRUCTION_README.md - Complete guide")
    print("- MIGRATION_README.md - Migration information")
    
    print("\n⚙️ Manual Usage:")
    print("# Validation")
    print("python3 validate_hunt_database.py --config")
    print()
    print("# Reconstruction with backup")
    print("python3 reconstruct_hunt_database.py --backup")
    print()
    print("# Standalone reconstruction")
    print("python3 reconstruct_hunt_database_standalone.py --config --backup")
    
    print("\n🔧 Requirements:")
    print("- MySQL database access")
    print("- PyMySQL (for standalone version)")
    print("- Bot dependencies (for integrated version)")
    
    print("\n⚠️  Important Notes:")
    print("- Reconstruction will DELETE all existing hunt data")
    print("- Always create a backup before reconstruction")
    print("- The process recreates 8 database tables with default data")

def main():
    """Main function"""
    print_banner()
    
    print("🔍 Checking environment...")
    bot_deps = check_dependencies()
    pymysql_available = check_pymysql()
    
    if not bot_deps and not pymysql_available:
        print("\n❌ Neither bot dependencies nor PyMySQL are available.")
        print("Install PyMySQL with: pip install PyMySQL")
        print("Or ensure bot dependencies are properly configured.")
        return False
    
    while True:
        choice = get_user_choice()
        
        if choice == 1:
            # Validate
            success = run_validation()
            if success:
                print("\n✅ Validation completed successfully!")
                print("Check the output above for any issues.")
            else:
                print("\n❌ Validation found issues.")
                print("Consider running reconstruction (option 2).")
        
        elif choice == 2:
            # Reconstruct
            print("\n⚠️  WARNING: This will DELETE all existing hunt data!")
            confirm = input("Are you sure you want to continue? (yes/no): ").strip().lower()
            
            if confirm == 'yes':
                success = run_reconstruction()
                if success:
                    print("\n✅ Reconstruction completed successfully!")
                    print("The hunt game should now work correctly.")
                    print("Test with: /hunt command in Telegram")
                else:
                    print("\n❌ Reconstruction failed.")
                    print("Check the error messages above for details.")
            else:
                print("Reconstruction cancelled.")
        
        elif choice == 3:
            # Show help
            show_help()
        
        elif choice == 4:
            # Exit
            break
        
        # Ask if user wants to continue
        print("\n" + "-" * 40)
        continue_choice = input("Return to main menu? (Y/n): ").strip().lower()
        if continue_choice in ['n', 'no']:
            break
    
    print("\n👋 Thank you for using the hunt database fix launcher!")
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)