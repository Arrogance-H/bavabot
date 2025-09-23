"""
ME点播 Panel - TMDB Search with Emby Library Check
First checks Emby library, then provides TMDB search if not found
"""

from pyrogram import filters, enums
from bot import bot, tmdb, moviepilot, bot_photo, LOGGER, sakura_b
from bot.func_helper.msg_utils import callAnswer, editMessage, sendMessage, sendPhoto, callListen
from bot.func_helper.filters import user_in_group_on_filter
from bot.func_helper.fix_bottons import tmdb_main_ikb, tmdb_search_page_ikb, tmdb_search_result_ikb, back_members_ikb
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby
from bot.sql_helper.sql_request_record import sql_add_request_record
from bot.func_helper.tmdb import tmdb_service
from bot.func_helper.emby import emby
from bot.func_helper.moviepilot import search, add_download_task
from bot.func_helper.utils import judge_admins
import asyncio
import math

# 存储TMDB搜索结果的全局字典
user_tmdb_data = {}


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

    await callAnswer(call, 'ME点播')
    welcome_text = (
        "🎬 **ME点播**\n\n"
        "智能影视搜索与观看指引！\n\n"
        "🔍 **功能介绍:**\n"
        "• 优先检查Emby媒体库现有资源\n"
        "• 如已存在，直接指引使用Emby客户端观看\n"
        "• 如不存在，提供TMDB数据库搜索\n"
        "• 查看详细的影视信息和评分\n\n"
        "📖 **使用说明:**\n"
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
        '🎬 **ME点播搜索**\n\n'
        '请在120秒内发送你想搜索的电影或电视剧名称\n'
        '支持中文和外文名称搜索\n\n'
        '🔍 **搜索流程:**\n'
        '1. 优先检查Emby媒体库\n'
        '2. 如不存在，搜索TMDB数据库\n\n'
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
                [('🔍 继续TMDB搜索', 'continue_tmdb_search')],
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
        
        success, results = await tmdb_service.search_multi(query, page)
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

        # 计算分页信息
        has_prev = page > 1
        has_next = len(results) >= 20  # 如果当前页有20个结果，可能还有下一页
        
        # 保存搜索结果
        user_tmdb_data[call.from_user.id] = {
            'query': query,
            'results': results,
            'current_page': page
        }

        # 显示结果
        result_text = f"🎬 **ME点播 - TMDB搜索结果**\n"
        result_text += f"🔍 搜索词: `{query}`\n"
        result_text += f"📄 第 {page} 页 | 共找到 {len(results)} 个结果\n\n"
        
        for index, item in enumerate(results[:10], start=1):  # 只显示前10个结果
            result_text += tmdb_service.format_search_result_text(item, index)
            result_text += "\n" + "─" * 30 + "\n\n"

        # 限制消息长度
        if len(result_text) > 4000:
            result_text = result_text[:3900] + "\n...\n\n📝 结果过长，已截断显示"

        await editMessage(
            call, 
            result_text, 
            buttons=tmdb_search_page_ikb(has_prev, has_next, page),
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


@bot.on_callback_query(filters.regex('^tmdb_select_item$') & user_in_group_on_filter)
async def tmdb_select_item(_, call):
    """选择TMDB影片查看详情"""
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
        '请在120秒内发送你要查看的影片编号（1-10）\n'
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
        if index < 1 or index > min(10, len(results)):
            await editMessage(call, 
                f'❌ 编号无效，请输入1-{min(10, len(results))}之间的数字', 
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
    """显示选中影片的详细信息"""
    title = item.get("title", "未知标题")
    original_title = item.get("original_title", "")
    year = item.get("year", "未知")
    media_type = item.get("media_type_cn", "未知")
    overview = item.get("overview", "暂无简介")
    vote_average = item.get("vote_average", 0)
    vote_count = item.get("vote_count", 0)
    poster_url = item.get("poster_url", "")
    
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
    
    # 根据MoviePilot状态显示不同的提示
    if moviepilot.status:
        detail_text += "💡 这是TMDB数据库中的影视信息\n"
        detail_text += "可以点击\"🎬 点播此片\"发起下载请求"
    else:
        detail_text += "💡 这是TMDB数据库中的影视信息\n"
        detail_text += "如需观看，请查看Emby媒体库或其他观看渠道"
    
    if poster_url:
        # 如果有海报，显示海报
        try:
            await sendPhoto(
                call,
                photo=poster_url,
                caption=detail_text,
                buttons=tmdb_search_result_ikb if moviepilot.status else tmdb_search_result_ikb,
                send=True,
                chat_id=call.from_user.id,
                parse_mode=enums.ParseMode.MARKDOWN
            )
        except:
            # 如果海报加载失败，使用默认图片
            await sendPhoto(
                call,
                photo=bot_photo,
                caption=detail_text,
                buttons=tmdb_search_result_ikb if moviepilot.status else tmdb_search_result_ikb,
                send=True,
                chat_id=call.from_user.id,
                parse_mode=enums.ParseMode.MARKDOWN
            )
    else:
        await sendPhoto(
            call,
            photo=bot_photo,
            caption=detail_text,
            buttons=tmdb_search_result_ikb if moviepilot.status else tmdb_search_result_ikb,
            send=True,
            chat_id=call.from_user.id,
            parse_mode=enums.ParseMode.MARKDOWN
        )


@bot.on_callback_query(filters.regex('^tmdb_view_details$') & user_in_group_on_filter)
async def tmdb_view_details(_, call):
    """查看更多详情（扩展功能预留）"""
    await callAnswer(call, '📖 查看详情')
    await editMessage(call, 
        '📖 **功能说明**\n\n'
        '当前显示的已经是该影片的详细信息\n'
        '包含了标题、年份、评分、简介等内容\n\n'
        '🔄 你可以返回继续搜索其他影片',
        buttons=tmdb_search_result_ikb,
        parse_mode=enums.ParseMode.MARKDOWN
    )


@bot.on_callback_query(filters.regex('^tmdb_request_movie$') & user_in_group_on_filter)
async def tmdb_request_movie(_, call):
    """点播TMDB中选中的影片"""
    if not moviepilot.status:
        return await callAnswer(call, '❌ 管理员未开启点播功能', True)
    
    # 检查用户权限
    emby_user = sql_get_emby(tg=call.from_user.id)
    if not emby_user:
        return await editMessage(call, '⚠️ 数据库没有你，请重新 /start录入')
    if emby_user.lv is None or emby_user.lv not in ['a', 'b']:
        return await editMessage(call, '🫡 您没有权限使用此功能', buttons=tmdb_main_ikb)
    if not judge_admins(emby_user.tg) and moviepilot.lv == 'a' and emby_user.lv != 'a':
        return await editMessage(call, '🫡 您没有权限使用此功能，仅限白名单用户可用', buttons=tmdb_main_ikb)

    user_data = user_tmdb_data.get(call.from_user.id)
    if not user_data or 'selected_item' not in user_data:
        return await callAnswer(call, '❌ 未找到选中的影片信息，请重新搜索', True)
    
    await callAnswer(call, '🎬 开始点播处理')
    
    selected_item = user_data['selected_item']
    search_title = user_data['search_title']
    
    # 显示点播费用并等待确认
    await editMessage(call,
        f"🎬 **确认点播**\n\n"
        f"影片：{selected_item.get('title', '未知')}\n"
        f"年份：{selected_item.get('year', '未知')}\n"
        f"类型：{selected_item.get('media_type_cn', '未知')}\n\n"
        f"💰 **点播费用**: 预估 {moviepilot.price} {sakura_b} (实际费用以资源大小计算)\n"
        f"💳 **您当前拥有**: {emby_user.iv} {sakura_b}\n\n"
        f"⚠️ **注意**: 将使用影片名称在资源站点搜索下载资源\n\n"
        f"确认发起点播请求吗？",
        parse_mode=enums.ParseMode.MARKDOWN
    )
    
    # 创建确认按钮
    from bot.func_helper.fix_bottons import ikb
    confirm_buttons = ikb([
        [('✅ 确认点播', 'confirm_tmdb_request'), ('❌ 取消', 'cancel_tmdb_search')],
        [('🔙 返回', 'tmdb_main')]
    ])
    
    await editMessage(call, call.message.text, buttons=confirm_buttons, parse_mode=enums.ParseMode.MARKDOWN)


@bot.on_callback_query(filters.regex('^confirm_tmdb_request$') & user_in_group_on_filter)
async def confirm_tmdb_request(_, call):
    """确认TMDB影片点播请求"""
    user_data = user_tmdb_data.get(call.from_user.id)
    if not user_data or 'selected_item' not in user_data:
        return await callAnswer(call, '❌ 未找到选中的影片信息，请重新搜索', True)
    
    await callAnswer(call, '🔍 处理点播请求中...')
    
    selected_item = user_data['selected_item']
    search_title = user_data['search_title']
    
    # 使用影片标题搜索资源站点
    await editMessage(call, '🔍 正在资源站点搜索，请稍后...', buttons=tmdb_main_ikb)
    
    try:
        # 使用MoviePilot搜索资源
        success, search_results = await search(search_title)
        
        if not success or not search_results:
            await editMessage(call, 
                f'🤷‍♂️ 未在资源站点找到 "{search_title}" 的下载资源\n\n'
                f'💡 **建议**:\n'
                f'• 影片可能尚未发布资源\n'
                f'• 尝试稍后再次搜索\n'
                f'• 或使用不同的搜索关键词',
                buttons=tmdb_main_ikb,
                parse_mode=enums.ParseMode.MARKDOWN
            )
            return
        
        # 选择最佳资源（按做种数排序，取第一个）
        best_resource = search_results[0]
        
        # 计算费用
        size_in_bytes = int(best_resource.get('size', 0))
        size_in_gb = size_in_bytes / (1024 * 1024 * 1024)
        need_cost = math.ceil(size_in_gb) * moviepilot.price if size_in_gb > 0 else moviepilot.price
        
        # 检查用户余额
        emby_user = sql_get_emby(tg=call.from_user.id)
        if need_cost > emby_user.iv:
            await editMessage(call,
                f"❌ 余额不足！\n\n"
                f"需要费用: {need_cost} {sakura_b}\n"
                f"当前拥有: {emby_user.iv} {sakura_b}\n"
                f"还需要: {need_cost - emby_user.iv} {sakura_b}",
                buttons=tmdb_main_ikb
            )
            return
        
        # 添加下载任务
        torrent_info = best_resource.get('torrent_info', {})
        param = {**torrent_info, 'torrent_in': torrent_info}
        download_success, download_id = await add_download_task(param)
        
        if download_success:
            # 成功添加下载任务
            # 扣除费用
            sql_update_emby(Emby.tg == call.from_user.id, iv=emby_user.iv - need_cost)
            
            # 记录请求
            request_title = f"{selected_item.get('title', '未知')} ({selected_item.get('year', '未知')})"
            log_detail = (f"【ME点播】：#{call.from_user.id} [{call.from_user.first_name}](tg://user?id={call.from_user.id}) "
                         f"通过TMDB搜索点播: {request_title}\n"
                         f"搜索关键词: {search_title}\n"
                         f"资源信息: {best_resource.get('title', '未知')}\n"
                         f"文件大小: {size_in_gb:.2f} GB\n"
                         f"消耗: {need_cost} {sakura_b}\n"
                         f"下载ID: {download_id}")
            
            sql_add_request_record(call.from_user.id, download_id, request_title, log_detail, need_cost)
            
            # 发送成功消息给用户
            await editMessage(call,
                f"🎉 **点播请求成功！**\n\n"
                f"影片: {request_title}\n"
                f"下载ID: `{download_id}`\n"
                f"消耗: {need_cost} {sakura_b}\n"
                f"余额: {emby_user.iv - need_cost} {sakura_b}\n\n"
                f"✅ 已添加到下载队列，请耐心等待处理",
                buttons=tmdb_main_ikb,
                parse_mode=enums.ParseMode.MARKDOWN
            )
            
            # 发送通知给管理员
            if moviepilot.download_log_chatid:
                try:
                    admin_log = (f"🎬 **ME点播新请求**\n\n"
                               f"**用户**: [{call.from_user.first_name}](tg://user?id={call.from_user.id})\n"
                               f"**影片**: {request_title}\n"
                               f"**搜索词**: {search_title}\n"
                               f"**下载ID**: `{download_id}`\n"
                               f"**费用**: {need_cost} {sakura_b}\n"
                               f"**资源**: {best_resource.get('title', '未知')}\n"
                               f"**大小**: {size_in_gb:.2f} GB\n"
                               f"**做种数**: {best_resource.get('seeders', 0)}")
                    
                    await sendMessage(call, admin_log, send=True, chat_id=moviepilot.download_log_chatid, parse_mode=enums.ParseMode.MARKDOWN)
                    LOGGER.info(f"ME点播通知已发送给管理员: {request_title}")
                except Exception as e:
                    LOGGER.error(f"发送ME点播通知到管理员失败: {str(e)}")
            
            LOGGER.info(f"ME点播成功: 用户{call.from_user.id} 点播 {request_title}")
            
        else:
            # 添加下载任务失败
            await editMessage(call,
                f"❌ **添加下载任务失败**\n\n"
                f"影片: {request_title}\n"
                f"请稍后重试或联系管理员",
                buttons=tmdb_main_ikb
            )
            LOGGER.error(f"ME点播失败: 用户{call.from_user.id} 添加下载任务失败 {request_title}")
            
    except Exception as e:
        LOGGER.error(f"ME点播处理出错: {str(e)}")
        await editMessage(call,
            f"❌ **处理点播请求时出错**\n\n"
            f"请稍后重试或联系管理员\n"
            f"错误信息: {str(e)[:100]}",
            buttons=tmdb_main_ikb
        )
    finally:
        # 清理用户数据
        user_tmdb_data.pop(call.from_user.id, None)


@bot.on_callback_query(filters.regex('^cancel_tmdb_search$') & user_in_group_on_filter)
async def cancel_tmdb_search(_, call):
    """取消TMDB搜索"""
    await callAnswer(call, '❌ 取消搜索')
    # 清除用户的TMDB搜索记录
    user_tmdb_data.pop(call.from_user.id, None)
    await editMessage(call, '🔍 已取消TMDB搜索', buttons=tmdb_main_ikb)