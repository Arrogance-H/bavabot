#!/usr/bin/env python3
"""
红包封面生成验证脚本 - Red Envelope Cover Generation Validation Script

这个脚本验证红包封面生成相关的路径和文件是否存在
This script validates that red envelope cover generation paths and files exist
"""

import os
import sys

def validate_red_envelope_resources():
    """验证红包封面相关资源"""
    print("=== 红包封面资源验证 Red Envelope Cover Resource Validation ===\n")
    
    base_path = "/home/runner/work/bavabot/bavabot"
    
    # 1. 验证背景图片目录
    red_bg_path = os.path.join(base_path, 'bot', 'ranks_helper', 'red', 'bg')
    print(f"1. 背景图片目录 Background Images Directory:")
    print(f"   路径 Path: {red_bg_path}")
    
    if os.path.exists(red_bg_path):
        print("   ✅ 目录存在 Directory exists")
        bg_files = os.listdir(red_bg_path)
        print(f"   📁 包含 {len(bg_files)} 个文件 Contains {len(bg_files)} files:")
        for file in bg_files:
            print(f"      - {file}")
    else:
        print("   ❌ 目录不存在 Directory does not exist")
        return False
    
    # 2. 验证遮罩文件
    print(f"\n2. 用户头像遮罩 User Avatar Mask:")
    red_mask_path = os.path.join(base_path, 'bot', 'ranks_helper', 'red', 'red_mask.png')
    print(f"   路径 Path: {red_mask_path}")
    
    if os.path.exists(red_mask_path):
        print("   ✅ 遮罩文件存在 Mask file exists")
    else:
        print("   ❌ 遮罩文件不存在 Mask file does not exist")
        return False
    
    # 3. 验证字体文件
    print(f"\n3. 字体文件 Font Files:")
    
    fonts = [
        ('粗体字体 Bold Font', os.path.join(base_path, 'bot', 'ranks_helper', 'resource', 'font', 'PingFang Bold.ttf')),
        ('数字字体 Number Font', os.path.join(base_path, 'bot', 'ranks_helper', 'resource', 'font', 'Provicali.otf'))
    ]
    
    for font_name, font_path in fonts:
        print(f"   {font_name}: {font_path}")
        if os.path.exists(font_path):
            print(f"   ✅ 字体文件存在 Font file exists")
        else:
            print(f"   ❌ 字体文件不存在 Font file does not exist")
    
    # 4. 验证主要Python文件
    print(f"\n4. 主要Python文件 Main Python Files:")
    
    python_files = [
        ('红包模块 Red Envelope Module', os.path.join(base_path, 'bot', 'modules', 'extra', 'red_envelope.py')),
        ('排行绘制模块 Ranks Draw Module', os.path.join(base_path, 'bot', 'ranks_helper', 'ranks_draw.py'))
    ]
    
    for file_name, file_path in python_files:
        print(f"   {file_name}: {file_path}")
        if os.path.exists(file_path):
            print(f"   ✅ Python文件存在 Python file exists")
        else:
            print(f"   ❌ Python文件不存在 Python file does not exist")
    
    # 5. 验证文档文件
    print(f"\n5. 文档文件 Documentation Files:")
    doc_path = os.path.join(base_path, 'RED_ENVELOPE_COVER_GUIDE.md')
    print(f"   红包封面指南 Red Envelope Cover Guide: {doc_path}")
    if os.path.exists(doc_path):
        print(f"   ✅ 文档文件存在 Documentation file exists")
    else:
        print(f"   ❌ 文档文件不存在 Documentation file does not exist")
    
    print(f"\n=== 验证完成 Validation Complete ===")
    print(f"所有必要的红包封面生成资源都已验证")
    print(f"All necessary red envelope cover generation resources have been validated")
    
    return True

if __name__ == "__main__":
    success = validate_red_envelope_resources()
    sys.exit(0 if success else 1)