"""
TMDB trending and popular commands
/trend - Get daily trending movies and TV shows from TMDB (10 items)
/popular - Get popular (streaming) movies and TV shows from TMDB (10 items)
/search - Search TMDB and request content (e.g., /search 阿凡达)
"""

from datetime import datetime
from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyromod.helpers import ikb
from bot import bot, prefixes, LOGGER, tmdb
from bot.func_helper.filters import user_in_group_on_filter
from bot.func_helper.msg_utils import sendMessage, deleteMessage
from bot.func_helper.tmdb import tmdb_service
from bot.func_helper.fix_bottons import tmdb_search_result_list_ikb, tmdb_main_ikb
from bot.sql_helper.sql_emby import sql_get_emby


def format_media_item(item: dict, index: int) -> str:
    """Format a single media item for display"""
    title = item.get("title", "未知标题")
    year = item.get("year", "未知")
    media_type = item.get("media_type_cn", "未知")
    vote_average = item.get("vote_average", 0)
    
    text = f"**{index}.** {title}"
    text += f"\n   📺 {media_type} | 📅 {year}"
    if vote_average > 0:
        text += f" | ⭐ {vote_average:.1f}"
    text += "\n"
    
    return text


@bot.on_message(filters.command('trend', prefixes) & user_in_group_on_filter)
async def trend_command(_, msg):
    """
    Get daily trending movies and TV shows from TMDB
    """
    try:
        await deleteMessage(msg)
        
        # Check if TMDB is configured
        if not tmdb.api_key:
            await sendMessage(msg, "❌ TMDB API 未配置，请联系管理员设置 TMDB API Key", timer=30)
            return
        
        # Fetch trending content
        success, results = await tmdb_service.get_trending(time_window="day", limit=10)
        
        if not success or not results:
            await sendMessage(msg, "❌ 获取趋势内容失败，请稍后再试", timer=30)
            return
        
        # Format the response with current date
        today = datetime.now().strftime("%Y-%m-%d")
        text = f"🔥 **TMDB 今日趋势 ({today})**\n\n"
        for idx, item in enumerate(results, 1):
            text += format_media_item(item, idx)
        
        await sendMessage(msg, text, timer=120)
        
    except Exception as e:
        LOGGER.error(f"处理 /trend 命令时出错: {str(e)}")
        await sendMessage(msg, f"❌ 获取趋势内容失败: {str(e)[:50]}", timer=30)


@bot.on_message(filters.command('popular', prefixes) & user_in_group_on_filter)
async def popular_command(_, msg):
    """
    Get popular (streaming) movies and TV shows from TMDB
    """
    try:
        await deleteMessage(msg)
        
        # Check if TMDB is configured
        if not tmdb.api_key:
            await sendMessage(msg, "❌ TMDB API 未配置，请联系管理员设置 TMDB API Key", timer=30)
            return
        
        # Fetch popular content
        success, results = await tmdb_service.get_popular(media_type="all", limit=10)
        
        if not success or not results:
            await sendMessage(msg, "❌ 获取流行内容失败，请稍后再试", timer=30)
            return
        
        # Format the response with current date
        today = datetime.now().strftime("%Y-%m-%d")
        text = f"🌟 **TMDB 流行内容 ({today})**\n\n"
        for idx, item in enumerate(results, 1):
            text += format_media_item(item, idx)
        
        await sendMessage(msg, text, timer=120)
        
    except Exception as e:
        LOGGER.error(f"处理 /popular 命令时出错: {str(e)}")
        await sendMessage(msg, f"❌ 获取流行内容失败: {str(e)[:50]}", timer=30)


def format_search_result(item: dict, index: int) -> str:
    """Format a single search result item for display with detailed info"""
    title = item.get("title", "未知标题")
    original_title = item.get("original_title", "")
    year = item.get("year", "未知")
    media_type = item.get("media_type_cn", "未知")
    vote_average = item.get("vote_average", 0)
    vote_count = item.get("vote_count", 0)
    
    text = f"🎬 **编号**: `{index}`\n"
    text += f"📺 **类型**: {media_type}\n"
    text += f"🎭 **标题**: {title}\n"
    
    if original_title and original_title != title:
        text += f"🔤 **原名**: {original_title}\n"
        
    if year:
        text += f"📅 **年份**: {year}\n"
        
    if vote_average > 0:
        stars = "⭐" * min(int(vote_average/2), 5)
        text += f"⭐ **评分**: {vote_average:.1f}/10 {stars} ({vote_count}票)\n"
    
    return text


@bot.on_message(filters.command('search', prefixes) & user_in_group_on_filter)
async def search_command(_, msg):
    """
    Search TMDB and allow users to request content
    Usage: /search 阿凡达
    """
    from bot.modules.panel.tmdb_panel import user_tmdb_data
    
    try:
        await deleteMessage(msg)
        
        # Check if TMDB is configured
        if not tmdb.api_key:
            await sendMessage(msg, "❌ TMDB API 未配置，请联系管理员设置 TMDB API Key", timer=30)
            return
        
        # Check user permission
        emby_user = sql_get_emby(tg=msg.from_user.id)
        if not emby_user:
            await sendMessage(msg, "⚠️ 数据库没有你，请先私聊机器人 /start 录入", timer=30)
            return
        if emby_user.lv is None or emby_user.lv not in ['a', 'b', 'm']:
            await sendMessage(msg, "🫡 您没有权限使用此功能", timer=30)
            return
        
        # Extract search query from command
        command_parts = msg.text.split(maxsplit=1)
        if len(command_parts) < 2:
            await sendMessage(msg, 
                "🔍 **TMDB 搜索**\n\n"
                "请提供搜索关键词\n"
                "用法: `/search 阿凡达`\n\n"
                "示例:\n"
                "• `/search 阿凡达`\n"
                "• `/search Avatar`\n"
                "• `/search 19995` (TMDB ID)", 
                timer=60,
                parse_mode=enums.ParseMode.MARKDOWN
            )
            return
        
        search_query = command_parts[1].strip()
        
        if len(search_query) < 2:
            await sendMessage(msg, "❌ 搜索关键词太短，请输入至少2个字符", timer=30)
            return
        
        # Check if the search query is a TMDB ID
        if tmdb_service.is_tmdb_id(search_query):
            tmdb_id = tmdb_service.extract_tmdb_id(search_query)
            
            # Get movie/TV details from TMDB
            success, tmdb_results = await tmdb_service.search_by_tmdb_id(tmdb_id)
            if not success or not tmdb_results:
                await sendMessage(msg, f"🤷‍♂️ TMDB ID {tmdb_id} 未找到对应的影视作品", timer=30)
                return
            
            # Store the results for later use
            user_tmdb_data[msg.from_user.id] = {
                'display_results': tmdb_results,
                'query': f'TMDB ID: {tmdb_id}',
                'total_results': len(tmdb_results),
                'is_tmdb_id_search': True,
                'tmdb_id': tmdb_id
            }
            
            # If only one result, format and display it
            if len(tmdb_results) == 1:
                tmdb_result = tmdb_results[0]
                user_tmdb_data[msg.from_user.id]['selected_item'] = tmdb_result
                user_tmdb_data[msg.from_user.id]['search_title'] = f"{tmdb_result.get('title', '未知')} {tmdb_result.get('year', '')}".strip()
                
                # Format the result
                title = tmdb_result.get("title", "未知标题")
                original_title = tmdb_result.get("original_title", "")
                year = tmdb_result.get("year", "未知")
                media_type = tmdb_result.get("media_type_cn", "未知")
                overview = tmdb_result.get("overview", "暂无简介")
                vote_average = tmdb_result.get("vote_average", 0)
                vote_count = tmdb_result.get("vote_count", 0)
                
                result_text = f"🆔 **TMDB ID 精确查找**\n\n"
                result_text += f"📺 **类型**: {media_type}\n"
                result_text += f"🎭 **标题**: {title}\n"
                
                if original_title and original_title != title:
                    result_text += f"🔤 **原名**: {original_title}\n"
                    
                if year:
                    result_text += f"📅 **年份**: {year}\n"
                    
                if vote_average > 0:
                    stars = "⭐" * min(int(vote_average/2), 5)
                    result_text += f"⭐ **评分**: {vote_average:.1f}/10 {stars} ({vote_count}票)\n"
                
                # Add genres if available
                if tmdb_result.get('genres'):
                    result_text += f"🏷️ **分类**: {tmdb_result['genres']}\n"
                
                # Add runtime/seasons info
                if tmdb_result.get('runtime') and tmdb_result['runtime'] > 0:
                    result_text += f"⏱️ **时长**: {tmdb_result['runtime']} 分钟\n"
                elif tmdb_result.get('number_of_seasons') and tmdb_result['number_of_seasons'] > 0:
                    result_text += f"📺 **季数**: {tmdb_result['number_of_seasons']} 季\n"
                
                # Add overview
                if overview and len(overview) > 200:
                    overview = overview[:197] + "..."
                result_text += f"\n📝 **简介**: {overview}\n\n"
                result_text += "💡 点击下方按钮点播此影片"
                
                # Create keyboard with request button
                # Note: No return button for /search command to prevent photo loss issue
                # The /search command creates a text-only message, not part of the photo-based panel flow
                keyboard = ikb([
                    [('🎬 点播此片', 'me_request_movie')]
                ])
                
                await sendMessage(msg, result_text, buttons=keyboard, parse_mode=enums.ParseMode.MARKDOWN)
            
            else:
                # Multiple results (both movie and TV show found)
                result_text = f"🆔 **TMDB ID 精确查找**\n\n"
                result_text += f"🔍 TMDB ID: `{tmdb_id}`\n"
                result_text += f"✅ 找到 {len(tmdb_results)} 个匹配的影视作品\n\n"
                result_text += f"📺 该ID同时存在电影和电视剧，请选择:\n\n"
                
                # Format each result with detailed info
                for i, item in enumerate(tmdb_results, 1):
                    result_text += format_search_result(item, i)
                    result_text += "\n" + "─" * 10 + "\n\n"
                
                result_text += "💡 点击下方编号选择影片进行点播"
                
                await sendMessage(msg, result_text, buttons=tmdb_search_result_list_ikb(len(tmdb_results)), parse_mode=enums.ParseMode.MARKDOWN)
            
            return
        
        # Regular text search
        all_results = []
        api_page = 1
        max_pages = 3  # Limit API calls
        
        while api_page <= max_pages:
            success, results, pagination_info = await tmdb_service.search_multi(search_query, api_page)
            if not success or not results:
                break
            
            all_results.extend(results)
            
            if api_page >= pagination_info.get("total_pages", 1):
                break
            
            api_page += 1
        
        if not all_results:
            await sendMessage(msg, 
                f"🤷‍♂️ 未找到关键词 \"{search_query}\" 的相关影视作品\n\n"
                f"💡 **搜索建议:**\n"
                f"• 尝试使用不同的关键词\n"
                f"• 使用中文或英文名称\n"
                f"• 检查拼写是否正确", 
                timer=60,
                parse_mode=enums.ParseMode.MARKDOWN
            )
            return
        
        # Only show top 5 results
        MAX_RESULTS = 5
        display_results = all_results[:MAX_RESULTS]
        total_results = len(all_results)
        
        # Store results for later use
        user_tmdb_data[msg.from_user.id] = {
            'query': search_query,
            'display_results': display_results,
            'total_results': total_results,
            'all_results': all_results
        }
        
        # Format results
        result_text = f"🎬 **TMDB 搜索结果**\n"
        result_text += f"🔍 搜索词: `{search_query}`\n"
        result_text += f"📊 显示 {len(display_results)} 个结果"
        if total_results > MAX_RESULTS:
            result_text += f" (共找到 {total_results} 个结果)\n\n"
        else:
            result_text += f"\n\n"
        
        for idx, item in enumerate(display_results, 1):
            result_text += format_search_result(item, idx)
            result_text += "\n" + "─" * 10 + "\n\n"
        
        # Limit message length
        if len(result_text) > 4000:
            result_text = result_text[:3900] + "\n...\n\n📝 结果过长，已截断显示"
        
        result_text += "💡 点击下方编号选择影片进行点播"
        
        await sendMessage(msg, result_text, buttons=tmdb_search_result_list_ikb(len(display_results)), parse_mode=enums.ParseMode.MARKDOWN)
        
    except Exception as e:
        LOGGER.error(f"处理 /search 命令时出错: {str(e)}")
        await sendMessage(msg, f"❌ 搜索失败: {str(e)[:50]}", timer=30)
