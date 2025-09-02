# 红包封面生成指南 - Red Envelope Cover Generation Guide

## 概述 - Overview

本文档详细说明了红包封面 (红包封面) 的生成过程和来源，回答了"red_envelope.py红包封面是从哪里获取的"这个问题。

This document provides a detailed explanation of the red envelope cover generation process and sources, answering the question "Where are the red envelope covers obtained from in red_envelope.py".

## 红包封面生成流程 - Red Envelope Cover Generation Flow

### 1. 主要调用路径 - Main Call Path

```
red_envelope.py (send_red_envelope函数) 
    ↓
RanksDraw.hb_test_draw() (bot/ranks_helper/ranks_draw.py)
    ↓
生成最终的红包封面图片
```

### 2. 核心函数位置 - Core Function Location

- **主要生成函数**: `bot/ranks_helper/ranks_draw.py` 中的 `hb_test_draw()` 方法
- **调用位置**: `bot/modules/extra/red_envelope.py` 中的 `send_red_envelope()` 函数

### 3. 红包封面组成要素 - Red Envelope Cover Components

#### 3.1 背景图片 - Background Images

**来源路径**: `bot/ranks_helper/red/bg/`

**可用背景图片**:
- bg01.JPG
- bg02.JPG  
- rbg01.png
- rbg02.png
- rbg03.png
- rbg04.png
- rbg05.png
- rbg06.png
- rbg07.png

**选择机制**: 系统使用 `random.choice()` 从以上图片中随机选择一个作为红包封面背景

#### 3.2 用户头像处理 - User Avatar Processing

**头像获取**:
```python
# 在 red_envelope.py 中
user_pic = await get_user_photo(msg.from_user)
```

**处理过程**:
1. 通过 `bot.download_media()` 下载用户的Telegram大尺寸头像
2. 转换为RGBA格式并调整为300x300像素
3. 应用圆角遮罩 (`bot/ranks_helper/red/red_mask.png`)
4. 与背景色融合处理

#### 3.3 文字内容 - Text Content

**文字元素**:
- 用户姓名 + "红包" (位置: 图片中心, Y=550)
- 金额/份数 "money / members" (位置: 图片中心, Y=图片高度-100)

**字体文件**:
- 粗体字体: `bot/ranks_helper/resource/font/PingFang Bold.ttf`
- 数字字体: `bot/ranks_helper/resource/font/Provicali.otf`

**文字颜色**: RGB(249, 219, 160) - 金黄色

## 详细代码分析 - Detailed Code Analysis

### 类变量定义 - Class Variable Definitions

```python
class RanksDraw:
    # 红包背景图片目录
    red_bg_path = os.path.join('bot', 'ranks_helper', 'red', 'bg')
    
    # 获取目录中所有背景图片文件列表
    red_bg_list = os.listdir(red_bg_path)
    
    # 用户头像圆角遮罩
    red_mask = Image.open(os.path.join('bot', 'ranks_helper', 'red', 'red_mask.png')).convert('RGBA')
```

### 封面生成函数 - Cover Generation Function

```python
async def hb_test_draw(money: int, members: int, user_pic: bytes = None, first_name: str = None):
    # 1. 随机选择背景图片
    red_bg = os.path.join(RanksDraw.red_bg_path, random.choice(RanksDraw.red_bg_list))
    
    # 2. 如果没有用户头像，只生成背景+文字
    if not user_pic:
        cover = Image.open(red_bg)
        cover = await draw_cover_text(cover, first_name, money, members)
        # 返回字节流
        
    # 3. 如果有用户头像，生成背景+头像+文字
    else:
        # 处理用户头像（调整大小、应用遮罩等）
        # 将头像贴到背景图片上
        # 添加文字内容
```

## 红包类型差异 - Red Envelope Type Differences

### 普通红包 - Regular Red Envelope
- 使用发送者头像
- 显示发送者姓名

### 专享红包 - Private Red Envelope  
- 使用接收者头像
- 显示 "接收者姓名 专享"

## 自定义背景图片 - Customizing Background Images

如果要添加新的红包背景图片:

1. 将图片文件放入 `bot/ranks_helper/red/bg/` 目录
2. 系统会自动扫描该目录并包含新图片到随机选择列表中
3. 支持的格式: JPG, PNG 等PIL支持的图片格式

## 总结 - Summary

红包封面是通过以下步骤动态生成的:

1. **背景选择**: 从 `bot/ranks_helper/red/bg/` 目录随机选择预设背景图片
2. **头像处理**: 下载并处理用户Telegram头像（如果提供）
3. **文字渲染**: 添加用户姓名和金额信息
4. **图片合成**: 将背景、头像、文字合成为最终的红包封面
5. **输出**: 返回PNG格式的字节流数据

这个系统确保每个红包都有独特的视觉外观，同时保持统一的设计风格。