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
    print("1. Use SQL script fix (recommended - no dependencies needed)")
    print("2. Validate current database structure")
    print("3. Reconstruct hunt database (requires PyMySQL)")
    print("4. Show help and documentation")
    print("5. Exit")
    
    while True:
        try:
            choice = input("\nEnter your choice (1-5): ").strip()
            if choice in ['1', '2', '3', '4', '5']:
                return int(choice)
            else:
                print("Please enter 1, 2, 3, 4, or 5")
        except KeyboardInterrupt:
            print("\n\nExiting...")
            sys.exit(0)

def show_sql_fix_instructions():
    """Show SQL script fix instructions"""
    print("\n🔧 SQL Script Fix (Recommended)")
    print("-" * 40)
    
    print("This is the easiest and most reliable method to fix the hunt database.")
    print("It doesn't require Python dependencies and works directly with your MySQL database.")
    
    print("\n📋 Instructions:")
    print("1. Connect to your MySQL database using your preferred client")
    print("   (MySQL Workbench, phpMyAdmin, command line, etc.)")
    
    print("\n2. Open and run the SQL script file: fix_hunt_schema.sql")
    print("   Or run this command if using MySQL command line:")
    print("   mysql -u your_username -p your_database < fix_hunt_schema.sql")
    
    print("\n3. The script will automatically:")
    print("   ✓ Add missing hunt_actions column")
    print("   ✓ Add missing daily_car_info column") 
    print("   ✓ Add missing message_id column")
    print("   ✓ Add missing chat_id column")
    print("   ✓ Skip columns that already exist")
    print("   ✓ Show verification results")
    
    print("\n4. Restart your bot after running the script")
    
    print("\n📄 SQL Script Location:")
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fix_hunt_schema.sql")
    print(f"   {script_path}")
    
    if os.path.exists(script_path):
        print("   ✓ SQL script file found")
        
        try:
            show_content = input("\n🔍 Would you like to see the SQL script content? (y/N): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            show_content = 'n'
            print("n")  # Show what was selected
            
        if show_content in ['y', 'yes']:
            print("\n" + "=" * 60)
            print("SQL SCRIPT CONTENT:")
            print("=" * 60)
            try:
                with open(script_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    print(content)
            except Exception as e:
                print(f"Error reading script file: {e}")
            print("=" * 60)
    else:
        print("   ❌ SQL script file not found")
        print(f"   Please ensure fix_hunt_schema.sql is in the same directory as this script")
    
    print("\n💡 Why this method is recommended:")
    print("   • No Python dependencies required")
    print("   • Works with any MySQL client")
    print("   • Safe - only adds missing columns")
    print("   • Fast and reliable")
    print("   • Provides immediate feedback")
    
    print("\n⚠️  Note:")
    print("Make sure to change 'bavabot' in the script to your actual database name")
    print("if your database has a different name.")

def run_validation():
    """Run database validation"""
    print("\n🔍 Running database validation...")
    print("-" * 40)
    
    bot_deps = check_dependencies()
    pymysql_available = check_pymysql()
    
    if not bot_deps and not pymysql_available:
        print("❌ Cannot run validation: no dependencies available")
        print("\nAlternative validation method:")
        print("1. Use the SQL script fix (option 1) - it includes verification")
        print("2. Install PyMySQL: pip install PyMySQL")
        print("3. Then rerun this validation")
        return False
    
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
    
    # Check dependencies first
    bot_deps = check_dependencies()
    pymysql_available = check_pymysql()
    
    if not bot_deps and not pymysql_available:
        print("❌ Cannot run reconstruction: PyMySQL is required")
        print("\nOptions:")
        print("1. Install PyMySQL: pip install PyMySQL")
        print("2. Use the SQL script fix instead (option 1) - recommended")
        print("3. Check the help documentation (option 4)")
        return False
    
    # Ask for backup
    backup = input("Create backup before reconstruction? (Y/n): ").strip().lower()
    create_backup = backup in ['', 'y', 'yes']
    
    # Ask for force
    force = input("Force reconstruction even if tables exist? (y/N): ").strip().lower()
    force_rebuild = force in ['y', 'yes']
    
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
    print("This tool helps fix the hunt game database issues including:")
    print("• ✗ PyMySQL not installed errors")  
    print("• Missing database columns (hunt_actions, daily_car_info, etc.)")
    print("• Database structure incompatibility with hunt.py")
    
    print("\n🛠️ Available Methods (in order of recommendation):")
    print("\n1. 🔧 SQL Script Fix (RECOMMENDED)")
    print("   • No Python dependencies needed")
    print("   • Works with any MySQL client")
    print("   • File: fix_hunt_schema.sql")
    print("   • Safe and fast")
    
    print("\n2. 🔍 Database Validation")
    print("   • Checks current database structure")
    print("   • Requires PyMySQL or bot dependencies")
    print("   • File: validate_hunt_database.py")
    
    print("\n3. 🏗️ Full Database Reconstruction")
    print("   • Complete rebuild of hunt tables")
    print("   • Requires PyMySQL")
    print("   • Files: reconstruct_hunt_database*.py")
    print("   • ⚠️ DELETES existing hunt data")
    
    print("\n📖 Documentation Files:")
    print("• HUNT_FIX_README.md - Quick fix guide")
    print("• HUNT_RECONSTRUCTION_README.md - Complete reconstruction guide")
    
    print("\n⚙️ Manual Commands:")
    print("# Quick SQL fix (recommended)")
    print("mysql -u username -p database_name < fix_hunt_schema.sql")
    print()
    print("# With PyMySQL installed:")
    print("python3 validate_hunt_database.py --config")
    print("python3 reconstruct_hunt_database_standalone.py --config --backup")
    
    print("\n🔧 Troubleshooting:")
    print("• If PyMySQL not installed → Use SQL script method")
    print("• If SQL script doesn't work → Install PyMySQL and use validation")
    print("• If validation fails → Use reconstruction (with backup)")
    print("• If all methods fail → Check database permissions and connectivity")
    
    print("\n📋 Quick Start for Most Users:")
    print("1. Connect to your MySQL database")
    print("2. Run the fix_hunt_schema.sql script")
    print("3. Restart your bot")
    print("4. Test with /hunt command")
    
    print("\n💡 About PyMySQL Dependency:")
    print("PyMySQL is only needed for Python-based validation and reconstruction.")
    print("The SQL script method works without any Python dependencies.")
    print("If you see 'PyMySQL not installed' - just use the SQL script instead!")

def main():
    """Main function"""
    print_banner()
    
    print("🔍 Checking environment...")
    bot_deps = check_dependencies()
    pymysql_available = check_pymysql()
    
    if not bot_deps and not pymysql_available:
        print("\n⚠️  Python dependencies not available:")
        print("• Bot dependencies: Not available") 
        print("• PyMySQL: Not installed")
        print("\n💡 Don't worry! You can still fix the hunt database using the SQL script method.")
        print("This is actually the easiest and most reliable way to fix the issue.")
        print("\n🔧 Recommended action: Choose option 1 (SQL script fix)")
    else:
        print(f"\n✅ Environment check:")
        print(f"• Bot dependencies: {'✓' if bot_deps else '✗'}")
        print(f"• PyMySQL: {'✓' if pymysql_available else '✗'}")
    
    while True:
        choice = get_user_choice()
        
        if choice == 1:
            # SQL Script Fix
            show_sql_fix_instructions()
        
        elif choice == 2:
            # Validate
            success = run_validation()
            if success:
                print("\n✅ Validation completed successfully!")
                print("Check the output above for any issues.")
            else:
                print("\n❌ Validation found issues or couldn't run.")
                print("Consider using the SQL script fix (option 1).")
        
        elif choice == 3:
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
                    print("Consider using the SQL script fix (option 1) instead.")
            else:
                print("Reconstruction cancelled.")
        
        elif choice == 4:
            # Show help
            show_help()
        
        elif choice == 5:
            # Exit
            break
        
        # Ask if user wants to continue
        print("\n" + "-" * 40)
        try:
            continue_choice = input("Return to main menu? (Y/n): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            continue_choice = 'n'
            print("n")  # Show what was selected
            
        if continue_choice in ['n', 'no']:
            break
    
    print("\n👋 Thank you for using the hunt database fix launcher!")
    print("💡 Remember: If you used the SQL script, restart your bot to apply changes.")
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)