import pytz

from bot import bot, _open, save_config, owner, admins, bot_name, ranks, schedall, group, config
from bot.sql_helper.sql_code import sql_add_code
from bot.sql_helper.sql_emby import sql_get_emby
from cacheout import Cache

cache = Cache()

# Constants for expiry time display
NO_PRESERVE_NEEDED_MSG = '__无需保号，放心食用__'


def judge_admins(uid):
    """
    判断是否admin
    :param uid: tg_id
    :return: bool
    """
    if uid != owner and uid not in admins and uid not in group:
        return False
    else:
        return True


def compare_user_level(user_level, required_level):
    """
    比较用户等级是否满足要求
    等级层次：m（M尊享）> a（白名单）> b（普通用户）> c（已禁用用户）> d（未注册用户）
    
    :param user_level: 用户的等级
    :param required_level: 所需的最低等级
    :return: True 如果用户等级满足要求，False 否则
    """
    # 定义等级优先级，数字越小优先级越高
    level_priority = {
        'm': 0,  # M尊享 - 最高级
        'a': 1,  # 白名单
        'b': 2,  # 普通用户  
        'c': 3,  # 已禁用用户
        'd': 4   # 无账号用户 - 最低级
    }
    
    user_priority = level_priority.get(user_level, 999)  # 未知等级设为最低
    required_priority = level_priority.get(required_level, 999)
    
    # 用户等级优先级小于等于所需等级优先级时，满足要求
    return user_priority <= required_priority


# @cache.memoize(ttl=60)
async def members_info(tg=None, name=None):
    """
    基础资料 - 可传递 tg,emby_name
    :param tg: tg_id
    :param name: emby_name
    :return: name, lv, ex, iv, embyid, pwd2, preserve_mode, preserve_mode_changed
    """
    if tg is None:
        tg = name
    data = sql_get_emby(tg)
    if data is None:
        return None
    else:
        name = data.name or '无账户信息'
        pwd2 = data.pwd2
        embyid = data.embyid
        iv = data.iv
        lv_dict = {
            'm': 'M尊享',
            'a': '白名单',
            'b': '普通用户',
            'c': '已禁用',
            'd': '未注册'
        }
        lv = lv_dict.get(data.lv, '未知')
        
        # 获取保号方式信息
        preserve_mode = getattr(data, 'preserve_mode', 'active')  # 默认为活跃保号
        preserve_mode_changed = getattr(data, 'preserve_mode_changed', 0)
        
        # Update ex display logic based on user's preserve_mode and admin settings
        # This implements preserve mode specific logic for displaying expiration information:
        # - M尊享 and whitelist users: show infinity symbol
        # - When admin disables corresponding check: show "无需保号"
        # - 'expire' mode with check enabled: shows formatted expiration date (到期保号)
        # - 'active' mode with check enabled: shows activity warning message (活跃保号) 
        # - no account: shows default message
        if lv in ['白名单', 'M尊享']:
            ex = '+ ∞'
        elif name != '无账户信息':
            # Check if admin has disabled the corresponding preserve check
            if preserve_mode == 'expire' and not schedall.check_ex:
                # Admin disabled expire check (到期保号检测), show "无需保号"
                ex = NO_PRESERVE_NEEDED_MSG
            elif preserve_mode == 'active' and not schedall.low_activity:
                # Admin disabled activity check (活跃保号检测), show "无需保号"
                ex = NO_PRESERVE_NEEDED_MSG
            elif preserve_mode == 'expire':
                # For 'expire' mode (到期保号), show the formatted expiration date
                if data.ex:
                    ex = data.ex.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    ex = '无账户信息'
            elif preserve_mode == 'active':
                # For 'active' mode (活跃保号), show activity warning message
                ex = f'__若{config.activity_check_days}天无观看将封禁__'
            else:
                # For any other preserve_mode, show the default message
                ex = NO_PRESERVE_NEEDED_MSG
        else:
            ex = data.ex or '无账户信息'
        
        return name, lv, ex, iv, embyid, pwd2, preserve_mode, preserve_mode_changed


async def open_check():
    """
    对config查询open
    :return: open_stats, all_user, tem, timing
    """
    open_stats = _open.stat
    all_user = _open.all_user
    tem = _open.tem
    timing = _open.timing
    return open_stats, all_user, tem, timing


def tem_adduser():
    _open.tem = _open.tem + 1
    if _open.tem >= _open.all_user:
        _open.stat = False
    save_config()


def tem_deluser():
    _open.tem = _open.tem - 1
    save_config()


from random import choice
import string


async def pwd_create(length=8, chars=string.ascii_letters + string.digits):
    """
    简短地生成随机密码，包括大小写字母、数字，可以指定密码长度
    :param length: 长度
    :param chars: 字符 -> python3中为string.ascii_letters,而python2下则可以使用string.letters和string.ascii_letters
    :return: 密码
    """
    return ''.join([choice(chars) for i in range(length)])


# 创建注册
async def cr_link_one(tg: int, times, count, days: int, method: str):
    """
    创建连接
    :param tg:
    :param times:
    :param count:
    :param days:
    :param method:
    :return:
    """
    links = ''
    code_list = []
    i = 1
    if method == 'code':
        while i <= count:
            p = await pwd_create(10)
            uid = f'{ranks.logo}-{times}-Register_{p}'
            code_list.append(uid)
            link = f'`{uid}`\n'
            links += link
            i += 1
    elif method == 'link':
        while i <= count:
            p = await pwd_create(10)
            uid = f'{ranks.logo}-{times}-Register_{p}'
            code_list.append(uid)
            link = f't.me/{bot_name}?start={uid}\n'
            links += link
            i += 1
    if sql_add_code(code_list, tg, days) is False:
        return None
    return links


# 创建续期
async def rn_link_one(tg: int, times, count, days: int, method: str):
    """
    创建连接
    :param tg:
    :param times:
    :param count:
    :param days:
    :param method:
    :return:
    """
    links = ''
    code_list = []
    i = 1
    if method == 'code':
        while i <= count:
            p = await pwd_create(10)
            uid = f'{ranks.logo}-{times}-Renew_{p}'
            code_list.append(uid)
            link = f'`{uid}`\n'
            links += link
            i += 1
    elif method == 'link':
        while i <= count:
            p = await pwd_create(10)
            uid = f'{ranks.logo}-{times}-Renew_{p}'
            code_list.append(uid)
            link = f't.me/{bot_name}?start={uid}\n'
            links += link
            i += 1
    if sql_add_code(code_list, tg, days) is False:
        return None
    return links


async def cr_link_two(tg: int, for_tg, days: int):
    code_list = []
    invite_code = await pwd_create(11)
    uid = f'{for_tg}-{invite_code}'
    code_list.append(uid)
    link = f't.me/{bot_name}?start={uid}'
    if sql_add_code(code_list, tg, days) is False:
        return None
    return link


from datetime import datetime, timedelta


async def convert_s(seconds: int):
    # 创建一个时间间隔对象，换算以后返回计算出的字符串
    duration = timedelta(seconds=seconds)
    days = duration.days
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    days = '' if days == 0 else f'{days} 天'
    hours = '' if hours == 0 else f'{hours} 小时'
    return f"{days} {hours} {minutes} 分钟"


def convert_runtime(RunTimeTicks: int):
    # 创建一个时间间隔对象，换算以后返回计算出的字符串
    seconds = RunTimeTicks // 10000000
    duration = timedelta(seconds=seconds)
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    hours = '' if hours == 0 else f'{hours} 小时'
    return f"{hours} {minutes} 分钟"


def convert_to_beijing_time(original_date):
    original_date = original_date.split(".")[0].replace('T', ' ')
    dt = datetime.strptime(original_date, "%Y-%m-%d %H:%M:%S") + timedelta(hours=8)
    # 使用pytz.timezone函数获取北京时区对象
    beijing_tz = pytz.timezone("Asia/Shanghai")
    # 使用beijing_tz.localize函数将dt对象转换为有时区的对象
    dt = beijing_tz.localize(dt)
    return dt


@cache.memoize(ttl=300)
async def get_users():
    # 创建一个空字典来存储用户的 first_name 和 id
    members_dict = {}
    async for member in bot.get_chat_members(group[0]):
        try:
            members_dict[member.user.id] = member.user.first_name
        except Exception as e:
            print(f'{e} 某名bug {member}')
    return members_dict


def bytes_to_gb(size_in_bytes):
    # 1 GB = 1024^3 字节
    size_in_gb = size_in_bytes / (1024 ** 3)
    return f"{round(size_in_gb)} G"

def split_long_message(content, max_length=2000):
    """
    将过长的消息内容分割成多个部分，确保每部分都不超过Telegram的长度限制
    
    Args:
        content (str): 要分割的内容
        max_length (int): 每条消息的最大长度限制，默认1000字符（留缓冲）
    
    Returns:
        list: 分割后的消息列表
    """
    if len(content) <= max_length:
        return [content]

    messages = []
    lines = content.split('\n')
    current_message = ""

    for line in lines:
        # 检查添加这一行后是否会超长
        test_message = current_message + ('\n' if current_message else '') + line

        if len(test_message) <= max_length:
            current_message = test_message
        else:
            # 如果当前消息不为空，保存它
            if current_message:
                messages.append(current_message)
                current_message = line
            else:
                # 如果单行就超长，需要强制分割
                if len(line) > max_length:
                    # 按字符分割超长的单行
                    while len(line) > max_length:
                        messages.append(line[:max_length])
                        line = line[max_length:]
                    if line:
                        current_message = line
                else:
                    current_message = line

    # 添加最后一部分
    if current_message:
        messages.append(current_message)

    return messages


import abc


class Singleton(abc.ABCMeta, type):
    """
    类单例
    """

    _instances: dict = {}

    def __call__(cls, *args, **kwargs):
        key = (cls, args, frozenset(kwargs.items()))
        if key not in cls._instances:
            cls._instances[key] = super().__call__(*args, **kwargs)
        return cls._instances[key]

# import random
# import grequests


# def err_handler(request, exception):
#     get_bot_wlc()


# def random_shici_data(data_list, x):
#     try:
#         # 根据不同的url返回的数据结构，获取相应的字段
#         if x == 0:
#             ju, nm = data_list[0]["content"], f'{data_list[0]["author"]}《{data_list[0]["origin"]}》'
#         elif x == 1:
#             ju, nm = data_list[1]["hitokoto"], f'{data_list[1]["from_who"]}《{data_list[1]["from"]}》'
#         elif x == 2:
#             ju, nm = data_list[2]["content"], data_list[2]["source"]
#             # 如果没有作者信息，就不显示
#         return ju, nm
#     except:
#         return False


# # 请求每日诗词
# def get_bot_shici():
#     try:
#         urls = ['https://v1.jinrishici.com/all.json', 'https://international.v1.hitokoto.cn/?c=i',
#                 'http://yijuzhan.com/api/word.php?m=json']
#         reqs = [grequests.get(url) for url in urls]
#         res_list = grequests.map(reqs)  # exception_handler=err_handler
#         data_list = [res.json() for res in res_list]
#         # print(data_list)
#         seq = [0, 1, 2]
#         x = random.choice(seq)
#         seq.remove(x)
#         e = random.choice(seq)
#         ju, nm = random_shici_data(data_list, x=x)
#         e_ju, e_nm = random_shici_data(data_list, x=e)
#         e_ju = random.sample(e_ju, 6)
#         T = ju
#         t = random.sample(ju, 2)
#         e_ju.extend(t)
#         random.shuffle(e_ju)
#         for i in t:
#             ju = ju.replace(i, '░')  # ░
#         print(T, e_ju, ju, nm)
#         return T, e_ju, ju, nm
#     except Exception as e:
#         print(e)
#         # await get_bot_shici()
