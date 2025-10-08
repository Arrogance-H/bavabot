"""
定时检查请求库中的影片是否已添加到Emby库中
如果Emby库中已有该影片，则自动更新请求状态为已入库
使用TMDB ID进行精准匹配
"""

import json
import re
from bot import LOGGER, config, bot, emby_url, emby_api, group
from bot.func_helper.emby import emby
from bot.sql_helper.sql_request_record import (
    sql_get_request_records_by_state, 
    sql_update_request_status
)
from bot.sql_helper.sql_emby import sql_get_emby
from bot.func_helper.scheduler import scheduler


def extract_tmdb_id_from_detail(detail: str) -> str:
    """从请求详情中提取TMDB ID"""
    try:
        # 尝试匹配 "TMDB ID: xxxxx" 格式
        tmdb_match = re.search(r'TMDB ID:\s*(\d+)', detail)
        if tmdb_match:
            return tmdb_match.group(1)
        
        # 尝试匹配纯数字格式
        number_match = re.search(r'\b(\d{4,7})\b', detail)
        if number_match:
            return number_match.group(1)
        
        return None
    except Exception as e:
        LOGGER.error(f"提取TMDB ID失败: {str(e)}")
        return None


async def check_emby_requests():
    """检查请求库中的影片是否已添加到Emby库中，使用TMDB ID精准匹配"""
    try:
        # 检查Emby配置是否可用
        if not emby_url or not emby_api:
            LOGGER.warning("[Emby Request Check] Emby配置未启用，跳过检查")
            return
        
        # 检查群组配置
        if not group or len(group) == 0:
            LOGGER.warning("[Emby Request Check] 群组配置未设置，跳过检查")
            return
        
        # 获取所有待处理和处理中的ME点播请求
        pending_requests, _, _, _ = sql_get_request_records_by_state(download_state='pending', limit=100)
        downloading_requests, _, _, _ = sql_get_request_records_by_state(download_state='downloading', limit=100)
        
        # 过滤只处理ME开头的请求
        all_requests = []
        for requests in [pending_requests, downloading_requests]:
            for request in requests:
                if request.download_id.startswith('ME'):
                    all_requests.append(request)
        
        if not all_requests:
            LOGGER.debug("[Emby Request Check] 没有需要检查的ME点播请求")
            return
        
        LOGGER.info(f"[Emby Request Check] 开始检查 {len(all_requests)} 个ME点播请求")
        
        # 使用全局Emby实例
        updated_count = 0
        
        for request in all_requests:
            try:
                # 从请求详情中提取TMDB ID
                tmdb_id = extract_tmdb_id_from_detail(request.detail)
                
                if not tmdb_id:
                    LOGGER.debug(f"[Emby Request Check] 无法提取TMDB ID，跳过: {request.download_id}")
                    continue
                
                # 在Emby库中搜索影片
                movies = await emby.get_movies(title=request.request_name, limit=10)
                
                if movies and len(movies) > 0:
                    # 使用TMDB ID精准匹配
                    found_movie = None
                    for movie in movies:
                        emby_tmdb_id = movie.get('tmdbid')
                        if emby_tmdb_id and str(emby_tmdb_id) == str(tmdb_id):
                            found_movie = movie
                            break
                    
                    if found_movie:
                        # 更新请求状态为已入库
                        success = sql_update_request_status(
                            download_id=request.download_id,
                            download_state='completed',
                            progress=100,
                            left_time='已入库'
                        )
                        
                        if success:
                            updated_count += 1
                            LOGGER.info(f"[Emby Request Check] TMDB ID匹配成功，更新状态: {request.request_name} ({request.download_id}) - TMDB ID: {tmdb_id}")
                            
                            # 获取请求用户信息
                            user_info = sql_get_emby(tg=request.tg)
                            username = user_info.name if user_info else f"用户{request.tg}"
                            
                            # 发送群组通知
                            try:
                                notification_text = (
                                    f"🎉 **ME点播入库**\n\n"
                                    f"🎬 **影片名称**: {request.request_name}\n"
                                    f"📊 **点播状态**: 已入库 ✅\n"
                                    f"👤 **ME用户**: {username}\n"
                                    f"📺 影片已可在Emby中观看！"
                                )
                                
                                await bot.send_message(
                                    chat_id=group[0],
                                    text=notification_text
                                )
                                LOGGER.info(f"[Emby Request Check] 群组通知已发送: {request.request_name}")
                            except Exception as e:
                                LOGGER.error(f"[Emby Request Check] 发送群组通知失败: {str(e)}")
                            
                            # 发送私聊通知给点播用户
                            try:
                                private_notification_text = (
                                    f"🎉 **ME点播入库通知**\n\n"
                                    f"🎬 **影片名称**: {request.request_name}\n"
                                    f"📊 **点播状态**: 已入库 ✅\n"
                                    f"📺 影片已可在Emby中观看！\n\n"
                                    f"感谢您使用ME点播服务！"
                                )
                                
                                await bot.send_message(
                                    chat_id=request.tg,
                                    text=private_notification_text
                                )
                                LOGGER.info(f"[Emby Request Check] 私聊通知已发送给用户 {request.tg}: {request.request_name}")
                            except Exception as e:
                                LOGGER.error(f"[Emby Request Check] 发送私聊通知失败 (用户: {request.tg}): {str(e)}")
                        else:
                            LOGGER.error(f"[Emby Request Check] 更新状态失败: {request.download_id}")
                    else:
                        LOGGER.debug(f"[Emby Request Check] TMDB ID未匹配: {request.request_name} (期望: {tmdb_id})")
                            
            except Exception as e:
                LOGGER.error(f"[Emby Request Check] 检查请求失败 {request.download_id}: {str(e)}")
                continue
        
        if updated_count > 0:
            LOGGER.info(f"[Emby Request Check] 本次检查完成，更新了 {updated_count} 个请求状态")
        else:
            LOGGER.debug("[Emby Request Check] 本次检查完成，没有发现新入库的影片")
            
    except Exception as e:
        LOGGER.error(f"[Emby Request Check] 检查任务执行失败: {str(e)}")


# 自动定时任务已禁用 - 可通过 /demand check 或 /demand scan 手动触发检查
# 原自动任务: 每3小时检查一次 (现已移除)
# if emby_url and emby_api:
#     scheduler.add_job(
#         check_emby_requests, 
#         'interval', 
#         hours=3, 
#         id='check_emby_requests',
#         max_instances=1  # 确保不会重复执行
#     )
#     LOGGER.info("[Emby Request Check] 已添加Emby请求检查定时任务 (每3小时执行一次)")
# else:
#     LOGGER.warning("[Emby Request Check] Emby配置未启用，跳过添加定时任务")

LOGGER.info("[Emby Request Check] 自动定时任务已禁用，请使用 /demand check 或 /demand scan 手动触发检查")
