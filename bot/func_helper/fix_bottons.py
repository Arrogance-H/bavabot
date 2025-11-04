from cacheout import Cache
from pykeyboard import InlineKeyboard, InlineButton
from pyrogram.types import InlineKeyboardMarkup
from pyromod.helpers import ikb, array_chunk
from bot import chanel, main_group, bot_name, extra_emby_libs, tz_id, tz_ad, tz_api, _open, sakura_b, \
    schedall, auto_update, fuxx_pitao, moviepilot, red_envelope, config, tmdb
from bot.func_helper import nezha_res
from bot.func_helper.emby import emby
from bot.func_helper.utils import members_info, convert_to_beijing_time

cache = Cache()

"""start面板 ↓"""


def judge_start_ikb(is_admin: bool, account: bool, user_data=None) -> InlineKeyboardMarkup:
    """
    start面板按钮
    """
    if not account:
        d = []
        d.append(['🎟️ 使用注册码', 'exchange'])
        d.append(['👑 创建账户', 'create'])
        d.append(['⭕ 换绑TG', 'changetg'])
        d.append(['🔍 绑定TG', 'bindtg'])
        # 如果邀请等级为d （未注册用户也能使用），则显示兑换商店
        if _open.invite_lv == 'd':
            d.append(['🏪 兑换商店', 'storeall'])
    else:
        d = [['️👥 用户功能', 'members'], ['🌐 服务器', 'server']]
        # 只有在检查到期且用户不是活跃保号模式时才显示续期码按钮
        show_renew_button = schedall.check_ex
        if user_data and show_renew_button:
            _, _, _, _, _, _, preserve_mode, _ = user_data
            # 如果是活跃保号用户，不显示使用续期码按钮
            if preserve_mode == 'active':
                show_renew_button = False
        
        if show_renew_button:
            d.append(['🎟️ 使用续期码', 'exchange'])
    if _open.checkin: d.append([f'🎯 签到', 'checkin'])
    if _open.punch_in: d.append([f'🎮 F1', 'punch_in'])
    lines = array_chunk(d, 2)
    if is_admin: lines.append([['👮🏻‍♂️ admin', 'manage']])
    keyword = ikb(lines)
    return keyword


# un_group_answer
group_f = ikb([[('点击我(●ˇ∀ˇ●)', f't.me/{bot_name}', 'url')]])
# un in group
judge_group_ikb = ikb([[('🌟 频道入口 ', f't.me/{chanel}', 'url'),
                        ('💫 群组入口', f't.me/{main_group}', 'url')],
                       [('❌ 关闭消息', 'closeit')]])

"""members ↓"""


def members_ikb(is_admin: bool = False, account: bool = False, can_switch_preserve: bool = False) -> InlineKeyboardMarkup:
    """
    判断用户面板
    """
    if account:
        normal = [[('🏪 兑换商店', 'storeall'), ('🗑️ 删除账号', 'delme')],
                    [('🎬 显示/隐藏', 'embyblock'), ('⭕ 重置密码', 'reset')],
                    [('💖 我的收藏', 'my_favorites'),('💠 我的设备', 'my_devices')],
                    ]
        
        if moviepilot.status:
            normal.append([('🍿 点播中心', 'download_center')])
        
        # 将保号切换按钮与ME点播按钮放在同一行
        last_row = []
        if tmdb.api_key:
            last_row.append(('🍿 ME点播', 'tmdb_main'))
        if can_switch_preserve:
            last_row.append(('🛡️ 保号切换', 'switch_preserve_mode'))
        
        if last_row:
            normal.append(last_row)
        normal.append([('♻️ 主界面', 'back_start')])
        return ikb(normal)
    else:
        return judge_start_ikb(is_admin, account, user_data=None)
        # return ikb(
        #     [[('👑 创建账户', 'create')], [('⭕ 换绑TG', 'changetg'), ('🔍 绑定TG', 'bindtg')],
        #      [('♻️ 主界面', 'back_start')]])


back_start_ikb = ikb([[('💫 回到首页', 'back_start')]])
back_members_ikb = ikb([[('💨 返回', 'members')]])
back_manage_ikb = ikb([[('💨 返回', 'manage')]])
re_create_ikb = ikb([[('🍥 重新输入', 'create'), ('💫 用户主页', 'members')]])
re_changetg_ikb = ikb([[('✨ 换绑TG', 'changetg'), ('💫 用户主页', 'members')]])
re_bindtg_ikb = ikb([[('✨ 绑定TG', 'bindtg'), ('💫 用户主页', 'members')]])
re_delme_ikb = ikb([[('♻️ 重试', 'delme')], [('🔙 返回', 'members')]])
re_reset_ikb = ikb([[('♻️ 重试', 'reset')], [('🔙 返回', 'members')]])
re_exchange_b_ikb = ikb([[('♻️ 重试', 'exchange'), ('❌ 关闭', 'closeit')]])
re_born_ikb = ikb([[('✨ 重输', 'store-reborn'), ('💫 返回', 'storeall')]])


def send_changetg_ikb(cr_id, rp_id):
    """
    :param cr_id: 当前操作id
    :param rp_id: 替换id
    :return:
    """
    return ikb([[('✅ 通过', f'changetg_{cr_id}_{rp_id}'), ('❎ 驳回', f'nochangetg_{cr_id}_{rp_id}')]])


def store_ikb():
    return ikb([[(f'♾️ 兑换白名单', 'store-whitelist'), (f'🔥 兑换解封禁', 'store-reborn')],
                [(f'🎟️ 兑换注册码', 'store-invite'), (f'🔍 查询注册码', 'store-query')],
                [(f'❌ 取消', 'members')]])


re_store_renew = ikb([[('✨ 重新输入', 'changetg'), ('💫 取消输入', 'storeall')]])


def del_me_ikb(embyid) -> InlineKeyboardMarkup:
    return ikb([[('🎯 确定', f'delemby-{embyid}')], [('🔙 取消', 'members')]])


def emby_block_ikb(embyid) -> InlineKeyboardMarkup:
    return ikb(
        [[("✔️️ - 显示", f"emby_unblock-{embyid}"), ("✖️ - 隐藏", f"emby_block-{embyid}")], [("🔙 返回", "members")]])


user_emby_block_ikb = ikb([[('✅ 已隐藏', 'members')]])
user_emby_unblock_ikb = ikb([[('❎ 已显示', 'members')]])

def preserve_switch_confirm_ikb(new_mode: str) -> InlineKeyboardMarkup:
    """保号方式切换确认按钮"""
    return ikb([
        [('✅ 确认切换', f'confirm_preserve_switch_{new_mode}'), ('❌ 取消', 'members')]
    ])


def preserve_manage_ikb() -> InlineKeyboardMarkup:
    """管理员保号方式管理面板按钮"""
    return ikb([
        [('📊 保号统计', 'preserve_stats'), ('🔍 查询用户', 'preserve_user_query')],
        [('⚙️ 修改保号方式', 'preserve_user_modify'), ('🔄 重置切换权限', 'preserve_reset_switch')],
        [('🔙 返回管理面板', 'manage')]
    ])


def preserve_back_ikb() -> InlineKeyboardMarkup:
    """保号管理返回按钮"""
    return ikb([[('🔙 返回', 'preserve_manage')]])


def preserve_retry_query_ikb() -> InlineKeyboardMarkup:
    """保号管理重新查询按钮"""
    return ikb([[('🔄 重新查询', 'preserve_user_query'), ('🔙 返回', 'preserve_manage')]])


def preserve_retry_modify_ikb() -> InlineKeyboardMarkup:
    """保号管理重新修改按钮"""
    return ikb([[('🔄 重新输入', 'preserve_user_modify'), ('🔙 返回', 'preserve_manage')]])


def preserve_retry_reset_ikb() -> InlineKeyboardMarkup:
    """保号管理重新重置按钮"""
    return ikb([[('🔄 重新输入', 'preserve_reset_switch'), ('🔙 返回', 'preserve_manage')]])


"""server ↓"""


@cache.memoize(ttl=120)
async def cr_page_server():
    """
    翻页服务器面板
    :return:
    """
    sever = nezha_res.sever_info(tz_ad, tz_api, tz_id)
    if not sever:
        return ikb([[('🔙 - 用户', 'members'), ('❌ - 上一级', 'back_start')]]), None
    d = []
    for i in sever:
        d.append([i['name'], f'server:{i["id"]}'])
    lines = array_chunk(d, 3)
    lines.append([['🔙 - 用户', 'members'], ['❌ - 上一级', 'back_start']])
    # keyboard是键盘，a是sever
    return ikb(lines), sever


"""admins ↓"""

gm_ikb_content = ikb([[('⭕ 注册状态', 'open-menu'), ('🎟️ 注册/续期码', 'cr_link')],
                      [('💊 查询注册', 'ch_link'), ('🏬 兑换设置', 'set_renew')],
                      [('👥 用户列表', 'normaluser'), ('👑 白名单列表', 'whitelist')],
                      [('💎 M尊享列表', 'mpremium'), ('💠 设备列表', 'user_devices')],
                      [('🛡️ 保号管理', 'preserve_manage'), ('🌏 定时', 'schedall')],
                      [('🕹️ 主界面', 'back_start'), ('其他 🪟', 'back_config')]])


def open_menu_ikb(openstats, timingstats) -> InlineKeyboardMarkup:
    return ikb([[(f'{openstats} 自由注册', 'open_stat'), (f'{timingstats} 定时注册', 'open_timing')],
                [('🤖注册账号天数', 'open_us'),('⭕ 注册限制', 'all_user_limit')], [('🌟 返回上一级', 'manage')]])


back_free_ikb = ikb([[('🔙 返回上一级', 'open-menu')]])
back_open_menu_ikb = ikb([[('🪪 重新定时', 'open_timing'), ('🔙 注册状态', 'open-menu')]])
re_cr_link_ikb = ikb([[('♻️ 继续创建', 'cr_link'), ('🎗️ 返回主页', 'manage')]])
close_it_ikb = ikb([[('❌ - Close', 'closeit')]])


def ch_link_ikb(ls: list) -> InlineKeyboardMarkup:
    lines = array_chunk(ls, 2)
    lines.append([["💫 回到首页", "manage"]])
    return ikb(lines)


def date_ikb(i) -> InlineKeyboardMarkup:
    return ikb([[('🌘 - 月', f'register_mon_{i}'), ('🌗 - 季', f'register_sea_{i}'),
                 ('🌖 - 半年', f'register_half_{i}')],
                [('🌕 - 年', f'register_year_{i}'), ('🌑 - 未用', f'register_unused_{i}'), ('🎟️ - 已用', f'register_used_{i}')],
                [('🔙 - 返回', 'ch_link')]])

# 翻页按钮
async def cr_paginate(total_page: int, current_page: int, n) -> InlineKeyboardMarkup:
    """
    :param total_page: 总数
    :param current_page: 目前
    :param n: mode 可变项
    :return:
    """
    keyboard = InlineKeyboard()
    keyboard.paginate(total_page, current_page, 'pagination_keyboard:{number}' + f'_{n}')
    next = InlineButton('⏭️ 后退+5', f'users_iv:{current_page + 5}-{n}')
    previous = InlineButton('⏮️ 前进-5', f'users_iv:{current_page - 5}-{n}')
    followUp = [InlineButton('❌ 关闭', f'closeit')]
    if total_page > 5:
        if current_page - 5 >= 1:
            followUp.append(previous)
        if current_page + 5 < total_page:
            followUp.append(next)
    keyboard.row(*followUp)
    return keyboard


async def users_iv_button(total_page: int, current_page: int, tg) -> InlineKeyboardMarkup:
    """
    :param total_page: 总页数
    :param current_page: 当前页数
    :param tg: 可操作的tg_id
    :return:
    """
    keyboard = InlineKeyboard()
    keyboard.paginate(total_page, current_page, 'users_iv:{number}' + f'_{tg}')
    next = InlineButton('⏭️ 后退+5', f'users_iv:{current_page + 5}_{tg}')
    previous = InlineButton('⏮️ 前进-5', f'users_iv:{current_page - 5}_{tg}')
    followUp = [InlineButton('❌ 关闭', f'closeit')]
    if total_page > 5:
        if current_page - 5 >= 1:
            followUp.append(previous)
        if current_page + 5 < total_page:
            followUp.append(next)
    keyboard.row(*followUp)
    return keyboard


async def plays_list_button(total_page: int, current_page: int, days) -> InlineKeyboardMarkup:
    """
    :param total_page: 总页数
    :param current_page: 当前页数
    :param days: 请求获取多少天
    :return:
    """
    keyboard = InlineKeyboard()
    keyboard.paginate(total_page, current_page, 'uranks:{number}' + f'_{days}')
    # 添加按钮,前进5, 后退5
    next = InlineButton('⏭️ 后退+5', f'uranks:{current_page + 5}_{days}')
    previous = InlineButton('⏮️ 前进-5', f'uranks:{current_page - 5}_{days}')
    followUp = [InlineButton('❌ 关闭', f'closeit')]
    if total_page > 5:
        if current_page - 5 >= 1:
            followUp.append(previous)
        if current_page + 5 < total_page:
            followUp.append(next)
    keyboard.row(*followUp)
    return keyboard


async def store_query_page(total_page: int, current_page: int) -> InlineKeyboardMarkup:
    """
    member的注册码查询分页
    :param total_page: 总
    :param current_page: 当前
    :return:
    """
    keyboard = InlineKeyboard()
    keyboard.paginate(total_page, current_page, 'store-query:{number}')
    next = InlineButton('⏭️ 后退+5', f'store-query:{current_page + 5}')
    previous = InlineButton('⏮️ 前进-5', f'store-query:{current_page - 5}')
    followUp = [InlineButton('🔙 Back', 'storeall')]
    if total_page > 5:
        if current_page - 5 >= 1:
            followUp.append(previous)
        if current_page + 5 < total_page:
            followUp.append(next)
    keyboard.row(*followUp)
    return keyboard

async def whitelist_page_ikb(total_page: int, current_page: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboard()
    keyboard.paginate(total_page, current_page, 'whitelist:{number}')
    next = InlineButton('⏭️ 后退+5', f'whitelist:{current_page + 5}')
    previous = InlineButton('⏮️ 前进-5', f'whitelist:{current_page - 5}')
    followUp = [InlineButton('🔙 Back', 'manage')]
    if total_page > 5:
        if current_page - 5 >= 1:
            followUp.append(previous)
        if current_page + 5 < total_page:
            followUp.append(next)
    keyboard.row(*followUp)
    return keyboard

async def mpremium_page_ikb(total_page: int, current_page: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboard()
    keyboard.paginate(total_page, current_page, 'mpremium:{number}')
    next = InlineButton('⏭️ 后退+5', f'mpremium:{current_page + 5}')
    previous = InlineButton('⏮️ 前进-5', f'mpremium:{current_page - 5}')
    followUp = [InlineButton('🔙 Back', 'manage')]
    if total_page > 5:
        if current_page - 5 >= 1:
            followUp.append(previous)
        if current_page + 5 < total_page:
            followUp.append(next)
    keyboard.row(*followUp)
    return keyboard

async def normaluser_page_ikb(total_page: int, current_page: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboard()
    keyboard.paginate(total_page, current_page, 'normaluser:{number}')
    next = InlineButton('⏭️ 后退+5', f'normaluser:{current_page + 5}')
    previous = InlineButton('⏮️ 前进-5', f'normaluser:{current_page - 5}')
    followUp = [InlineButton('🔙 Back', 'manage')]
    if total_page > 5:
        if current_page - 5 >= 1:
            followUp.append(previous)
        if current_page + 5 < total_page:
            followUp.append(next)
    keyboard.row(*followUp)
    return keyboard
def devices_page_ikb( has_prev: bool, has_next: bool, page: int) -> InlineKeyboardMarkup:
    # 构建分页按钮
    buttons = []
    if has_prev or has_next:
        nav_buttons = []
        if has_prev:
            nav_buttons.append(('⬅️', f'devices:{page-1}'))
        nav_buttons.append((f'第 {page} 页', 'none'))
        if has_next:
            nav_buttons.append(('➡️', f'devices:{page+1}'))
        buttons.append(nav_buttons)
    # 添加返回按钮
    buttons.append([('🔙 返回', 'manage')])
    keyboard = ikb(buttons)
    return keyboard
async def favorites_page_ikb(total_page: int, current_page: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboard()
    keyboard.paginate(total_page, current_page, 'page_my_favorites:{number}')
    next = InlineButton('⏭️ 后退+5', f'page_my_favorites:{current_page + 5}')
    previous = InlineButton('⏮️ 前进-5', f'page_my_favorites:{current_page - 5}')
    followUp = [InlineButton('🔙 Back', 'members')]
    if total_page > 5:
        if current_page - 5 >= 1:
            followUp.append(previous)
        if current_page + 5 < total_page:
            followUp.append(next)
    keyboard.row(*followUp)
    return keyboard
def cr_renew_ikb():
    checkin = '✔️' if _open.checkin else '❌'
    punch_in = '✔️' if _open.punch_in else '❌'
    exchange = '✔️' if _open.exchange else '❌'
    whitelist = '✔️' if _open.whitelist else '❌'
    invite = '✔️' if _open.invite else '❌'
    # 添加邀请等级的显示
    invite_lv_text = {
        'a': '白名单',
        'b': '普通用户',
        'c': '已禁用用户',
        'd': '无账号用户',
        'm': 'M尊享'
    }.get(_open.invite_lv, '未知')
    keyboard = InlineKeyboard(row_width=2)
    keyboard.add(InlineButton(f'{checkin} 每日签到', f'set_renew-checkin'),
                 InlineButton(f'{punch_in} 打卡游戏', f'set_renew-punch_in'),
                 InlineButton(f'{exchange} 自动{sakura_b}续期', f'set_renew-exchange'),
                 InlineButton(f'{whitelist} 兑换白名单', f'set_renew-whitelist'),
                 InlineButton(f'{invite} 兑换邀请码', f'set_renew-invite'),
                 InlineButton(f'邀请等级: {invite_lv_text}', f'set_invite_lv')
                 )
    keyboard.row(InlineButton(f'◀ 返回', 'manage'))
    return keyboard
def invite_lv_ikb():
    keyboard = ikb([
        [('🅰️ 白名单', 'set_invite_lv-a'), ('🅱️ 普通用户', 'set_invite_lv-b')],
        [('©️ 已禁用用户', 'set_invite_lv-c'), ('🅳️ 无账号用户', 'set_invite_lv-d')],
        [('Ⓜ️ M尊享', 'set_invite_lv-m')],
        [('🔙 返回', 'set_renew')]
    ])
    return keyboard

""" config_panel ↓"""


def config_preparation() -> InlineKeyboardMarkup:
    mp_set = '✅' if moviepilot.status else '❎'
    auto_up = '✅' if auto_update.status else '❎'
    leave_ban = '✅' if _open.leave_ban else '❎'
    uplays = '✅' if _open.uplays else '❎'
    fuxx_pt = '✅' if fuxx_pitao else '❎'
    red_envelope_status = '✅' if red_envelope.status else '❎'
    allow_private = '✅' if red_envelope.allow_private else '❎'
    keyboard = ikb(
        [[('📄 导出日志', 'log_out'), ('📌 设置探针', 'set_tz')],
         [('🎬 显/隐指定库', 'set_block'), (f'{fuxx_pt} 皮套人过滤功能', 'set_fuxx_pitao')],
         [('💠 普通用户线路', 'set_line'),('🌟 白名单线路', 'set_whitelist_line')],
         [('Ⓜ️ M尊享线路', 'set_m_line'), ('👥 M用户管理', 'manage_m_users')],
         [(f'{leave_ban} 退群封禁', 'leave_ban'), (f'{uplays} 观影奖励结算', 'set_uplays')],
         [(f'{auto_up} 自动更新bot', 'set_update'), (f'{mp_set} Moviepilot点播', 'set_mp')],
         [(f'{red_envelope_status} 红包', 'set_red_envelope_status'), (f'{allow_private} 专属红包', 'set_red_envelope_allow_private')],
         [(f'设置赠送资格天数({config.kk_gift_days}天)', 'set_kk_gift_days'), (f'设置活跃检测天数({config.activity_check_days}天)', 'set_activity_check_days')],
         [(f'设置封存账号天数({config.freeze_days}天)', 'set_freeze_days')],
        # Hunt game button removed
         [('🔙 返回', 'manage')]])
    return keyboard


back_config_p_ikb = ikb([[("🎮  ️返回主控", "back_config")]])


def back_set_ikb(method) -> InlineKeyboardMarkup:
    return ikb([[("♻️ 重新设置", f"{method}"), ("🔙 返回主页", "back_config")]])


def try_set_buy(ls: list) -> InlineKeyboardMarkup:
    d = [[ls], [["✅ 体验结束返回", "back_config"]]]
    return ikb(d)


""" other """
register_code_ikb = ikb([[('🎟️ 注册', 'create'), ('⭕ 取消', 'closeit')]])
dp_g_ikb = ikb([[("🈺 ╰(￣ω￣ｏ)", "t.me/Aaaaa_su", "url")]])


async def cr_kk_ikb(uid, first):
    text = ''
    text1 = ''
    keyboard = []
    data = await members_info(uid)
    if data is None:
        text += f'**· 🆔 TG** ：[{first}](tg://user?id={uid}) [`{uid}`]\n数据库中没有此ID。ta 还没有私聊过我'
    else:
        name, lv, ex, iv, embyid, pwd2, preserve_mode, preserve_mode_changed = data
        if name != '无账户信息':
            ban = "🌟 解除禁用" if lv == "已禁用" else '💢 禁用账户'
            keyboard = [[ban, f'user_ban-{uid}'], ['⚠️ 删除账户', f'closeemby-{uid}']]
            
            # 添加保号方式管理按钮（白名单和M尊享用户不显示）
            if lv not in ['白名单', 'M尊享']:  # 白名单和M尊享用户不显示保号切换按钮
                mode_name = {'active': '活跃保号', 'expire': '到期保号'}
                current_mode_text = mode_name.get(preserve_mode, '未知')
                switch_to_mode = 'expire' if preserve_mode == 'active' else 'active'
                switch_to_text = mode_name.get(switch_to_mode, '未知')
                keyboard.append([f'🛡️ 切换至{switch_to_text}', f'kk_preserve_switch-{uid}'])
            
            if len(extra_emby_libs) > 0:
                success, rep = await emby.user(emby_id=embyid)
                if success:
                    try:
                        currentblock = rep["Policy"]["BlockedMediaFolders"]
                    except KeyError:
                        currentblock = []
                    # 此处符号用于展示是否开启的状态
                    libs, embyextralib = ['✖️', f'embyextralib_unblock-{uid}'] if set(extra_emby_libs).issubset(
                        set(currentblock)) else ['✔️', f'embyextralib_block-{uid}']
                    keyboard.append([f'{libs} 额外媒体库', embyextralib])
            try:
                rst = await emby.emby_cust_commit(emby_id=embyid, days=30)
                last_time = rst[0][0]
                toltime = rst[0][1]
                if last_time:
                    try:
                        # Convert to Beijing time
                        beijing_time = convert_to_beijing_time(last_time)
                        formatted_time = beijing_time.strftime("%Y-%m-%d %H:%M:%S")
                        text1 = f"**· 🔋 上次活动** | {formatted_time}\n" \
                                f"**· 📅 过去30天** | {toltime} 分钟"
                    except Exception:
                        # Fallback to original format if conversion fails
                        text1 = f"**· 🔋 上次活动** | {last_time.split('.')[0]}\n" \
                                f"**· 📅 过去30天** | {toltime} 分钟"
                else:
                    text1 = f"**· 📅 过去30天未有记录**"
            except (TypeError, IndexError, ValueError):
                text1 = f"**· 📅 过去30天未有记录**"
        else:
            keyboard.append(['✨ 赠送资格', f'gift-{uid}'])
        
        # 添加保号方式信息到显示文本（白名单和M尊享用户不显示）
        if name != '无账户信息' and lv not in ['白名单', 'M尊享']:
            mode_name = {'active': '活跃保号', 'expire': '到期保号'}
            preserve_mode_text = mode_name.get(preserve_mode, '未知')
            switch_status = '已切换' if preserve_mode_changed >= 1 else '可切换'
            preserve_info = f"**· 🛡️ 保号方式** | {preserve_mode_text} ({switch_status})\n"
        else:
            preserve_info = ""
            
        text += f"**· 🍉 TG&名称** | [{first}](tg://user?id={uid})\n" \
                f"**· 🍒 识别のID** | `{uid}`\n" \
                f"**· 🍓 当前状态** | {lv}\n" \
                f"**· 🍥 持有{sakura_b}** | {iv}\n" \
                f"**· 💠 账号名称** | {name}\n" \
                f"**· 🚨 到期时间** | **{ex}**\n" \
                f"{preserve_info}"
        text += text1
        keyboard.extend([['🚫 踢出并封禁', f'fuckoff-{uid}'], ['❌ 删除消息', f'closeit']])
        lines = array_chunk(keyboard, 2)
        keyboard = ikb(lines)
    return text, keyboard


def cv_user_playback_reporting(user_id):
    return ikb([[('🌏 播放查询', f'userip-{user_id}'), ('❌ 关闭', 'closeit')]])


def gog_rester_ikb(link=None) -> InlineKeyboardMarkup:
    link_ikb = ikb([[('🎁 点击领取', link, 'url')]]) if link else ikb([[('👆🏻 点击注册', f't.me/{bot_name}', 'url')]])
    return link_ikb


""" sched_panel ↓"""


def sched_buttons():
    dayrank = '✅' if schedall.dayrank else '❎'
    weekrank = '✅' if schedall.weekrank else '❎'
    dayplayrank = '✅' if schedall.dayplayrank else '❎'
    weekplayrank = '✅' if schedall.weekplayrank else '❎'
    check_ex = '✅' if schedall.check_ex else '❎'
    low_activity = '✅' if schedall.low_activity else '❎'
    backup_db = '✅' if schedall.backup_db else '❎'
    keyboard = InlineKeyboard(row_width=2)
    keyboard.add(InlineButton(f'{dayrank} 播放日榜', f'sched-dayrank'),
                 InlineButton(f'{weekrank} 播放周榜', f'sched-weekrank'),
                 InlineButton(f'{dayplayrank} 观影日榜', f'sched-dayplayrank'),
                 InlineButton(f'{weekplayrank} 观影周榜', f'sched-weekplayrank'),
                 InlineButton(f'{check_ex} 到期保号', f'sched-check_ex'),
                 InlineButton(f'{low_activity} 活跃保号', f'sched-low_activity'),
                 InlineButton(f'{backup_db} 自动备份数据库', f'sched-backup_db')
                 )
    keyboard.row(InlineButton(f'🫧 返回', 'manage'))
    return keyboard


""" checkin 按钮↓"""

# def shici_button(ls: list):
#     shici = []
#     for l in ls:
#         l = [l, f'checkin-{l}']
#         shici.append(l)
#     # print(shici)
#     lines = array_chunk(shici, 4)
#     return ikb(lines)


# checkin_button = ikb([[('🔋 重新签到', 'checkin'), ('🎮 返回主页', 'back_start')]])

""" Request_media """

# request_tips_ikb = ikb([[('✔️ 已转向私聊求片', 'go_to_qiupian')]])

request_tips_ikb = None


def get_resource_ikb(download_name: str):
    # 翻页 + 下载此片 + 取消操作
    return ikb([[(f'下载本片', f'download_{download_name}'), ('激活订阅', f'submit_{download_name}')],
                [('❌ 关闭', 'closeit')]])
re_download_center_ikb = ikb([
    [('🍿 点播', 'get_resource'), ('📶 下载进度', 'download_rate')], 
    [('🔙 返回', 'members')]])
continue_search_ikb = ikb([
    [('🔄 继续搜索', 'continue_search'), ('❌ 取消搜索', 'cancel_search')],
    [('🔙 返回', 'download_center')]
])
def download_resource_ids_ikb(resource_ids: list):
    buttons = []
    row = []
    for i in range(0, len(resource_ids), 2):
        current_id = resource_ids[i]
        current_button = [f"资源编号: {current_id}", f'download_resource_id_{current_id}']
        if i + 1 < len(resource_ids):
            next_id = resource_ids[i + 1]
            next_button = [f"资源编号: {next_id}", f'download_resource_id_{next_id}']
            row.append([current_button, next_button])
        else:
            row.append([current_button])
    buttons.extend(row)
    buttons.append([('❌ 取消', 'cancel_download')])
    return ikb(buttons)
def request_record_page_ikb(has_prev: bool, has_next: bool):
    buttons = []
    if has_prev:
        buttons.append(('< 上一页', 'request_record_prev'))
    if has_next:
        buttons.append(('下一页 >', 'request_record_next'))
    return ikb([buttons, [('🔙 返回', 'download_center')]])
def mp_search_page_ikb(has_prev: bool, has_next: bool, page: int):
    buttons = []
    if has_prev:
        buttons.append(('< 上一页', 'mp_search_prev_page'))
    if has_next:
        buttons.append(('下一页 >', 'mp_search_next_page'))
    return ikb([buttons, [('💾 选择下载', 'mp_search_select_download'), ('❌ 取消搜索', 'cancel_search')]])

def tmdb_search_result_list_ikb(results_count: int = 0):
    """TMDB搜索结果列表按钮 - 无分页版本"""
    buttons = []
    
    # 添加选择按钮行
    select_buttons = []
    for i in range(1, min(results_count + 1, 6)):  # 最多5个结果
        select_buttons.append((f'{i}', f'tmdb_select_{i}'))
    
    result_buttons = []
    if select_buttons:
        # 每行最多3个按钮
        for i in range(0, len(select_buttons), 3):
            row = select_buttons[i:i+3]
            result_buttons.append(row)
    
    result_buttons.append([('🔙 返回', 'tmdb_main')])
    
    return ikb(result_buttons)

def tmdb_search_page_ikb(has_prev: bool, has_next: bool, page: int, results_count: int = 0):
    """TMDB搜索结果分页按钮"""
    buttons = []
    
    # 添加选择按钮行
    select_buttons = []
    for i in range(1, min(results_count + 1, 4)):  # 最多3个结果
        select_buttons.append((f'{i}', f'tmdb_select_{i}'))
    
    result_buttons = []
    if select_buttons:
        result_buttons.append(select_buttons)
    
    # 添加分页按钮
    nav_buttons = []
    if has_prev:
        nav_buttons.append(('< 上一页', 'tmdb_search_prev_page'))
    if has_next:
        nav_buttons.append(('下一页 >', 'tmdb_search_next_page'))
    
    if nav_buttons:
        result_buttons.append(nav_buttons)
    
    result_buttons.append([('🔙 返回', 'tmdb_main')])
    
    return ikb(result_buttons)

# Independent TMDB search buttons (not connected to download center)
tmdb_main_ikb = ikb([
    [('🔍 开始搜索', 'tmdb_search')],
    [('📋 点播记录', 'view_my_demands'), ('🎛️ 点播管理', 'demand_manage')],
    [('🔙 返回', 'members')]
])

tmdb_search_result_ikb = ikb([
    [('🎬 点播此片', 'me_request_movie')],
    [('🔙 返回', 'return_to_search_results')]
])

# 添加 MoviePilot 设置按钮
def mp_config_ikb():
    """MoviePilot 设置面板按钮"""
    mp_status = '✅' if moviepilot.status else '❎'
    lv_text = '无'
    if moviepilot.lv == 'a':
        lv_text = '白名单'
    elif moviepilot.lv == 'b':
        lv_text = '普通用户'
    keyboard = ikb([
        [(f'{mp_status} 点播功能', 'set_mp_status')],
        [('💰 设置点播价格', 'set_mp_price'), ('👥 设置用户权限', 'set_mp_lv')],
        [('📝 设置日志频道', 'set_mp_log_channel')],
        [('🔙 返回', 'back_config')]
    ])
    return keyboard

def tmdb_season_selection_ikb(seasons: list, selected_seasons: list = None, emby_season_count: int = 0, existing_seasons: list = None):
    """TMDB电视剧季数选择按钮 - 支持多选，不检查Emby限制"""
    if selected_seasons is None:
        selected_seasons = []
    # existing_seasons parameter ignored as we don't check Emby restrictions
    
    buttons = []
    
    # 每行最多2个季数按钮
    season_buttons = []
    for season in seasons:
        season_num = season.get('season_number', 0)
        episode_count = season.get('episode_count', 0)
        
        # 所有季数都可选择，不检查Emby状态
        if season_num in selected_seasons:
            button_text = f"✅ 第{season_num}季"
        else:
            button_text = f"⭕ 第{season_num}季"
            
        if episode_count > 0:
            button_text += f" ({episode_count}集)"
        season_buttons.append((button_text, f'toggle_season_{season_num}'))
    
    # 按每行2个按钮分组
    for i in range(0, len(season_buttons), 2):
        row = season_buttons[i:i+2]
        buttons.append(row)
    
    # 添加操作按钮
    action_buttons = []
    if selected_seasons:
        action_buttons.append(('✅ 确认选择', 'confirm_multi_seasons'))
        action_buttons.append(('🗑️ 清空选择', 'clear_season_selection'))
    
    if action_buttons:
        # 如果操作按钮超过2个，分成两行
        if len(action_buttons) > 2:
            buttons.append(action_buttons[:2])
            buttons.append(action_buttons[2:])
        else:
            buttons.append(action_buttons)
    
    # 添加返回按钮
    buttons.append([('🔙 返回', 'return_to_search_results')])
    
    return ikb(buttons)
