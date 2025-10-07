# 标准库
import asyncio
import base64
import io
import logging
import random
import zipfile
from typing import List, Optional

# 第三方库
import httpx

# 本地模块
from .image_tools import 重新编码图片
from .request_payload import CharCaption, get_payload

async def get_character_reference_image(
        novelai_api_lock:asyncio.Lock,
        novelai_api_key:str,
        prompt:str,
        new_negative_prompt:str,
        width:int,
        height:int,
        proxy_client:httpx.AsyncClient,
        v4_prompt_char_captions: Optional[List[CharCaption]],
        image_base_64_string:str|None=None,
        )->str|None:
    url="https://image.novelai.net/ai/generate-image"
    headers = {
    'Authorization': f'Bearer {novelai_api_key}',
    'Content-Type': 'application/json',
}
    seed = random.randint(0, 2**32 - 1)

    image_base64=重新编码图片(image_base_64_string) if image_base_64_string else None

    payloads=get_payload(
    prompt=prompt,
    new_negative_prompt=new_negative_prompt,
    width=width,
    height=height,
    seed=seed,
    image_base64=image_base64,
    v4_prompt_char_captions=v4_prompt_char_captions
    )
    timeout = httpx.Timeout(60.0, connect=10.0)

    try:
        async with novelai_api_lock:
            response = await proxy_client.post(url, headers=headers, json=payloads, timeout=timeout)
            response.raise_for_status()
            if not response.content:
                return None

            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                if not zip_ref.namelist():
                    return None
                image_filename = zip_ref.namelist()[0]
                with zip_ref.open(image_filename) as image_file:
                    image_bytes = image_file.read()
                    base64_string = base64.b64encode(image_bytes).decode('utf-8')
                    return base64_string
    except httpx.HTTPError as e:
        logging.error(f"NovelAI API请求失败: {e}")
        return None
    except zipfile.BadZipFile:
        logging.error("返回的图片数据格式错误")
        return None
    except Exception as e:
        logging.error(f"生成图片时发生未知错误: {e}")
        return None

