# from . import emby_libs, pro_rev, renew, renewall, rmemby, score_coins, syncs, start

from .emby_libs import extraembylibs_blockall, extraembylibs_unblockall, embylibs_blockall, embylibs_unblockall
from .pro_rev import pro_admin, pro_user, rev_user, del_admin
from .renew import renew_user
from .renewall import renew_all
from .rmemby import rmemby_user
from .score_coins import score_user, coins_user
from .start import ui_g_command, my_info, count_info, p_start, b_start, store_alls
from .syncs import sync_emby_group, sync_emby_unbound, bindall_id, reload_admins
from .view_user import list_whitelist, whitelist_page, list_normaluser, normaluser_page

# 车库游戏用户命令 (Hunt Game User Commands)
from .hunt import (
    start_hunt,              # 开始游戏命令 (/hunt)
    hunt_action, hunt_bulk_action,
    hunt_end, hunt_game_return
)

# 车库游戏管理员命令 (Hunt Game Admin Commands)  
from .hunt_admin import (
    config_hunt_reward,      # 游戏配置命令 (/hunt_config_reward)
    list_hunt_rewards,       # 查看奖励配置 (/hunt_list_rewards)
    hunt_statistics          # 游戏统计信息 (/hunt_stats)
)

# 抽奖系统用户命令 (Lottery System User Commands)
from .lottery import (
    lottery_list,            # 查看抽奖列表 (/lottery)
    my_lottery_status        # 查看我的抽奖状态 (/my_lottery)
)

# 抽奖系统管理员命令 (Lottery System Admin Commands)
from .lottery_admin import (
    create_lottery_command,  # 创建抽奖 (/lottery_create)
    add_lottery_prize_command,  # 添加奖品 (/lottery_add_prize)
    manage_lottery_command,  # 管理抽奖 (/lottery_manage)
    manual_draw_lottery,     # 手动开奖 (/lottery_draw)
    list_all_lotteries,      # 查看所有抽奖 (/lottery_list_all)
    check_auto_draw          # 自动检查开奖任务
)
