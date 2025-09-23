"""
ME点播 Panel - TMDB Search with Emby Library Check
First checks Emby library, then provides TMDB search if not found
Independent system with own request recording, admin notifications, and cost management
"""

from pyrogram import filters, enums
from bot import bot, tmdb, bot_photo, LOGGER, owner, admins, sakura_b
from bot.func_helper.msg_utils import callAnswer, editMessage, sendMessage, sendPhoto, callListen
from bot.func_helper.filters import user_in_group_on_filter
from bot.func_helper.fix_bottons import tmdb_main_ikb, tmdb_search_page_ikb, tmdb_search_result_ikb, back_members_ikb, tmdb_season_selection_ikb
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby
from bot.sql_helper.sql_request_record import sql_add_request_record, sql_check_existing_request_by_title
from bot.func_helper.tmdb import tmdb_service
from bot.func_helper.emby import emby
from bot.func_helper.utils import judge_admins
import asyncio
import uuid
import datetime

# 存储TMDB搜索结果的全局字典
user_tmdb_data = {}

# ME点播费用配置
ME_REQUEST_COSTS = {
    'movie': 10,  # 电影10币
    'tv': 10      # 电视剧10币(每季)
}

def calculate_me_request_cost(media_type: str) -> int:
    """计算ME点播请求费用"""
    if media_type.lower() in ['movie', '电影']:
        return ME_REQUEST_COSTS['movie']
    elif media_type.lower() in ['tv', 'series', '电视剧', '剧集']:
        return ME_REQUEST_COSTS['tv']
    else:
        # 默认按电影收费
        return ME_REQUEST_COSTS['movie']


@bot.on_callback_query(filters.regex('tmdb_main') & user_in_group_on_filter)
async def tmdb_main_handler(_, call):
    """ME点播主页面"""
    if not tmdb.api_key:
        return await callAnswer(call, '❌ 管理员未配置TMDB API密钥', True)
    
    emby_user = sql_get_emby(tg=call.from_user.id)
    if not emby_user:
        return await editMessage(call, '⚠️ 数据库没有你，请重新 /start录入')
    if emby_user.lv is None or emby_user.lv not in ['a', 'b']:
        return await editMessage(call, '🫡 您没有权限使用此功能', buttons=back_members_ikb)

    await callAnswer(call, '🍿 ME点播')
    welcome_text = (
        "🎬 **ME点播**\n\n"
        "点击下方\"🔍 开始搜索\"按钮开始使用"
    )
    
    await editMessage(call, welcome_text, buttons=tmdb_main_ikb, parse_mode=enums.ParseMode.MARKDOWN)


@bot.on_callback_query(filters.regex('tmdb_search') & user_in_group_on_filter)
async def tmdb_search_handler(_, call):
    """ME点播搜索入口"""
    if not tmdb.api_key:
        return await callAnswer(call, '❌ 管理员未配置TMDB API密钥', True)
    
    emby_user = sql_get_emby(tg=call.from_user.id)
    if not emby_user:
        return await editMessage(call, '⚠️ 数据库没有你，请重新 /start录入')
    if emby_user.lv is None or emby_user.lv not in ['a', 'b']:
        return await editMessage(call, '🫡 您没有权限使用此功能', buttons=back_members_ikb)

    await callAnswer(call, '🔍 开始搜索')
    await editMessage(call, 
        '🎬 **ME点播**\n\n'
        '请在120秒内发送你想搜索的电影或电视剧名称\n'
        '支持中文和外文名称搜索\n\n'
        '输入 /cancel 取消操作',
        parse_mode=enums.ParseMode.MARKDOWN
    )

    txt = await callListen(call, 120, buttons=tmdb_main_ikb)
    if txt is False:
        return
    if txt.text == '/cancel':
        await asyncio.gather(txt.delete(), editMessage(call, '🔍 已取消搜索', buttons=tmdb_main_ikb))
        return

    search_query = txt.text.strip()
    await txt.delete()
    
    # 首先检查Emby库
    await check_emby_first(call, search_query)


async def check_emby_first(call, search_query: str):
    """首先检查Emby库中是否存在该影视"""
    try:
        await editMessage(call, '🔍 正在检查Emby媒体库，请稍后...', buttons=tmdb_main_ikb)
        
        # 使用request_movie_panel.py中相同的Emby查询逻辑
        emby_results = await emby.get_movies(title=search_query)
        
        if emby_results:
            # 如果Emby库中存在，显示结果并提示使用Emby客户端观看
            text = "🎯 **Emby媒体库中已存在相关内容！**\n\n"
            text += "📚 **已找到以下影视资源:**\n\n"
            
            for index, item in enumerate(emby_results, start=1):
                text += f"**{index}.** {item['title']}"
                if item['year'] and item['year'] != '缺失':
                    text += f" ({item['year']})"
                text += f"\n📺 类型: {item.get('item_type', '未知')}\n"
                if item.get('genres') and item['genres'] != '未知':
                    text += f"🎭 类型: {item['genres']}\n"
                text += "\n"
            
            text += "✅ **观看指引:**\n"
            text += "请直接使用Emby客户端观看这些内容！\n"
            text += "• 打开Emby客户端应用\n"
            text += "• 搜索上述影片名称\n"
            text += "• 即可开始观看\n\n"
            text += "💡 如需搜索其他内容，可继续使用TMDB搜索"
            
            # 创建按钮：继续TMDB搜索 或 返回主页
            from bot.func_helper.fix_bottons import ikb
            emby_found_buttons = ikb([
                [('🔍 继续搜索', 'continue_tmdb_search')],
                [('🔙 返回主页', 'tmdb_main')]
            ])
            
            # 保存搜索词以便继续搜索使用
            user_tmdb_data[call.from_user.id] = {'search_query': search_query}
            
            await editMessage(call, text, buttons=emby_found_buttons, parse_mode=enums.ParseMode.MARKDOWN)
            return
        
        # 如果Emby中没有找到，继续TMDB搜索
        await editMessage(call, 
            f'🔍 Emby库中未找到 "{search_query}"\n'
            f'正在TMDB数据库中搜索...',
            buttons=tmdb_main_ikb
        )
        await tmdb_search_results(call, search_query, page=1)
        
    except Exception as e:
        LOGGER.error(f"检查Emby库时出错: {str(e)}")
        await editMessage(call, 
            '❌ 检查Emby库时出错，直接进行TMDB搜索...',
            buttons=tmdb_main_ikb
        )
        await tmdb_search_results(call, search_query, page=1)


@bot.on_callback_query(filters.regex('^continue_tmdb_search$') & user_in_group_on_filter)
async def continue_tmdb_search(_, call):
    """继续TMDB搜索（在Emby已找到内容后）"""
    user_data = user_tmdb_data.get(call.from_user.id)
    if not user_data or 'search_query' not in user_data:
        return await callAnswer(call, '❌ 搜索会话已过期，请重新搜索', True)
    
    await callAnswer(call, '🔍 继续TMDB搜索')
    search_query = user_data['search_query']
    await tmdb_search_results(call, search_query, page=1)


async def tmdb_search_results(call, query: str, page: int = 1):
    """显示TMDB搜索结果"""
    try:
        await editMessage(call, '🔍 正在TMDB搜索中，请稍后...', buttons=tmdb_main_ikb)
        
        success, results, pagination_info = await tmdb_service.search_multi(query, page)
        if not success or not results:
            await editMessage(
                call, 
                f'🤷‍♂️ TMDB数据库中未找到关键词 "{query}" 的相关影视作品\n\n'
                f'💡 **搜索建议:**\n'
                f'• 尝试使用不同的关键词\n'
                f'• 使用中文或英文名称\n'
                f'• 检查拼写是否正确', 
                buttons=tmdb_main_ikb,
                parse_mode=enums.ParseMode.MARKDOWN
            )
            return

        # 计算分页信息 - 基于TMDB API返回的分页信息
        has_prev = page > 1
        has_next = page < pagination_info.get("total_pages", 1)
        
        # 我们只显示前3个结果
        display_results = results[:3]
        
        # 保存搜索结果
        user_tmdb_data[call.from_user.id] = {
            'query': query,
            'results': results,
            'current_page': page,
            'pagination_info': pagination_info
        }

        # 显示结果
        result_text = f"🎬 **ME点播 - TMDB搜索结果**\n"
        result_text += f"🔍 搜索词: `{query}`\n"
        result_text += f"📄 第 {page} 页 / 共 {pagination_info.get('total_pages', 1)} 页\n"
        result_text += f"📊 本页显示 {len(display_results)} 个结果 | 总共 {pagination_info.get('total_results', 0)} 个结果\n\n"
        
        for index, item in enumerate(display_results, start=1):
            result_text += tmdb_service.format_search_result_text(item, index)
            result_text += "\n" + "─" * 10 + "\n\n"

        # 限制消息长度
        if len(result_text) > 4000:
            result_text = result_text[:3900] + "\n...\n\n📝 结果过长，已截断显示"

        await editMessage(
            call, 
            result_text, 
            buttons=tmdb_search_page_ikb(has_prev, has_next, page, len(display_results)),
            parse_mode=enums.ParseMode.MARKDOWN
        )

    except Exception as e:
        LOGGER.error(f"TMDB搜索出错: {str(e)}")
        await editMessage(call, '❌ 搜索过程中出错，请稍后再试', buttons=tmdb_main_ikb)


@bot.on_callback_query(filters.regex('^tmdb_search_prev_page$') & user_in_group_on_filter)
async def tmdb_search_prev_page(_, call):
    """TMDB搜索上一页"""
    user_data = user_tmdb_data.get(call.from_user.id)
    if not user_data:
        return await callAnswer(call, '❌ 搜索会话已过期，请重新搜索', True)
    
    new_page = user_data['current_page'] - 1
    if new_page < 1:
        return await callAnswer(call, '❌ 已经是第一页了', True)
    
    await callAnswer(call, f'📃 正在加载第 {new_page} 页')
    await tmdb_search_results(call, user_data['query'], new_page)


@bot.on_callback_query(filters.regex('^tmdb_search_next_page$') & user_in_group_on_filter)
async def tmdb_search_next_page(_, call):
    """TMDB搜索下一页"""
    user_data = user_tmdb_data.get(call.from_user.id)
    if not user_data:
        return await callAnswer(call, '❌ 搜索会话已过期，请重新搜索', True)
    
    new_page = user_data['current_page'] + 1
    await callAnswer(call, f'📃 正在加载第 {new_page} 页')
    await tmdb_search_results(call, user_data['query'], new_page)


@bot.on_callback_query(filters.regex('^tmdb_select_[123]$') & user_in_group_on_filter)
async def tmdb_select_numbered_item(_, call):
    """选择编号对应的TMDB影片查看详情"""
    user_data = user_tmdb_data.get(call.from_user.id)
    if not user_data:
        return await callAnswer(call, '❌ 搜索会话已过期，请重新搜索', True)
    
    # 从callback data中提取编号
    selected_index = int(call.data.split('_')[-1])
    
    await callAnswer(call, f'✅ 选择影片 {selected_index}')
    results = user_data['results']
    
    # 只显示前3个结果，所以直接使用索引
    display_results = results[:3]
    
    if not display_results or selected_index > len(display_results):
        await editMessage(call, '❌ 选择的影片不存在', buttons=tmdb_main_ikb)
        return

    try:
        selected_item = display_results[selected_index - 1]
        
        # 显示选中的影片详情
        await show_tmdb_item_details(call, selected_item)
        
    except Exception as e:
        LOGGER.error(f"选择TMDB影片出错: {str(e)}")
        await editMessage(call, '❌ 选择过程中出错', buttons=tmdb_main_ikb)


@bot.on_callback_query(filters.regex('^tmdb_select_item$') & user_in_group_on_filter)
async def tmdb_select_item(_, call):
    """选择TMDB影片查看详情（保留旧的文字输入方式作为备用）"""
    user_data = user_tmdb_data.get(call.from_user.id)
    if not user_data:
        return await callAnswer(call, '❌ 搜索会话已过期，请重新搜索', True)
    
    await callAnswer(call, '✅ 选择影片')
    results = user_data['results']
    
    if not results:
        await editMessage(call, '❌ 没有可选择的影片', buttons=tmdb_main_ikb)
        return

    await editMessage(call, 
        '🎬 **选择影片**\n\n'
        f'请在120秒内发送你要查看的影片编号（1-{min(len(results), 3)}）\n'
        '输入 /cancel 取消操作',
        parse_mode=enums.ParseMode.MARKDOWN
    )
    
    txt = await callListen(call, 120, buttons=tmdb_main_ikb)
    if txt is False:
        return
    if txt.text == '/cancel':
        await asyncio.gather(txt.delete(), editMessage(call, '🔍 已取消操作', buttons=tmdb_main_ikb))
        return

    try:
        index = int(txt.text.strip())
        if index < 1 or index > min(3, len(results)):
            await editMessage(call, 
                f'❌ 编号无效，请输入1-{min(3, len(results))}之间的数字', 
                buttons=tmdb_main_ikb
            )
            return
        
        selected_item = results[index - 1]
        await txt.delete()
        
        # 显示选中的影片详情
        await show_tmdb_item_details(call, selected_item)
        
    except ValueError:
        await editMessage(call, '❌ 请输入有效的数字编号', buttons=tmdb_main_ikb)
    except Exception as e:
        LOGGER.error(f"选择TMDB影片出错: {str(e)}")
        await editMessage(call, '❌ 选择过程中出错', buttons=tmdb_main_ikb)


async def show_tmdb_item_details(call, item: dict):
    """显示选中影片的详细信息，不发送图片，仅文本"""
    title = item.get("title", "未知标题")
    original_title = item.get("original_title", "")
    year = item.get("year", "未知")
    media_type = item.get("media_type_cn", "未知")
    overview = item.get("overview", "暂无简介")
    vote_average = item.get("vote_average", 0)
    vote_count = item.get("vote_count", 0)

    # 保存选中的影片信息到用户数据中，用于潜在的点播请求
    user_tmdb_data[call.from_user.id] = {
        'selected_item': item,
        'search_title': f"{title} {year}" if year and year != "未知" else title
    }

    # 构建详情文本
    detail_text = f"🎬 **影片详情**\n\n"
    detail_text += f"📺 **类型**: {media_type}\n"
    detail_text += f"🎭 **标题**: {title}\n"

    if original_title and original_title != title:
        detail_text += f"🔤 **原名**: {original_title}\n"

    if year:
        detail_text += f"📅 **年份**: {year}\n"

    if vote_average > 0:
        stars = "⭐" * min(int(vote_average/2), 5)
        detail_text += f"⭐ **评分**: {vote_average:.1f}/10 {stars}\n"
        detail_text += f"👥 **投票数**: {vote_count:,} 人\n"

    detail_text += f"\n📝 **剧情简介**:\n{overview}\n\n"
    detail_text += "💡 这是TMDB数据库中的影视信息\n"
    detail_text += "如需观看但Emby中没有，可点击\"🎬 点播\"发起请求"

    # 只发送文本，无图片
    await editMessage(
        call,
        detail_text,
        buttons=tmdb_search_result_ikb,
        parse_mode=enums.ParseMode.MARKDOWN
    )


@bot.on_callback_query(filters.regex('^me_request_movie$') & user_in_group_on_filter)
async def me_request_movie(_, call):
    """ME点播独立请求功能"""
    # 检查用户权限
    emby_user = sql_get_emby(tg=call.from_user.id)
    if not emby_user:
        return await editMessage(call, '⚠️ 数据库没有你，请重新 /start录入')
    if emby_user.lv is None or emby_user.lv not in ['a', 'b']:
        return await editMessage(call, '🫡 您没有权限使用此功能', buttons=tmdb_main_ikb)

    user_data = user_tmdb_data.get(call.from_user.id)
    if not user_data or 'selected_item' not in user_data:
        return await callAnswer(call, '❌ 未找到选中的影片信息，请重新搜索', True)
    
    await callAnswer(call, '🎬 点播')
    
    selected_item = user_data['selected_item']
    media_type = selected_item.get('media_type', 'movie')
    
    # 如果是电视剧，显示季数选择
    if media_type == 'tv':
        tv_id = selected_item.get('id')
        if not tv_id:
            await editMessage(call, '❌ 获取电视剧ID失败', buttons=tmdb_main_ikb)
            return
            
        await editMessage(call, '🔍 正在获取电视剧季数信息...', buttons=tmdb_main_ikb)
        
        try:
            success, seasons = await tmdb_service.get_tv_seasons(tv_id)
            if not success or not seasons:
                await editMessage(call, '❌ 无法获取电视剧季数信息', buttons=tmdb_main_ikb)
                return
            
            # 保存季数信息到用户数据
            user_tmdb_data[call.from_user.id]['seasons'] = seasons
            
            # 显示季数选择界面
            await show_season_selection(call, selected_item, seasons)
            return
            
        except Exception as e:
            LOGGER.error(f"获取电视剧季数失败: {str(e)}")
            await editMessage(call, '❌ 获取季数信息时出错', buttons=tmdb_main_ikb)
            return
    
    # 如果是电影，继续原有流程
    await process_movie_request(call, selected_item)


async def show_season_selection(call, tv_series: dict, seasons: list):
    """显示电视剧季数选择界面"""
    title = tv_series.get("title", "未知电视剧")
    year = tv_series.get("year", "未知")
    
    selection_text = f"📺 **电视剧季数选择**\n\n"
    selection_text += f"🎭 **剧名**: {title}\n"
    if year:
        selection_text += f"📅 **年份**: {year}\n"
    selection_text += f"🎬 **总季数**: {len(seasons)} 季\n\n"
    selection_text += "💰 **点播说明**: 每季需要 10 币\n"
    selection_text += "📝 请选择要点播的季数:\n\n"
    
    for season in seasons[:5]:  # 只显示前5季的详细信息
        season_num = season.get('season_number', 0)
        episode_count = season.get('episode_count', 0)
        air_date = season.get('air_date', '')
        year_info = f" ({air_date[:4]})" if air_date else ""
        
        selection_text += f"🎬 **第{season_num}季**: {episode_count}集{year_info}\n"
    
    if len(seasons) > 5:
        selection_text += f"... 还有 {len(seasons) - 5} 季\n"
    
    await editMessage(
        call,
        selection_text,
        buttons=tmdb_season_selection_ikb(seasons),
        parse_mode=enums.ParseMode.MARKDOWN
    )


async def process_movie_request(call, selected_item: dict):
    """处理电影点播请求"""
    search_title = user_tmdb_data.get(call.from_user.id, {}).get('search_title', '')
    
    # 检查影片是否已经被点播
    movie_title = selected_item.get('title', '未知')
    existing_request = sql_check_existing_request_by_title(movie_title)
    
    if existing_request:
        # 如果影片已在点播库中，显示提示信息
        status_text = "未知状态"
        if existing_request.transfer_state is not None:
            if existing_request.transfer_state:
                status_text = "已入库 📽️"
            else:
                status_text = "入库失败 🚫"
        elif existing_request.download_state:
            if existing_request.download_state == 'pending':
                status_text = "等待下载 ⏳"
            elif existing_request.download_state == 'downloading':
                progress = existing_request.progress or 0
                status_text = f"正在下载 📥 ({progress:.1f}%)"
            elif existing_request.download_state == 'completed':
                status_text = "下载完成 ✅"
            elif existing_request.download_state == 'failed':
                status_text = "下载失败 ❌"
        
        await editMessage(call,
            f"⚠️ **此影片已被点播**\n\n"
            f"影片：{existing_request.request_name}\n"
            f"状态：{status_text}\n"
            f"请求时间：{existing_request.create_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"请求ID：`{existing_request.download_id}`\n\n"
            f"💡 影片已在点播库中，请耐心等待或联系管理员查看进度",
            buttons=tmdb_main_ikb,
            parse_mode=enums.ParseMode.MARKDOWN
        )
        return
    
    # 获取用户信息以检查余额
    emby_user = sql_get_emby(tg=call.from_user.id)
    if not emby_user:
        await editMessage(call, '❌ 用户信息获取失败，请重试', buttons=tmdb_main_ikb)
        return
    
    # 计算费用
    media_type = selected_item.get('media_type', 'movie')
    cost = calculate_me_request_cost(media_type)
    
    # 检查用户余额
    if cost > emby_user.iv:
        await editMessage(call,
            f"❌ **余额不足**\n\n"
            f"影片：{selected_item.get('title', '未知')}\n"
            f"类型：{selected_item.get('media_type_cn', '未知')}\n"
            f"需要费用：{cost} {sakura_b}\n"
            f"当前拥有：{emby_user.iv} {sakura_b}",
            buttons=tmdb_main_ikb,
            parse_mode=enums.ParseMode.MARKDOWN
        )
        return
    
    # 创建确认按钮
    from bot.func_helper.fix_bottons import ikb
    confirm_buttons = ikb([
        [('✅ 确认', 'confirm_me_request'), ('❌ 取消', 'cancel_tmdb_search')],
        [('🔙 返回', 'return_to_search_results')]
    ])

    await editMessage(call,
        f"🎬 **确认点播**\n\n"
        f"影片：{selected_item.get('title', '未知')}\n"
        f"年份：{selected_item.get('year', '未知')}\n"
        f"类型：{selected_item.get('media_type_cn', '未知')}\n\n"
        f"点播费用: {cost} {sakura_b}\n"
        f"当前余额: {emby_user.iv} {sakura_b}\n"
        f"确认点播吗？",
        buttons=confirm_buttons,
        parse_mode=enums.ParseMode.MARKDOWN
    )


@bot.on_callback_query(filters.regex('^select_season_[0-9]+$') & user_in_group_on_filter)
async def select_season(_, call):
    """选择电视剧季数"""
    user_data = user_tmdb_data.get(call.from_user.id)
    if not user_data or 'selected_item' not in user_data or 'seasons' not in user_data:
        return await callAnswer(call, '❌ 搜索会话已过期，请重新搜索', True)
    
    # 提取季数编号
    season_number = int(call.data.split('_')[-1])
    
    await callAnswer(call, f'✅ 选择第{season_number}季')
    
    # 找到对应的季数信息
    selected_season = None
    for season in user_data['seasons']:
        if season.get('season_number') == season_number:
            selected_season = season
            break
    
    if not selected_season:
        await editMessage(call, '❌ 选择的季数不存在', buttons=tmdb_main_ikb)
        return
    
    # 保存选中的季数信息
    user_tmdb_data[call.from_user.id]['selected_season'] = selected_season
    
    # 显示季数确认页面
    await show_season_confirmation(call, user_data['selected_item'], selected_season)


async def show_season_confirmation(call, tv_series: dict, season: dict):
    """显示电视剧季数确认页面"""
    emby_user = sql_get_emby(tg=call.from_user.id)
    if not emby_user:
        await editMessage(call, '❌ 用户信息获取失败，请重试', buttons=tmdb_main_ikb)
        return
    
    season_number = season.get('season_number', 0)
    episode_count = season.get('episode_count', 0)
    air_date = season.get('air_date', '')
    cost = calculate_me_request_cost('tv')  # 电视剧每季10币
    
    # 检查用户余额
    if cost > emby_user.iv:
        await editMessage(call,
            f"❌ **余额不足**\n\n"
            f"电视剧：{tv_series.get('title', '未知')}\n"
            f"季数：第{season_number}季\n"
            f"需要费用：{cost} {sakura_b}\n"
            f"当前拥有：{emby_user.iv} {sakura_b}",
            buttons=tmdb_main_ikb,
            parse_mode=enums.ParseMode.MARKDOWN
        )
        return
    
    # 创建确认按钮
    from bot.func_helper.fix_bottons import ikb
    confirm_buttons = ikb([
        [('✅ 确认', 'confirm_season_request'), ('❌ 取消', 'cancel_tmdb_search')],
        [('🔙 返回', 'return_to_search_results')]
    ])
    
    confirmation_text = f"📺 **确认点播电视剧**\n\n"
    confirmation_text += f"🎭 **剧名**: {tv_series.get('title', '未知')}\n"
    confirmation_text += f"📅 **年份**: {tv_series.get('year', '未知')}\n"
    confirmation_text += f"🎬 **季数**: 第{season_number}季"
    if episode_count > 0:
        confirmation_text += f" ({episode_count}集)"
    if air_date:
        confirmation_text += f"\n📺 **播出年份**: {air_date[:4]}"
    
    confirmation_text += f"\n\n💰 **点播费用**: {cost} {sakura_b}\n"
    confirmation_text += f"💳 **当前余额**: {emby_user.iv} {sakura_b}\n\n"
    confirmation_text += "确认点播此季吗？"

    await editMessage(call,
        confirmation_text,
        buttons=confirm_buttons,
        parse_mode=enums.ParseMode.MARKDOWN
    )


@bot.on_callback_query(filters.regex('^confirm_season_request$') & user_in_group_on_filter)
async def confirm_season_request(_, call):
    """确认电视剧季数点播请求"""
    user_data = user_tmdb_data.get(call.from_user.id)
    if not user_data or 'selected_item' not in user_data or 'selected_season' not in user_data:
        return await callAnswer(call, '❌ 未找到选中的剧集信息，请重新搜索', True)
    
    await callAnswer(call, '📝 正在处理季数点播请求...')
    
    selected_item = user_data['selected_item']
    selected_season = user_data['selected_season']
    season_number = selected_season.get('season_number', 0)
    
    try:
        # 重新获取用户信息以确保余额准确
        emby_user = sql_get_emby(tg=call.from_user.id)
        if not emby_user:
            await editMessage(call, '❌ 用户信息获取失败，请重试', buttons=tmdb_main_ikb)
            return
            
        # 计算费用
        cost = calculate_me_request_cost('tv')  # 电视剧每季10币
        
        # 再次检查余额（防止并发问题）
        if cost > emby_user.iv:
            await editMessage(call,
                f"❌ **余额不足**\n\n"
                f"当前余额：{emby_user.iv} {sakura_b}\n"
                f"需要费用：{cost} {sakura_b}",
                buttons=tmdb_main_ikb
            )
            return
        
        # 生成唯一的请求ID
        request_id = f"ME{datetime.datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8]}"
        
        # 创建请求标题 - 包含季数信息
        tv_title = selected_item.get('title', '未知')
        tv_year = selected_item.get('year', '未知')
        request_title = f"{tv_title} 第{season_number}季 ({tv_year})"
        
        # 检查该季是否已经被点播
        existing_request = sql_check_existing_request_by_title(request_title)
        if existing_request:
            await editMessage(call,
                f"⚠️ **此季已被点播**\n\n"
                f"剧集：{existing_request.request_name}\n"
                f"请求时间：{existing_request.create_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"请求ID：`{existing_request.download_id}`\n\n"
                f"💡 该季已在点播库中，请耐心等待或联系管理员查看进度",
                buttons=tmdb_main_ikb,
                parse_mode=enums.ParseMode.MARKDOWN
            )
            return
        
        request_detail = (
            f"【ME点播 - 电视剧】\n"
            f"用户: [{call.from_user.first_name}](tg://user?id={call.from_user.id})\n"
            f"TG ID: {call.from_user.id}\n"
            f"剧集: {request_title}\n"
            f"原名: {selected_item.get('original_title', '未知')}\n"
            f"类型: 电视剧\n"
            f"季数: 第{season_number}季\n"
            f"集数: {selected_season.get('episode_count', '未知')}集\n"
            f"年份: {selected_item.get('year', '未知')}\n"
            f"TMDB评分: {selected_item.get('vote_average', 0)}/10\n"
            f"请求时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"TMDB ID: {selected_item.get('id', '未知')}"
        )
        
        # 扣除费用
        success_deduct = sql_update_emby(Emby.tg == call.from_user.id, iv=emby_user.iv - cost)
        
        if not success_deduct:
            await editMessage(call,
                f"❌ **扣费失败**\n\n"
                f"请稍后重试或联系管理员",
                buttons=tmdb_main_ikb
            )
            return
        
        # 记录请求到数据库
        success = sql_add_request_record(call.from_user.id, request_id, request_title, request_detail, str(cost))
        
        if success:
            # 发送成功消息给用户
            await editMessage(call,
                f"✅ **电视剧季数点播已提交！**\n\n"
                f"剧集: {tv_title}\n"
                f"季数: 第{season_number}季\n"
                f"集数: {selected_season.get('episode_count', '未知')}集\n"
                f"类型: 电视剧\n"
                f"请求ID: `{request_id}`\n"
                f"费用: {cost} {sakura_b}\n"
                f"余额: {emby_user.iv - cost} {sakura_b}\n",
                buttons=tmdb_main_ikb,
                parse_mode=enums.ParseMode.MARKDOWN
            )
            
            # 发送通知给管理员和owner
            admin_notification = (
                f"📺 **ME点播新请求 - 电视剧季数**\n\n"
                f"**用户**: [{call.from_user.first_name}](tg://user?id={call.from_user.id})\n"
                f"**TG ID**: `{call.from_user.id}`\n"
                f"**剧集**: {tv_title}\n"
                f"**季数**: 第{season_number}季 ({selected_season.get('episode_count', '未知')}集)\n"
                f"**原名**: {selected_item.get('original_title', '未知')}\n"
                f"**年份**: {selected_item.get('year', '未知')}\n"
                f"**TMDB评分**: {selected_item.get('vote_average', 0):.1f}/10\n"
                f"**请求ID**: `{request_id}`\n"
                f"**TMDB ID**: {selected_item.get('id', '未知')}\n\n"
                f"⏰ **请求时间**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            # 发送给owner
            try:
                await sendMessage(call, admin_notification, send=True, chat_id=owner, parse_mode=enums.ParseMode.MARKDOWN)
                LOGGER.info(f"ME点播季数通知已发送给owner: {request_title}")
            except Exception as e:
                LOGGER.error(f"发送ME点播季数通知给owner失败: {str(e)}")
            
            # 发送给所有管理员
            for admin_id in admins:
                try:
                    await sendMessage(call, admin_notification, send=True, chat_id=admin_id, parse_mode=enums.ParseMode.MARKDOWN)
                    LOGGER.info(f"ME点播季数通知已发送给管理员 {admin_id}: {request_title}")
                except Exception as e:
                    LOGGER.error(f"发送ME点播季数通知给管理员 {admin_id} 失败: {str(e)}")
            
            LOGGER.info(f"ME点播季数请求成功: 用户{call.from_user.id} 请求 {request_title}, 费用{cost}{sakura_b}, 请求ID: {request_id}")
            
        else:
            # 记录请求失败，需要退还费用
            sql_update_emby(Emby.tg == call.from_user.id, iv=emby_user.iv)
            await editMessage(call,
                f"❌ **请求提交失败**\n\n"
                f"数据库记录失败，费用已退还\n"
                f"请稍后重试或联系管理员",
                buttons=tmdb_main_ikb
            )
            LOGGER.error(f"ME点播季数请求失败: 用户{call.from_user.id} 数据库记录失败 {request_title}，费用已退还")
    
    except Exception as e:
        LOGGER.error(f"ME点播季数处理出错: {str(e)}")
        # 尝试退还费用（如果已扣除）
        try:
            emby_user = sql_get_emby(tg=call.from_user.id)
            if emby_user:
                sql_update_emby(Emby.tg == call.from_user.id, iv=emby_user.iv + cost)
        except:
            pass
        await editMessage(call,
            f"❌ **处理请求时出错**\n\n"
            f"请稍后重试或联系管理员\n"
            f"如有费用扣除，系统已尝试退还\n"
            f"错误信息: {str(e)[:100]}",
            buttons=tmdb_main_ikb
        )
    finally:
        # 清理用户数据
        user_tmdb_data.pop(call.from_user.id, None)


@bot.on_callback_query(filters.regex('^confirm_me_request$') & user_in_group_on_filter)
async def confirm_me_request(_, call):
    """确认ME点播请求"""
    user_data = user_tmdb_data.get(call.from_user.id)
    if not user_data or 'selected_item' not in user_data:
        return await callAnswer(call, '❌ 未找到选中的影片信息，请重新搜索', True)
    
    await callAnswer(call, '📝 正在处理请求...')
    
    selected_item = user_data['selected_item']
    search_title = user_data['search_title']
    
    try:
        # 重新获取用户信息以确保余额准确
        emby_user = sql_get_emby(tg=call.from_user.id)
        if not emby_user:
            await editMessage(call, '❌ 用户信息获取失败，请重试', buttons=tmdb_main_ikb)
            return
            
        # 计算费用
        media_type = selected_item.get('media_type', 'movie')
        cost = calculate_me_request_cost(media_type)
        
        # 再次检查余额（防止并发问题）
        if cost > emby_user.iv:
            await editMessage(call,
                f"❌ **余额不足**\n\n"
                f"当前余额：{emby_user.iv} {sakura_b}\n"
                f"需要费用：{cost} {sakura_b}",
                buttons=tmdb_main_ikb
            )
            return
        
        # 生成唯一的请求ID
        request_id = f"ME{datetime.datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8]}"
        
        # 创建请求记录
        request_title = f"{selected_item.get('title', '未知')} ({selected_item.get('year', '未知')})"
        
        request_detail = (
            f"【ME点播】\n"
            f"用户: [{call.from_user.first_name}](tg://user?id={call.from_user.id})\n"
            f"TG ID: {call.from_user.id}\n"
            f"影片: {request_title}\n"
            f"原名: {selected_item.get('original_title', '未知')}\n"
            f"类型: {selected_item.get('media_type_cn', '未知')}\n"
            f"年份: {selected_item.get('year', '未知')}\n"
            f"TMDB评分: {selected_item.get('vote_average', 0)}/10\n"
            f"请求时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"TMDB ID: {selected_item.get('id', '未知')}"
        )
        
        # 扣除费用
        success_deduct = sql_update_emby(Emby.tg == call.from_user.id, iv=emby_user.iv - cost)
        
        if not success_deduct:
            await editMessage(call,
                f"❌ **扣费失败**\n\n"
                f"请稍后重试或联系管理员",
                buttons=tmdb_main_ikb
            )
            return
        
        # 记录请求到数据库 (使用实际费用作为成本)
        success = sql_add_request_record(call.from_user.id, request_id, request_title, request_detail, str(cost))
        
        if success:
            # 发送成功消息给用户
            await editMessage(call,
                f"✅ **点播已提交！**\n\n"
                f"影片: {request_title}\n"
                f"类型: {selected_item.get('media_type_cn', '未知')}\n"
                f"请求ID: `{request_id}`\n"
                f"费用: {cost} {sakura_b}\n"
                f"余额: {emby_user.iv - cost} {sakura_b}\n",
                buttons=tmdb_main_ikb,
                parse_mode=enums.ParseMode.MARKDOWN
            )
            
            # 发送通知给管理员和owner
            admin_notification = (
                f"🎬 **ME点播新请求**\n\n"
                f"**用户**: [{call.from_user.first_name}](tg://user?id={call.from_user.id})\n"
                f"**TG ID**: `{call.from_user.id}`\n"
                f"**影片**: {request_title}\n"
                f"**原名**: {selected_item.get('original_title', '未知')}\n"
                f"**类型**: {selected_item.get('media_type_cn', '未知')}\n"
                f"**年份**: {selected_item.get('year', '未知')}\n"
                f"**TMDB评分**: {selected_item.get('vote_average', 0):.1f}/10\n"
                f"**请求ID**: `{request_id}`\n"
                f"**TMDB ID**: {selected_item.get('id', '未知')}\n\n"
                f"⏰ **请求时间**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"📝 **简介**: {selected_item.get('overview', '暂无简介')[:200]}{'...' if len(selected_item.get('overview', '')) > 200 else ''}"
            )
            
            # 发送给owner
            try:
                await sendMessage(call, admin_notification, send=True, chat_id=owner, parse_mode=enums.ParseMode.MARKDOWN)
                LOGGER.info(f"ME点播通知已发送给owner: {request_title}")
            except Exception as e:
                LOGGER.error(f"发送ME点播通知给owner失败: {str(e)}")
            
            # 发送给所有管理员
            for admin_id in admins:
                try:
                    await sendMessage(call, admin_notification, send=True, chat_id=admin_id, parse_mode=enums.ParseMode.MARKDOWN)
                    LOGGER.info(f"ME点播通知已发送给管理员 {admin_id}: {request_title}")
                except Exception as e:
                    LOGGER.error(f"发送ME点播通知给管理员 {admin_id} 失败: {str(e)}")
            
            LOGGER.info(f"ME点播请求成功: 用户{call.from_user.id} 请求 {request_title}, 费用{cost}{sakura_b}, 请求ID: {request_id}")
            
        else:
            # 记录请求失败，需要退还费用
            sql_update_emby(Emby.tg == call.from_user.id, iv=emby_user.iv)
            await editMessage(call,
                f"❌ **请求提交失败**\n\n"
                f"数据库记录失败，费用已退还\n"
                f"请稍后重试或联系管理员",
                buttons=tmdb_main_ikb
            )
            LOGGER.error(f"ME点播请求失败: 用户{call.from_user.id} 数据库记录失败 {request_title}，费用已退还")
    
    except Exception as e:
        LOGGER.error(f"ME点播处理出错: {str(e)}")
        # 尝试退还费用（如果已扣除）
        try:
            emby_user = sql_get_emby(tg=call.from_user.id)
            if emby_user:
                sql_update_emby(Emby.tg == call.from_user.id, iv=emby_user.iv + cost)
        except:
            pass
        await editMessage(call,
            f"❌ **处理请求时出错**\n\n"
            f"请稍后重试或联系管理员\n"
            f"如有费用扣除，系统已尝试退还\n"
            f"错误信息: {str(e)[:100]}",
            buttons=tmdb_main_ikb
        )
    finally:
        # 清理用户数据
        user_tmdb_data.pop(call.from_user.id, None)


@bot.on_callback_query(filters.regex('^tmdb_view_details$') & user_in_group_on_filter)
async def tmdb_view_details(_, call):
    """查看更多详情（扩展功能预留）"""
    await callAnswer(call, '📖 查看详情')
    from bot.func_helper.fix_bottons import ikb
    back_buttons = ikb([[('🔙 返回', 'tmdb_main')]])
    await editMessage(call, 
        '📖 **功能说明**\n\n'
        '当前显示的已经是该影片的详细信息\n'
        '包含了标题、年份、评分、简介等内容\n\n'
        '🔄 你可以返回继续搜索其他影片',
        buttons=back_buttons,
        parse_mode=enums.ParseMode.MARKDOWN
    )


@bot.on_callback_query(filters.regex('^cancel_tmdb_search$') & user_in_group_on_filter)
async def cancel_tmdb_search(_, call):
    """取消TMDB搜索"""
    await callAnswer(call, '❌ 取消搜索')
    # 清除用户的TMDB搜索记录
    user_tmdb_data.pop(call.from_user.id, None)
    await editMessage(call, '🔍 已取消TMDB搜索', buttons=tmdb_main_ikb)


@bot.on_callback_query(filters.regex('^return_to_search_results$') & user_in_group_on_filter)
async def return_to_search_results(_, call):
    """返回到搜索结果页面"""
    user_data = user_tmdb_data.get(call.from_user.id)
    if not user_data or 'query' not in user_data:
        # 如果没有搜索数据，返回主页面
        await callAnswer(call, '🔙 返回主页')
        await editMessage(call, '🔍 搜索会话已过期', buttons=tmdb_main_ikb)
        return
    
    await callAnswer(call, '🔙 返回搜索结果')
    # 重新显示搜索结果页面
    query = user_data['query']
    current_page = user_data.get('current_page', 1)
    await tmdb_search_results(call, query, current_page)
