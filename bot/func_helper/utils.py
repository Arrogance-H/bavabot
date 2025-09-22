import pytz

from bot import bot, _open, save_config, owner, admins, bot_name, ranks, schedall, group, config
from bot.sql_helper.sql_code import sql_add_code
from bot.sql_helper.sql_emby import sql_get_emby
from cacheout import Cache

cache = Cache()


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


# @cache.memoize(ttl=60)
async def members_info(tg=None, name=None):
    """
    获取用户基础信息的核心函数
    
    这个函数是myinfo命令数据获取的关键环节，负责：
    1. 从数据库查询用户记录
    2. 处理和转换用户状态信息
    3. 计算到期时间显示逻辑
    4. 返回格式化的用户信息元组
    
    参数:
    - tg: Telegram用户ID（主要查询参数）
    - name: 用户名（备用查询参数，如果tg为None时使用）
    
    返回:
    - None: 如果用户不存在
    - tuple: (name, lv, ex, iv, embyid, pwd2) 用户信息元组
      - name: Emby账户名称
      - lv: 用户等级显示文本
      - ex: 到期时间显示文本
      - iv: 用户积分
      - embyid: Emby服务器用户ID
      - pwd2: 用户密码
    """
    # 参数处理：如果没有传入tg，使用name作为查询参数
    if tg is None:
        tg = name
    
    # 核心数据查询：从数据库获取用户记录
    data = sql_get_emby(tg)
    
    # 处理用户不存在的情况
    if data is None:
        return None
    else:
        # 提取和处理用户基础信息
        name = data.name or '无账户信息'  # Emby账户名，如果为空显示默认文本
        pwd2 = data.pwd2                   # 用户密码
        embyid = data.embyid              # Emby服务器中的用户ID
        iv = data.iv                      # 用户积分
        
        # 用户等级转换：将数据库中的字母代码转换为用户友好的显示文本
        lv_dict = {
            'a': '白名单',          # 白名单用户，通常有特殊权限
            'b': '**正常**',        # 正常用户
            'c': '**已禁用**',      # 被禁用的用户
            'd': '未注册'           # 未注册用户
        }
        lv = lv_dict.get(data.lv, '未知')  # 获取等级显示文本，未知状态显示"未知"
        
        # 到期时间处理逻辑
        if lv == '白名单':
            # 白名单用户永不过期
            ex = '+ ∞'
        elif data.name is not None and schedall.low_activity and not schedall.check_ex:
            # 有账户 + 启用低活跃检查 + 未启用到期检查：显示活跃要求
            ex = f'__若{config.activity_check_days}天无观看将封禁__'
        elif data.name is not None and not schedall.low_activity and not schedall.check_ex:
            # 有账户 + 未启用低活跃检查 + 未启用到期检查：无需保号
            ex = ' __无需保号，放心食用__'
        else:
            # 其他情况：显示数据库中的到期时间或默认信息
            ex = data.ex or '无账户信息'
        
        # 返回处理后的用户信息元组
        return name, lv, ex, iv, embyid, pwd2


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
