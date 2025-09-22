#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
观影时长获取原理演示程序
这个演示程序展示了 userplays_rank.py 中观影时长获取和处理的核心逻辑
"""

from datetime import datetime, timezone, timedelta


def demonstrate_time_range_calculation(days: int):
    """演示时间范围计算"""
    print("⏰ 时间范围计算演示:")
    print("=" * 50)
    
    # 模拟北京时间
    sub_time = datetime.now(timezone(timedelta(hours=8)))
    start_time = (sub_time - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    end_time = sub_time.strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"当前北京时间: {sub_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"查询起始时间: {start_time}")
    print(f"查询结束时间: {end_time}")
    print(f"查询天数范围: {days} 天")
    print()
    
    return start_time, end_time


def convert_seconds_to_readable(seconds: int) -> str:
    """时长格式化函数，对应 bot/func_helper/utils.py 中的 convert_s() 函数"""
    duration = timedelta(seconds=seconds)
    days = duration.days
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    days_str = '' if days == 0 else f'{days} 天'
    hours_str = '' if hours == 0 else f'{hours} 小时'
    return f"{days_str} {hours_str} {minutes} 分钟".strip()


def main():
    """主演示函数"""
    print("🎬 BavaBot 观影时长获取原理演示")
    print("=" * 60)
    print()
    
    # 模拟数据：用户ID和观影时长（秒）
    sample_data = [
        ("user_001", 14400),  # 4小时
        ("user_002", 10800),  # 3小时  
        ("user_003", 7200),   # 2小时
        ("user_004", 5400),   # 1.5小时
        ("user_005", 3600),   # 1小时
        ("user_006", 2700),   # 45分钟（不满足奖励条件）
        ("user_007", 1800),   # 30分钟（不满足奖励条件）
    ]
    
    user_mapping = {
        "user_001": {"name": "张三", "tg": 123456789, "lv": "b", "iv": 100},
        "user_002": {"name": "李四", "tg": 987654321, "lv": "b", "iv": 80}, 
        "user_003": {"name": "王五", "tg": 456789123, "lv": "b", "iv": 60},
        "user_004": {"name": "赵六", "tg": 321654987, "lv": "b", "iv": 40},
        "user_005": {"name": "孙七", "tg": 789123456, "lv": "b", "iv": 20},
        "user_006": {"name": "周八", "tg": 654987321, "lv": "b", "iv": 10},
        "user_007": {"name": "吴九", "tg": 147258369, "lv": "b", "iv": 5},
    }
    
    days = 7
    demonstrate_time_range_calculation(days)
    
    print(f"📊 模拟从 Emby 获取过去 {days} 天的观影数据:")
    print("=" * 50)
    for user_id, watch_time in sample_data:
        hours = watch_time // 3600
        minutes = (watch_time % 3600) // 60
        print(f"  {user_id}: {watch_time}秒 ({hours}小时{minutes}分钟)")
    print()
    
    # 排行榜处理
    rank_medals = ["🥇", "��", "🥉", "🏅"]
    leaderboard_data = []
    
    print("🏆 观影排行榜处理:")
    print("=" * 50)
    
    for rank, (user_id, watch_time_seconds) in enumerate(sample_data, 1):
        medal = rank_medals[rank - 1] if rank < 4 else rank_medals[3]
        member_info = user_mapping.get(user_id)
        
        if member_info:
            emby_name = member_info["name"]
            viewing_time_minutes = watch_time_seconds // 60
            points = 0
            
            # 奖励机制：只有观看60分钟及以上才有奖励
            if viewing_time_minutes >= 60:
                points = 19  # 基础奖励
                
                # 前三名额外奖励
                if rank == 1:
                    points += 3
                elif rank == 2:
                    points += 2
                elif rank == 3:
                    points += 1
                
                new_iv = member_info["iv"] + points
                leaderboard_data.append([member_info["tg"], new_iv, f'{medal}{emby_name}', points])
        
        formatted_time = convert_seconds_to_readable(watch_time_seconds)
        status = f"获得 {points} 积分" if points > 0 else "观影时长不足60分钟，无奖励"
        print(f"{medal} 第{rank}名 | {emby_name}")
        print(f"   观影时长: {formatted_time}")
        print(f"   奖励状态: {status}")
        print()
    
    # 结算统计
    if leaderboard_data:
        print("💰 积分结算统计:")
        print("=" * 50)
        total_points = sum(item[3] for item in leaderboard_data)
        print(f"符合结算条件用户数: {len(leaderboard_data)} 人")
        print(f"发放积分总数: {total_points} 个")
        print(f"结算天数: {days} 天")
        print()
        
        print("详细结算清单:")
        for tg, new_iv, name_with_medal, points in leaderboard_data:
            print(f"  {name_with_medal} (TG:{tg}) 获得 {points} 积分，新积分余额: {new_iv}")
    
    print()
    print("📝 核心技术要点:")
    print("=" * 50)
    print("1. 数据源: Emby PlaybackActivity 表")
    print("2. 时长计算: PlayDuration - PauseDuration") 
    print("3. 奖励门槛: 观影时长 ≥ 60分钟")
    print("4. 基础奖励: 19积分")
    print("5. 排名奖励: 第一名+3, 第二名+2, 第三名+1")
    print("6. 时区处理: 统一使用北京时间 (UTC+8)")
    print("7. 缓存机制: 120秒 TTL")


if __name__ == "__main__":
    main()
