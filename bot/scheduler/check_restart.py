# 重启
from bot import bot, LOGGER, schedall, save_config, auto_update
from pyrogram.errors import BadRequest


# 定义一个检查函数
async def check_restart():
    if schedall.restart_chat_id != 0:
        chat_id, msg_id = schedall.restart_chat_id, schedall.restart_msg_id
        up_description = auto_update.up_description if auto_update.up_description else ""
        text = 'Restarted Successfully!\n\n' + up_description
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text)
            LOGGER.info(f"目标：{chat_id} 消息id：{msg_id} 已提示重启成功")
        except BadRequest:
            try:
                await bot.send_message(chat_id=chat_id, text=text)
                LOGGER.info(f"目标：{chat_id} 消息id：{msg_id} 已提示重启成功（通过新消息）")
            except Exception as e:
                LOGGER.error(f"发送重启消息失败: {e}")
        except Exception as e:
            LOGGER.error(f"编辑重启消息失败: {e}")
            try:
                await bot.send_message(chat_id=chat_id, text=text)
                LOGGER.info(f"目标：{chat_id} 已通过新消息提示重启成功")
            except Exception as e2:
                LOGGER.error(f"发送重启消息也失败: {e2}")
        
        schedall.restart_chat_id = 0
        schedall.restart_msg_id = 0
        auto_update.up_description = None
        save_config()

    else:
        LOGGER.info("未检索到有重启指令，直接启动")
