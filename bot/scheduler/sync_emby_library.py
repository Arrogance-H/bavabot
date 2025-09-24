from bot import LOGGER, bot, group
from bot.func_helper.emby import emby
from bot.sql_helper.sql_request_record import sql_get_request_records_for_emby_check, sql_update_request_status
from bot.func_helper.scheduler import scheduler


async def sync_emby_library_status():
    """同步Emby库状态，检查点播的影片是否已在Emby中出现"""
    try:
        # 获取需要检查的记录
        records_to_check = sql_get_request_records_for_emby_check()
        
        if not records_to_check:
            LOGGER.debug("[Emby同步] 没有需要检查的记录")
            return
        
        LOGGER.info(f"[Emby同步] 开始检查 {len(records_to_check)} 个记录")
        found_count = 0
        
        for record in records_to_check:
            try:
                # 在Emby中搜索该影片
                emby_results = await emby.get_movies(title=record.request_name, limit=10)
                
                # 检查是否找到匹配的影片
                found_in_emby = False
                if emby_results:
                    # 简单的标题匹配逻辑，可以根据需要优化
                    for emby_item in emby_results:
                        emby_title = emby_item.get('title', '').lower()
                        request_title = record.request_name.lower()
                        
                        # 检查标题匹配度 (包含检查或相似度检查)
                        if (request_title in emby_title or 
                            emby_title in request_title or
                            # 移除常见符号后再比较
                            request_title.replace(' ', '').replace('-', '') in 
                            emby_title.replace(' ', '').replace('-', '')):
                            found_in_emby = True
                            break
                
                if found_in_emby:
                    # 更新状态为已入库
                    sql_update_request_status(
                        download_id=record.download_id,
                        download_state='completed',  # 保持原状态
                        emby_state='stored'
                    )
                    
                    # 发送通知到群组
                    try:
                        notification_text = f"🎉 **影片入库通知**\n\n📽️ 影片：{record.request_name}\n👤 点播用户：[用户](tg://user?id={record.tg})\n✅ 状态：已成功入库到Emby媒体库\n\n请使用Emby客户端观看！"
                        await bot.send_message(chat_id=group[0], text=notification_text)
                        
                        # 也发送私信给点播用户
                        await bot.send_message(chat_id=record.tg, text=f"🎉 恭喜！您点播的「{record.request_name}」已成功入库到Emby媒体库，现在可以观看了！")
                        
                    except Exception as e:
                        LOGGER.error(f"[Emby同步] 发送通知失败: {str(e)}")
                    
                    found_count += 1
                    LOGGER.info(f"[Emby同步] 发现影片已入库: {record.request_name}")
                else:
                    # 影片还未在Emby中找到，保持processing状态
                    LOGGER.debug(f"[Emby同步] 影片尚未在Emby中找到: {record.request_name}")
                    
            except Exception as e:
                LOGGER.error(f"[Emby同步] 检查影片 {record.request_name} 时出错: {str(e)}")
                continue
        
        if found_count > 0:
            LOGGER.info(f"[Emby同步] 本次检查发现 {found_count} 个影片已成功入库")
        else:
            LOGGER.info("[Emby同步] 本次检查未发现新入库的影片")
            
    except Exception as e:
        LOGGER.error(f"[Emby同步] 同步Emby库状态时出错: {str(e)}")


# 添加定时任务，每6小时执行一次
scheduler.add_job(sync_emby_library_status, 'interval', hours=6, id='sync_emby_library_status')