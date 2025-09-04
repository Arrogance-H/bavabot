#!/usr/bin/env python3
"""
CodeLottery Database Test Script
测试抽奖系统数据库功能
"""

import sys
import os
import random

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# 设置环境变量以避免缺少配置文件的错误
os.environ.setdefault('CONFIG_FILE', 'config_example.json')

try:
    from bot.sql_helper.sql_codelottery import (
        sql_get_codelottery_user,
        sql_create_codelottery_user,
        sql_get_active_lottery_round,
        sql_create_lottery_round,
        sql_join_lottery_round,
        sql_get_lottery_participants,
        sql_complete_lottery_round,
        sql_get_lottery_statistics
    )
    print("✅ 成功导入 CodeLottery 数据库模块")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保项目依赖已正确安装")
    sys.exit(1)


def test_codelottery_system():
    """测试完整的抽奖系统流程"""
    print("\n🎲 开始测试 CodeLottery 系统...")
    
    # 测试用户ID列表
    test_users = [12345, 23456, 34567, 45678, 56789]
    test_nicknames = ["Alice", "Bob", "Charlie", "David", "Eve"]
    
    print("\n1. 测试创建用户记录...")
    for user_id in test_users:
        user = sql_create_codelottery_user(user_id)
        if user:
            print(f"✅ 创建用户 {user_id} 成功")
        else:
            print(f"❌ 创建用户 {user_id} 失败")
    
    print("\n2. 测试创建抽奖轮次...")
    round_obj = sql_create_lottery_round(
        round_number=1,
        lottery_name="ME注册资格测试",
        max_participants=3,
        entry_fee=3,
        winner_count=1,
        created_by=999999
    )
    
    if round_obj:
        print(f"✅ 创建抽奖轮次成功，ID: {round_obj.id}")
        round_id = round_obj.id
    else:
        print("❌ 创建抽奖轮次失败")
        return
    
    print("\n3. 测试用户参与抽奖...")
    participants = []
    for i, (user_id, nickname) in enumerate(zip(test_users[:3], test_nicknames[:3])):
        participant, msg = sql_join_lottery_round(round_id, user_id, nickname)
        if participant:
            print(f"✅ 用户 {nickname}({user_id}) 参与成功")
            participants.append({'tg': user_id, 'nickname': nickname})
        else:
            print(f"❌ 用户 {nickname}({user_id}) 参与失败: {msg}")
    
    print("\n4. 测试获取参与者列表...")
    participants_list = sql_get_lottery_participants(round_id)
    print(f"✅ 当前参与者数量: {len(participants_list)}")
    for p in participants_list:
        print(f"   - {p.nickname}({p.tg})")
    
    print("\n5. 测试开奖...")
    if participants:
        # 随机选择一个获奖者
        winner = random.choice(participants)
        winners = [winner]
        
        success, msg = sql_complete_lottery_round(round_id, winners)
        if success:
            print(f"✅ 开奖成功: {winner['nickname']}({winner['tg']}) 获奖")
        else:
            print(f"❌ 开奖失败: {msg}")
    
    print("\n6. 测试统计信息...")
    stats = sql_get_lottery_statistics()
    if stats:
        print(f"✅ 统计信息获取成功:")
        print(f"   - 总用户数: {stats['total_users']}")
        print(f"   - 总轮次数: {stats['total_rounds']}")
        print(f"   - 总参与次数: {stats['total_participations']}")
        print(f"   - 总获奖次数: {stats['total_wins']}")
        
        if stats['active_round']:
            print(f"   - 活跃轮次: 第{stats['active_round'].round_number}次")
        else:
            print("   - 当前无活跃轮次")
    else:
        print("❌ 获取统计信息失败")
    
    print("\n7. 测试重复参与检测...")
    if participants:
        user_id = participants[0]['tg']
        nickname = participants[0]['nickname']
        
        # 创建新轮次
        new_round = sql_create_lottery_round(
            round_number=2,
            lottery_name="ME注册资格测试2",
            max_participants=5,
            entry_fee=3,
            winner_count=1,
            created_by=999999
        )
        
        if new_round:
            # 第一次参与
            participant1, msg1 = sql_join_lottery_round(new_round.id, user_id, nickname)
            print(f"✅ 首次参与: {msg1}")
            
            # 重复参与
            participant2, msg2 = sql_join_lottery_round(new_round.id, user_id, nickname)
            print(f"✅ 重复参与检测: {msg2}")
            
            # 清理测试轮次
            sql_complete_lottery_round(new_round.id, [])
    
    print("\n🎉 CodeLottery 系统测试完成！")


def test_user_progression():
    """测试用户参与次数累积"""
    print("\n📈 测试用户参与次数累积...")
    
    test_user_id = 99999
    test_nickname = "TestUser"
    
    # 创建用户
    user = sql_create_codelottery_user(test_user_id)
    if not user:
        print("❌ 创建测试用户失败")
        return
    
    print(f"✅ 初始参与次数: {user.total_participations}")
    
    # 模拟多次参与
    for i in range(3):
        # 创建轮次
        round_obj = sql_create_lottery_round(
            round_number=100 + i,
            lottery_name=f"测试轮次{i+1}",
            max_participants=1,
            entry_fee=3,
            winner_count=1,
            created_by=999999
        )
        
        if round_obj:
            # 参与抽奖
            participant, msg = sql_join_lottery_round(round_obj.id, test_user_id, test_nickname)
            if participant:
                print(f"✅ 第{i+1}次参与成功")
                
                # 模拟开奖（偶数次获奖）
                if i % 2 == 0:
                    winners = [{'tg': test_user_id, 'nickname': test_nickname}]
                    sql_complete_lottery_round(round_obj.id, winners)
                    print(f"🎉 第{i+1}次获奖")
                else:
                    sql_complete_lottery_round(round_obj.id, [])
                    print(f"😔 第{i+1}次未获奖")
            else:
                print(f"❌ 第{i+1}次参与失败: {msg}")
    
    # 检查最终统计
    final_user = sql_get_codelottery_user(test_user_id)
    if final_user:
        print(f"✅ 最终统计:")
        print(f"   - 总参与次数: {final_user.total_participations}")
        print(f"   - 总获奖次数: {final_user.total_wins}")
        print(f"   - 获奖率: {final_user.total_wins / max(final_user.total_participations, 1) * 100:.1f}%")


if __name__ == "__main__":
    print("🚀 CodeLottery 数据库测试脚本")
    print("=" * 50)
    
    try:
        test_codelottery_system()
        test_user_progression()
        
        print("\n" + "=" * 50)
        print("✅ 所有测试完成")
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)