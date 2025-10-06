#!/usr/bin/env python3
"""
Gemini API 图片 Token 计算工具

用于计算发送到 Gemini API 的图片会消耗多少 tokens
"""

import base64
import sys
from io import BytesIO
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("请先安装 Pillow: pip install Pillow")
    sys.exit(1)


def calculate_image_tokens(width: int, height: int) -> int:
    """
    根据 Gemini API 官方文档计算图片 tokens
    
    公式: tokens = 258 + (宽度 × 高度) / 750
    
    Args:
        width: 图片宽度
        height: 图片高度
    
    Returns:
        估算的 token 数量
    """
    tokens = 258 + (width * height) / 750
    return int(tokens)


def analyze_image_file(image_path: str) -> dict:
    """
    分析图片文件并计算 token 消耗
    
    Args:
        image_path: 图片文件路径
    
    Returns:
        包含图片信息和 token 计算的字典
    """
    try:
        img = Image.open(image_path)
        width, height = img.size
        file_size = Path(image_path).stat().st_size
        
        tokens = calculate_image_tokens(width, height)
        
        return {
            'path': image_path,
            'width': width,
            'height': height,
            'file_size': file_size,
            'file_size_kb': file_size / 1024,
            'file_size_mb': file_size / (1024 * 1024),
            'format': img.format,
            'tokens': tokens
        }
    except Exception as e:
        return {'error': str(e)}


def analyze_base64_image(base64_str: str) -> dict:
    """
    分析 base64 编码的图片并计算 token 消耗
    
    Args:
        base64_str: base64 编码的图片字符串
    
    Returns:
        包含图片信息和 token 计算的字典
    """
    try:
        # 移除可能的 data:image 前缀
        if ',' in base64_str:
            base64_str = base64_str.split(',')[-1]
        
        image_data = base64.b64decode(base64_str)
        img = Image.open(BytesIO(image_data))
        width, height = img.size
        
        tokens = calculate_image_tokens(width, height)
        
        return {
            'width': width,
            'height': height,
            'base64_length': len(base64_str),
            'decoded_size': len(image_data),
            'decoded_size_kb': len(image_data) / 1024,
            'format': img.format,
            'tokens': tokens
        }
    except Exception as e:
        return {'error': str(e)}


def calculate_quota_usage(tokens: int, prompt_length: int = 0) -> dict:
    """
    计算配额使用情况
    
    Args:
        tokens: 图片的 token 数
        prompt_length: 提示词字符长度
    
    Returns:
        配额使用分析
    """
    # 估算文本 tokens (粗略: 1 token ≈ 4 字符)
    text_tokens = prompt_length / 4
    total_tokens = tokens + text_tokens
    
    # Gemini 2.5 Flash Image 的限制
    MAX_TOKENS_PER_MINUTE = 500000
    
    return {
        'image_tokens': tokens,
        'text_tokens': int(text_tokens),
        'total_tokens': int(total_tokens),
        'max_requests_per_minute': int(MAX_TOKENS_PER_MINUTE / total_tokens) if total_tokens > 0 else 0,
        'quota_limit': MAX_TOKENS_PER_MINUTE,
        'percentage_of_quota': (total_tokens / MAX_TOKENS_PER_MINUTE) * 100
    }


def print_analysis(info: dict, prompt_length: int = 0):
    """打印详细的分析报告"""
    print("\n" + "="*60)
    print("📊 Gemini API 图片 Token 分析报告")
    print("="*60)
    
    if 'error' in info:
        print(f"❌ 错误: {info['error']}")
        return
    
    # 图片基本信息
    print(f"\n🖼️  图片信息:")
    if 'path' in info:
        print(f"   文件路径: {info['path']}")
        print(f"   文件格式: {info.get('format', 'Unknown')}")
        print(f"   文件大小: {info['file_size_kb']:.2f} KB ({info['file_size_mb']:.2f} MB)")
    else:
        print(f"   来源: Base64 编码")
        print(f"   格式: {info.get('format', 'Unknown')}")
        print(f"   Base64 长度: {info.get('base64_length', 0):,} 字符")
        print(f"   解码后大小: {info.get('decoded_size_kb', 0):.2f} KB")
    
    print(f"   分辨率: {info['width']} × {info['height']} 像素")
    
    # Token 计算
    print(f"\n💰 Token 消耗:")
    print(f"   图片 Tokens: {info['tokens']:,}")
    print(f"   计算公式: 258 + ({info['width']} × {info['height']}) / 750")
    
    # 配额分析
    quota = calculate_quota_usage(info['tokens'], prompt_length)
    print(f"\n📈 配额使用分析:")
    print(f"   图片 Tokens: {quota['image_tokens']:,}")
    if prompt_length > 0:
        print(f"   文本 Tokens (估算): {quota['text_tokens']:,}")
        print(f"   总 Tokens: {quota['total_tokens']:,}")
    print(f"   每分钟最多请求: {quota['max_requests_per_minute']} 次")
    print(f"   单次请求占配额: {quota['percentage_of_quota']:.4f}%")
    print(f"   配额限制: {quota['quota_limit']:,} tokens/分钟")
    
    # 常见尺寸对比
    print(f"\n📏 常见尺寸 Token 对比:")
    common_sizes = [
        (512, 512, "小图"),
        (1024, 1024, "标准"),
        (1920, 1080, "Full HD"),
        (2048, 2048, "高清"),
        (4096, 4096, "超高清"),
    ]
    
    for w, h, label in common_sizes:
        tokens = calculate_image_tokens(w, h)
        marker = " ← 当前" if w == info['width'] and h == info['height'] else ""
        print(f"   {label:8} ({w:4}×{h:4}): {tokens:6,} tokens{marker}")
    
    print("\n" + "="*60 + "\n")


def main():
    """主函数 - 交互式使用"""
    print("\n🎨 Gemini API 图片 Token 计算器")
    print("="*60)
    
    while True:
        print("\n请选择:")
        print("1. 分析图片文件")
        print("2. 计算指定尺寸")
        print("3. 分析 Base64 图片")
        print("4. 退出")
        
        choice = input("\n输入选项 (1-4): ").strip()
        
        if choice == '1':
            path = input("请输入图片文件路径: ").strip()
            prompt_len = input("提示词字符长度 (可选,直接回车跳过): ").strip()
            prompt_len = int(prompt_len) if prompt_len else 0
            
            info = analyze_image_file(path)
            print_analysis(info, prompt_len)
            
        elif choice == '2':
            try:
                width = int(input("请输入宽度: ").strip())
                height = int(input("请输入高度: ").strip())
                prompt_len = input("提示词字符长度 (可选,直接回车跳过): ").strip()
                prompt_len = int(prompt_len) if prompt_len else 0
                
                tokens = calculate_image_tokens(width, height)
                info = {
                    'width': width,
                    'height': height,
                    'tokens': tokens
                }
                print_analysis(info, prompt_len)
            except ValueError:
                print("❌ 请输入有效的数字")
                
        elif choice == '3':
            base64_str = input("请输入 Base64 字符串 (或文件路径): ").strip()
            
            # 如果是文件路径,读取文件内容
            if Path(base64_str).is_file():
                with open(base64_str, 'r') as f:
                    base64_str = f.read().strip()
            
            prompt_len = input("提示词字符长度 (可选,直接回车跳过): ").strip()
            prompt_len = int(prompt_len) if prompt_len else 0
            
            info = analyze_base64_image(base64_str)
            print_analysis(info, prompt_len)
            
        elif choice == '4':
            print("\n👋 再见!")
            break
        else:
            print("❌ 无效选项,请重新选择")


if __name__ == "__main__":
    # 如果有命令行参数,直接分析
    if len(sys.argv) > 1:
        if sys.argv[1].isdigit() and len(sys.argv) >= 3:
            # 直接计算尺寸: python calculate_image_tokens.py 1024 1024
            width = int(sys.argv[1])
            height = int(sys.argv[2])
            prompt_len = int(sys.argv[3]) if len(sys.argv) > 3 else 0
            
            tokens = calculate_image_tokens(width, height)
            info = {
                'width': width,
                'height': height,
                'tokens': tokens
            }
            print_analysis(info, prompt_len)
        else:
            # 分析文件: python calculate_image_tokens.py image.png
            prompt_len = int(sys.argv[2]) if len(sys.argv) > 2 else 0
            info = analyze_image_file(sys.argv[1])
            print_analysis(info, prompt_len)
    else:
        # 交互式模式
        main()
