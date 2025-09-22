# userplays_rank.py 用户观影时长获取原理分析

## 概述

`userplays_rank.py` 文件是 BavaBot 项目中负责统计用户观影时长并进行排名的核心模块。该模块通过与 Emby 媒体服务器交互，获取用户的观影数据，计算观影时长，并根据时长进行排名和积分奖励。

## 核心类：Uplaysinfo

### 类结构
```python
class Uplaysinfo:
    client = emby  # Emby 服务客户端
    
    @classmethod
    async def users_playback_list(cls, days):
        # 获取用户播放记录列表的主要方法
    
    @staticmethod  
    async def user_plays_rank(days=7, uplays=True):
        # 用户观影排行榜处理方法
        
    @staticmethod
    async def check_low_activity():
        # 检查低活跃度用户方法
```

## 观影时长获取流程详解

### 1. 数据获取阶段

#### 1.1 从 Emby 获取原始播放数据
```python
play_list = await emby.emby_cust_commit(emby_id=None, days=days, method='sp')
```

**关键 SQL 查询**（在 `bot/func_helper/emby.py` 中）：
```sql
SELECT UserId, SUM(PlayDuration - PauseDuration) AS WatchTime 
FROM PlaybackActivity 
WHERE DateCreated >= '{start_time}' AND DateCreated < '{end_time}' 
GROUP BY UserId 
ORDER BY WatchTime DESC
```

**核心原理**：
- `PlayDuration`: 总播放时长（包含暂停时间）
- `PauseDuration`: 暂停时长
- `PlayDuration - PauseDuration`: 实际观看时长
- 按 `UserId` 分组统计指定时间范围内的观影时长
- 按观影时长降序排列

#### 1.2 查询用户映射关系
```python
with Session() as session:
    result = session.query(Emby).filter(Emby.name.isnot(None)).all()
    members_dict = {}
    for record in result:
        members_dict[record.name] = {
            "name": members.get(record.tg, '未绑定bot或已删除'),
            "tg": record.tg,
            "lv": record.lv,
            "iv": record.iv
        }
```

### 2. 数据处理阶段

#### 2.1 时长数据转换
- **输入**: `play_record[1]` (秒为单位的观影时长)
- **处理**: `viewing_time_seconds = int(play_record[1])`
- **分钟转换**: `viewing_time_minutes = viewing_time_seconds // 60`

#### 2.2 时长格式化显示
通过 `convert_s()` 函数进行友好格式化：
```python
async def convert_s(seconds: int):
    duration = timedelta(seconds=seconds)
    days = duration.days
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    days = '' if days == 0 else f'{days} 天'
    hours = '' if hours == 0 else f'{hours} 小时'
    return f"{days} {hours} {minutes} 分钟"
```

### 3. 积分奖励机制

#### 3.1 基础奖励条件
```python
if viewing_time_minutes >= 60:  # 观看时间≥60分钟才有奖励
    points = 19  # 基础奖励19积分
```

#### 3.2 排名额外奖励
```python
# 前三名额外奖励
if rank == 1:
    points += 3    # 第一名额外3积分
elif rank == 2:
    points += 2    # 第二名额外2积分  
elif rank == 3:
    points += 1    # 第三名额外1积分
```

#### 3.3 积分结算
```python
new_iv = member_info["iv"] + points
leaderboard_data.append([member_info["tg"], new_iv, f'{medal}{emby_name}', points])
```

### 4. 排行榜生成

#### 4.1 分页处理
- 每页显示 10 个用户
- `total_pages = math.ceil(len(play_list) / 10)`

#### 4.2 排名显示格式
```python
medal = rank_medals[rank - 1] if rank < 4 else rank_medals[3]
# rank_medals = ["🥇", "🥈", "🥉", "🏅"]

formatted_time = await convert_s(int(play_record[1]))
page_data += f'{medal}**第{cn2an.an2cn(rank)}名** | [{emby_name}](https://www.google.com/search?q={tg})\n' \
             f'  观影时长 | {formatted_time}\n'
```

## 时间处理机制

### 1. 时区处理
```python
sub_time = datetime.now(timezone(timedelta(hours=8)))  # 北京时间 UTC+8
start_time = (sub_time - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
end_time = sub_time.strftime("%Y-%m-%d %H:%M:%S")
```

### 2. 数据缓存
```python
@cache.memoize(ttl=120)  # 缓存2分钟
async def users_playback_list(cls, days):
```

## 数据流转流程图

```
1. 请求观影排行榜
       ↓
2. 构建时间查询范围（北京时间）
       ↓  
3. 调用 Emby API 执行 SQL 查询
   └─ PlaybackActivity 表
   └─ SUM(PlayDuration - PauseDuration)
       ↓
4. 获取原始播放时长数据
   └─ [UserId, WatchTime] 列表
       ↓
5. 查询用户映射关系
   └─ Emby 表：name → tg, iv, lv
       ↓
6. 数据处理与排名
   ├─ 时长转换（秒→分钟）
   ├─ 积分计算（≥60分钟→19积分+排名奖励）
   └─ 排行榜格式化
       ↓
7. 生成分页显示数据
   └─ 每页10个用户
       ↓
8. 积分结算（如果启用）
   └─ 更新数据库 iv 字段
```

## 关键技术点总结

1. **数据源**: Emby 媒体服务器的 `PlaybackActivity` 表
2. **核心计算**: `PlayDuration - PauseDuration` = 实际观影时长
3. **时长单位**: 服务器存储为秒，显示时转换为天/小时/分钟
4. **奖励门槛**: 60分钟起奖，基础19积分，前三名有额外奖励
5. **数据缓存**: 2分钟 TTL 避免频繁查询
6. **时区处理**: 统一使用北京时间（UTC+8）
7. **分页显示**: 每页10个用户，支持多页浏览

这个机制确保了观影时长统计的准确性，同时通过积分奖励鼓励用户活跃观影。