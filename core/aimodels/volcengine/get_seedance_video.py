import os
import time  
import asyncio
from typing import Any
# 通过 pip install 'volcengine-python-sdk[ark]' 安装方舟SDK
from volcenginesdkarkruntime import AsyncArk
from utilities.my_logging import logger

async def post_video(
        client:AsyncArk,
        prompt:str,
        model_name:str,
        image_base64:str|None=None
        )->str|None:
    content=[
            {
                "type":"text",
                #--resolution 1080p：指定输出分辨率（常见选项：480p / 720p / 1080p）
                #--duration 5：指定时长
                #--camerafixed false：是否固定摄像机
                #--watermark true：是否在成片上加“AI 生成”水印
                "text":f"{prompt} --resolution 720p  --duration 5 --camerafixed false --watermark false"
            }
        ]
    if image_base64:
        image_base64_paload={
        "type": "image_url",
        "image_url":{
            "url":f"data:image/png;base64,{image_base64}"
        }
    }
        content.append(image_base64_paload)
    
    create_result =await client.content_generation.tasks.create(
        model=model_name,
        content=content  # type: ignore[arg-type]
    )
    task_id=create_result.id
    while True:
        get_result = await client.content_generation.tasks.get(task_id=task_id)
        if get_result.status == "succeeded":
            logger.info("生成视频成功")
            url = get_result.content.video_url
            return url
        elif get_result.status == "failed":
            logger.error("视频生成失败!")
            return None
        else :
            logger.info("正在生成视频,请等待")
            await asyncio.sleep(1)
