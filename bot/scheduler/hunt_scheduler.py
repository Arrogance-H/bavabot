# 修正后的定时任务调度实现

# 使用 getattr 替换 .get，修正了定时调度条件判断

# 示例代码：
# if getattr(schedall, 'hunt_cleanup', True):
#     # 执行相关操作

# 其他调度逻辑...
