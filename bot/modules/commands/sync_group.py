import time

from pyrogram import filters

from bot import bot, prefixes, bot_photo, LOGGER
from bot.func_helper.emby import emby
from bot.func_helper.filters import admins_on_filter, judge_uid_ingroup
from bot.sql_helper.sql_emby import get_all_emby, Emby
from bot.func_helper.msg_utils import deleteMessage, sendMessage


@bot.on_message(filters.command('syncgroupm', prefixes) & admins_on_filter)
async def sync_emby_group(_, msg):
    await deleteMessage(msg)
    send = await bot.send_photo(msg.chat.id, photo=bot_photo,
                                caption="⚡#群组同步任务\n  **正在开启中...消灭未在群组的账户**")
    LOGGER.info(
        f"【群组同步任务开启】 - {msg.from_user.first_name} - {msg.from_user.id}")
    r = get_all_emby(Emby.lv == 'b')
    if r is None:
        return await send.edit("⚡#群组同步任务\n\n结束！搞毛，没有人。")

    b = 0
    a = 0
    start = time.perf_counter()
    for i in r:
        # print(i.tg)
        b += 1
        try:
            if not await judge_uid_ingroup(_, i.tg):
                if await emby.emby_del(i.embyid):
                    a += 1
                    re = await send.reply(
                        f'🎯#未在群组封禁 {b} #id{i.tg}\n已将 [{i.tg}](tg://user?id={i.tg}) 账户 {i.name} 完成删除')
                    await re.forward(i.tg)
                else:
                    await send.reply(
                        f'🎯#未在群组封禁 {b} #id{r[0]}\n[{i.tg}](tg://user?id={i.tg}) 账户 {i.name} 删除错误')
        except:
            continue

    end = time.perf_counter()
    times = end - start
    if a != 0:
        await sendMessage(msg, text=f"**⚡#群组同步任务 结束！**\n  共检索出 {b} 个账户，处刑 {a} 个账户，耗时：{times:.3f}s")
    else:
        await sendMessage(msg, text="**#群组同步任务 结束！没人偷跑~**")
    LOGGER.info(f"【群组同步任务结束】 - {msg.from_user.id} 共检索出 {b} 个账户，处刑 {a} 个账户，耗时：{times:.3f}s")
