"""
TMDB trending and popular commands
/trend - Get daily trending movies and TV shows from TMDB (10 items)
/popular - Get popular (streaming) movies and TV shows from TMDB (10 items)
"""

from pyrogram import filters
from bot import bot, prefixes, LOGGER, tmdb
from bot.func_helper.filters import user_in_group_on_filter
from bot.func_helper.msg_utils import sendMessage, deleteMessage
from bot.func_helper.tmdb import tmdb_service


def format_media_item(item: dict, index: int) -> str:
    """Format a single media item for display"""
    title = item.get("title", "未知标题")
    original_title = item.get("original_title", "")
    year = item.get("year", "未知")
    media_type = item.get("media_type_cn", "未知")
    vote_average = item.get("vote_average", 0)
    
    text = f"**{index}.** 🎬 {title}"
    if original_title and original_title != title:
        text += f" ({original_title})"
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
        
        # Format the response
        text = "🔥 **TMDB 今日趋势 (每日)**\n\n"
        for idx, item in enumerate(results, 1):
            text += format_media_item(item, idx)
        
        text += f"\n📊 共 {len(results)} 条结果"
        
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
        
        # Format the response
        text = "🌟 **TMDB 流行内容 (流媒体)**\n\n"
        for idx, item in enumerate(results, 1):
            text += format_media_item(item, idx)
        
        text += f"\n📊 共 {len(results)} 条结果"
        
        await sendMessage(msg, text, timer=120)
        
    except Exception as e:
        LOGGER.error(f"处理 /popular 命令时出错: {str(e)}")
        await sendMessage(msg, f"❌ 获取流行内容失败: {str(e)[:50]}", timer=30)
