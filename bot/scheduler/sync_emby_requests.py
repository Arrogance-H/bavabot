"""
定时检查请求库中的影片是否已添加到Emby库中
如果Emby库中已有该影片，则自动更新请求状态为已入库
"""

from bot import LOGGER, config, bot, emby_url, emby_api
from bot.func_helper.emby import EmbyUtils
from bot.sql_helper.sql_request_record import (
    sql_get_request_records_by_state, 
    sql_update_request_status
)
from bot.func_helper.scheduler import scheduler


async def check_emby_requests():
    """检查请求库中的影片是否已添加到Emby库中"""
    try:
        # 检查Emby配置是否可用
        if not emby_url or not emby_api:
            LOGGER.warning("[Emby Request Check] Emby配置未启用，跳过检查")
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
        
        # 创建Emby工具实例
        emby_utils = EmbyUtils()
        updated_count = 0
        
        for request in all_requests:
            try:
                # 在Emby库中搜索影片
                movies = await emby_utils.get_movies(title=request.request_name, limit=5)
                
                if movies and len(movies) > 0:
                    # 找到匹配的影片，检查是否为电影类型
                    found_movie = False
                    for movie in movies:
                        if movie.get('item_type') == 'Movie':
                            # 简单的名称匹配检查
                            movie_name = movie.get('item_name', '').lower()
                            request_name = request.request_name.lower()
                            
                            # 如果名称相似度较高，认为找到了匹配的影片
                            if (request_name in movie_name or 
                                movie_name in request_name or
                                # 移除常见的年份、标点符号进行比较
                                request_name.replace(' ', '').replace('(', '').replace(')', '') in 
                                movie_name.replace(' ', '').replace('(', '').replace(')', '')):
                                
                                found_movie = True
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
                            LOGGER.info(f"[Emby Request Check] 发现影片已入库，更新状态: {request.request_name} ({request.download_id})")
                            
                            # 发送通知给用户
                            try:
                                await bot.send_message(
                                    chat_id=request.tg,
                                    text=f"🎉 您点播的影片「{request.request_name}」已自动检测到已入库！\n\n"
                                         f"📺 现在可以在Emby中观看了\n"
                                         f"🆔 请求ID: {request.download_id}"
                                )
                            except Exception as e:
                                LOGGER.error(f"[Emby Request Check] 发送通知失败 {request.tg}: {str(e)}")
                        else:
                            LOGGER.error(f"[Emby Request Check] 更新状态失败: {request.download_id}")
                            
            except Exception as e:
                LOGGER.error(f"[Emby Request Check] 检查请求失败 {request.download_id}: {str(e)}")
                continue
        
        if updated_count > 0:
            LOGGER.info(f"[Emby Request Check] 本次检查完成，更新了 {updated_count} 个请求状态")
        else:
            LOGGER.debug("[Emby Request Check] 本次检查完成，没有发现新入库的影片")
            
    except Exception as e:
        LOGGER.error(f"[Emby Request Check] 检查任务执行失败: {str(e)}")


# 添加定时任务 - 每30分钟检查一次
if emby_url and emby_api:
    scheduler.add_job(
        check_emby_requests, 
        'interval', 
        minutes=30, 
        id='check_emby_requests',
        max_instances=1  # 确保不会重复执行
    )
    LOGGER.info("[Emby Request Check] 已添加Emby请求检查定时任务 (每30分钟执行一次)")
else:
    LOGGER.warning("[Emby Request Check] Emby配置未启用，跳过添加定时任务")