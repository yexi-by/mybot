import math
import io
import base64
from PIL import Image
from PIL.Image import Image as PILImage
from typing import Tuple

def calculate_novelai_reference_dimensions(width: int, height: int) -> Tuple[int, int]: 
    "获取图片长宽,输出官网图片长宽"
    # 使用宽高比阈值判断图片是否接近方形
    ASPECT_RATIO_THRESHOLD = 1.1 
    original_aspect_ratio = width / height

    # 首先根据宽高比，将图片分类
    if 1 / ASPECT_RATIO_THRESHOLD < original_aspect_ratio < ASPECT_RATIO_THRESHOLD:
        # 类方形图片
        # 强制宽高比为1:1，并使用方形的目标像素数
        target_aspect_ratio = 1.0
        target_pixels = 2166784  # 对应 1472*1472
    elif original_aspect_ratio >= ASPECT_RATIO_THRESHOLD:
        # 横屏图片
        # 强制宽高比为3:2，并使用非方形的目标像素数
        target_aspect_ratio = 1.5
        target_pixels = 1572864  # 对应 1536*1024
    else:
        # 竖屏图片
        # 强制宽高比为2:3，并使用非方形的目标像素数
        target_aspect_ratio = 2 / 3
        target_pixels = 1572864  # 对应 1024*1536
    # 根据目标像素和目标宽高比，计算出理想尺寸
    ideal_height = math.sqrt(target_pixels / target_aspect_ratio)
    ideal_width = ideal_height * target_aspect_ratio
    # 将理想尺寸向下取整到最近的64的倍数，得到最终尺寸
    final_width = (int(ideal_width) // 64) * 64
    final_height = (int(ideal_height) // 64) * 64
    return final_width, final_height

def get_image_dimensions(b64_string: str) -> Tuple[PILImage, Tuple[int, int]]:
    "计算图片长宽"
    img_data = base64.b64decode(b64_string)
    image_stream = io.BytesIO(img_data)
    img = Image.open(image_stream)
    return img, img.size
    
def 重新编码图片(b64_string: str) -> str:
    "模仿nai官网图片在编码算法"
    image, (width, height) = get_image_dimensions(b64_string)
    final_width, final_height = calculate_novelai_reference_dimensions(width, height)
    resized_image = image.resize((final_width, final_height), Image.Resampling.LANCZOS)
    if resized_image.mode != 'RGBA':
        resized_image = resized_image.convert('RGBA')
    with io.BytesIO() as output:
        resized_image.save(output, format="PNG", compress_level=0)
        final_png_bytes = output.getvalue()
    base64编码 = base64.b64encode(final_png_bytes).decode('utf-8')
    return base64编码