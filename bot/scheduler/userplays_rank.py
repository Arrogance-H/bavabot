import math
import cn2an
from datetime import datetime, timezone, timedelta

from bot import bot, bot_photo, group, sakura_b, LOGGER, ranks, _open 
from bot.func_helper.emby import emby
from bot.func_helper.utils import convert_to_beijing_time, convert_s, cache, get_users, tem_deluser
from bot.sql_helper import Session
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_embys, Emby, sql_update_emby
from bot.func_helper.fix_bottons import plays_list_button


class Uplaysinfo:
    client = emby

    @classmethod
    @cache.memoize(ttl=120)
    async def users_playback_list(cls, days):
        try:
            play_list = await emby.emby_cust_commit(emby_id=None, days=days, method='sp')
        except Exception as e:
            print(f"Error fetching playback list: {e}")
            return None, 1, 1

        if play_list is None:
            return None, 1, 1

        with Session() as session:
            # 更高效地查询 Emby 表的数据
            result = session.query(Emby).filter(Emby.name.isnot(None)).all()

            if not result:
                return None, 1

            total_pages = math.ceil(len(play_list) / 10)
            members = await get_users()
            members_dict = {}

            for record in result:
                members_dict[record.name] = {
                    "name": members.get(record.tg, '未绑定bot或已删除'),
                    "tg": record.tg,
                    "lv": record.lv,
                    "iv": record.iv
                }

            rank_medals = ["🥇", "🥈", "🥉", "🏅"]
            rank_points = [1000, 900, 800, 700, 600, 500, 400, 300, 200, 100]

            pages_data = []
            leaderboard_data = []

            for page_number in range(1, total_pages + 1):
                start_index = (page_number - 1) * 10
                end_index = start_index + 10
                page_data = f'**▎🏆{ranks.logo} {days} 天观影榜**\n\n'

                for rank, play_record in enumerate(play_list[start_index:end_index], start=start_index + 1):
                    medal = rank_medals[rank - 1] if rank < 4 else rank_medals[3]
                    member_info = members_dict.get(play_record[0], None)

                    if not member_info or not member_info["tg"]:
                        emby_name = '未绑定bot或已删除'
                        tg = 'None'
                    else:
                        emby_name = member_info["name"]
                        tg = member_info["tg"]

                        # 计算积分
                        viewing_time_seconds = int(play_record[1])
                        viewing_time_minutes = viewing_time_seconds // 60
                        
                        # 奖励机制：只有观看60分钟及以上才有奖励
                        if viewing_time_minutes >= 60:
                            # 观看时长超过60分钟，获得19积分
                            points = 19
                            
                            # 前三名额外奖励
                            if rank == 1:
                                points += 3
                            elif rank == 2:
                                points += 2
                            elif rank == 3:
                                points += 1
                            
                            # 只有获得积分的用户才加入奖励列表
                            new_iv = member_info["iv"] + points
                            leaderboard_data.append([member_info["tg"], new_iv, f'{medal}{emby_name}', points])

                    formatted_time = await convert_s(int(play_record[1]))
                    page_data += f'{medal}**第{cn2an.an2cn(rank)}名** | [{emby_name}](https://www.google.com/search?q={tg})\n' \
                                 f'  观影时长 | {formatted_time}\n'

                page_data += f'\n#UPlaysRank {datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")}'
                pages_data.append(page_data)

            return pages_data, total_pages, leaderboard_data

    @staticmethod
    async def user_plays_rank(days=7, uplays=True):
        try:
            a, n, ls = await Uplaysinfo.users_playback_list(days)
            if not a:
                error_msg = f'获取过去{days}天UserPlays数据失败'
                await bot.send_photo(chat_id=group[0], photo=bot_photo,
                                            caption=f'🍥 {error_msg}嘤嘤嘤 ~ 手动重试 ')
                LOGGER.error(f'【userplayrank】: {error_msg}')
                raise Exception(error_msg)
            
            play_button = await plays_list_button(n, 1, days)
            send = await bot.send_photo(chat_id=group[0], photo=bot_photo, caption=a[0], reply_markup=play_button)
            
            if uplays and _open.uplays:
                # 检查是否有用户需要结算
                if not ls:
                    await send.reply(f'📊 过去{days}天没有符合结算条件的用户（观看时间≥60分钟）')
                    LOGGER.info(f'【userplayrank】: 过去{days}天没有符合结算条件的用户')
                    return
                
                # 执行数据库更新
                if sql_update_embys(some_list=ls, method='iv'):
                    text = f'**✅ 自动将观看时长转换为{sakura_b} - 结算成功**\n\n'
                    for i in ls:
                        text += f'[{i[2]}](tg://user?id={i[0]}) 获得了 {i[3]} {sakura_b}奖励\n'
                    
                    # 添加结算统计信息
                    total_coins = sum(item[3] for item in ls)
                    text += f'\n📊 **结算统计**\n'
                    text += f'- 结算用户数: {len(ls)}人\n'
                    text += f'- 发放{sakura_b}总数: {total_coins}个\n'
                    text += f'- 结算天数: {days}天\n'
                    
                    n = 4096
                    chunks = [text[i:i + n] for i in range(0, len(text), n)]
                    for c in chunks:
                        await bot.send_message(chat_id=group[0],
                                               text=c + f'\n⏱️ 结算时间 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
                    LOGGER.info(f'【userplayrank】: 成功结算{len(ls)}个用户，发放{total_coins}个{sakura_b}')
                else:
                    error_msg = f'数据库更新失败 - 用户{sakura_b}增加操作执行失败'
                    await send.reply(f'**🎂！！！为用户增加{sakura_b}出错啦** \n\n错误详情: {error_msg}\n@管理员 请检查数据库连接状态')
                    LOGGER.error(f'【userplayrank】: {error_msg} - 影响用户列表: {ls}')
                    raise Exception(error_msg)
                    
        except Exception as e:
            # 如果这是从定时任务调用的，错误会被上层的错误处理函数捕获
            # 如果这是手动调用的，直接记录日志
            error_msg = f'用户观影结算执行异常: {str(e)}'
            LOGGER.error(f'【userplayrank】: {error_msg}')
            
            # 如果不是数据库错误（已经发过通知），发送通用错误通知
            if 'sql_update_embys' not in str(e) and 'UserPlays数据失败' not in str(e):
                try:
                    await bot.send_message(
                        chat_id=group[0], 
                        text=f'❌ **观影结算系统错误**\n\n'
                             f'错误信息: {error_msg}\n'
                             f'发生时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n'
                             f'@管理员 请检查系统状态'
                    )
                except:
                    pass  # 避免通知发送失败导致的二次异常
            
            raise  # 重新抛出异常，让上层错误处理函数处理

    @staticmethod
    async def check_low_activity():
        now = datetime.now(timezone(timedelta(hours=8)))
        success, users = await emby.users()
        if not success:
            return await bot.send_message(chat_id=group[0], text='⭕ 调用emby api失败')
        from bot import config
        activity_check_days = config.activity_check_days
        msg = f'正在执行**{activity_check_days}天活跃检测**...\n'
        for user in users:
            # 数据库先找
            e = sql_get_emby(tg=user["Name"])
            if e is None:
                continue

            elif e.lv == 'c':
                try:
                    ac_date = convert_to_beijing_time(user["LastActivityDate"])
                except KeyError:
                    ac_date = "None"
                finally:
                    if ac_date == "None" or ac_date + timedelta(days=15) < now:
                        if await emby.emby_del(emby_id=e.embyid):
                            sql_update_emby(Emby.embyid == e.embyid, embyid=None, name=None, pwd=None, pwd2=None, lv='d',
                                            cr=None, ex=None)
                            tem_deluser()
                            msg += f'**🔋活跃检测** - [{e.name}](tg://user?id={e.tg})\n#id{e.tg} 禁用后未解禁，已执行删除。\n\n'
                            LOGGER.info(f"【活跃检测】- 删除账户 {user['Name']} #id{e.tg}")
                        else:
                            msg += f'**🔋活跃检测** - [{e.name}](tg://user?id={e.tg})\n#id{e.tg} 禁用后未解禁，执行删除失败。\n\n'
                            LOGGER.info(f"【活跃检测】- 删除账户失败 {user['Name']} #id{e.tg}")
            elif e.lv == 'b':
                try:
                    ac_date = convert_to_beijing_time(user["LastActivityDate"])
                    
                    # print(e.name, ac_date, now)
                    if ac_date + timedelta(days=activity_check_days) < now:
                        if await emby.emby_change_policy(emby_id=user["Id"], disable=True):
                            sql_update_emby(Emby.embyid == user["Id"], lv='c')
                            msg += f"**🔋活跃检测** - [{user['Name']}](tg://user?id={e.tg})\n#id{e.tg} {activity_check_days}天未活跃，禁用\n\n"
                            LOGGER.info(f"【活跃检测】- 禁用账户 {user['Name']} #id{e.tg}：{activity_check_days}天未活跃")
                        else:
                            msg += f"**🎂活跃检测** - [{user['Name']}](tg://user?id={e.tg})\n{activity_check_days}天未活跃，禁用失败啦！检查emby连通性\n\n"
                            LOGGER.info(f"【活跃检测】- 禁用账户 {user['Name']} #id{e.tg}：禁用失败啦！检查emby连通性")
                except KeyError:
                    if await emby.emby_change_policy(emby_id=user["Id"], disable=True):
                        sql_update_emby(Emby.embyid == user["Id"], lv='c')
                        msg += f"**🔋活跃检测** - [{user['Name']}](tg://user?id={e.tg})\n#id{e.tg} 注册后未活跃，禁用\n\n"
                        LOGGER.info(f"【活跃检测】- 禁用账户 {user['Name']} #id{e.tg}：注册后未活跃禁用")
                    else:
                        msg += f"**🎂活跃检测** - [{user['Name']}](tg://user?id={e.tg})\n#id{e.tg} 注册后未活跃，禁用失败啦！检查emby连通性\n\n"
                        LOGGER.info(f"【活跃检测】- 禁用账户 {user['Name']} #id{e.tg}：禁用失败啦！检查emby连通性")
        msg += '**活跃检测结束**\n'
        n = 1000
        chunks = [msg[i:i + n] for i in range(0, len(msg), n)]
        for c in chunks:
            await bot.send_message(chat_id=group[0], text=c + f'**{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}**')
