# 储存小的功能函数方便调用
# 标准库
import base64
import datetime
from pathlib import Path
from typing import TYPE_CHECKING

# 第三方库
import httpx
from ncatbot.core import GroupMessage

# 本地模块
from base import ImageData
from utilities.my_logging import logger

if TYPE_CHECKING:
    from core.registry import AppConfig

def starts_with_keyword(msg:GroupMessage,keyword:str)->bool:
    """检测文本是否包含关键字"""
    for segment in msg.message:
        if segment.get("type") == "text":
            text = segment.get("data", {}).get("text", "")
            if text.startswith(f"/{keyword}"):
                return True
    return False


def get_text_segment(msg:GroupMessage,offset:int)->str|None:
    """降噪后提取文本内容"""
    for segment in msg.message:
        if segment.get("type") == "text":
            text = segment.get("data", {}).get("text", "")
            text = text.strip()
            return text[offset:]


def checkMentionBehavior(msg:GroupMessage,)->bool:
    """检查是否有艾特机器人行为"""
    for segment in msg.message:
        if segment.get("type") == "at":
            if segment.get("data", {}).get("qq","") == str(msg.self_id):
                return True
    return False

def is_reply_and_get_message_id(msg:GroupMessage)->str|None:
    """检测消息类型是否会回复,并且返回被回复的消息id"""
    for segment in msg.message:
        if segment.get("type") == "reply":
            message_id=segment.get("data",{}).get('id','')
            return str(message_id)
    return None

async def is_image_message_return_base64(msg:GroupMessage)->str|None:
    """判断消息类型是否为图片,并且返回该图片base64编码"""
    for segment in msg.message:
        if segment.get("type") == 'image':
            if image_url:= segment.get("data",{}).get('url',''):
                async with httpx.AsyncClient() as client:
                    response = await client.get(image_url)
                image_base64=base64.b64encode(response.content).decode('ascii')
                return image_base64
    return None

def read_prompt_file(filepath:Path|str)->str|None:
    """读取相对路径下的文件"""
    try:
        file_path = Path(filepath)
        with open(file_path,"r",encoding="utf8") as f:
            content=f.read()
            return content
    except (FileNotFoundError, IOError) as e:
        logger.error(f"读取文件失败 {filepath}: {e}")
        return None

def store_image_base64_with_message_id_and_timestamp(
        appconfig:"AppConfig",
        base64_image:str,
        response:dict|None=None,
        message_id:int|None|str=None
        ):
    """储存图片base64编码以及对应的消息id,附带时间"""
    if (response is not None and message_id is not None):
        raise ValueError("不能同时提供 'response' 和 'message_id'。请只选择一个。")
    if (response is None and message_id is None):
        raise ValueError("必须提供 'response' 或 'message_id' 中的一个。")
    if response:
        message_id = response["data"]["message_id"]      
    appconfig.imageIdBase64Map[str(message_id)]=ImageData(
        base64=base64_image,
        timestamp=datetime.datetime.now().timestamp()
    )
    if len(appconfig.imageIdBase64Map)>=60:
        oldest_key =min(appconfig.imageIdBase64Map, key=lambda k: appconfig.imageIdBase64Map[k].timestamp)
        del appconfig.imageIdBase64Map[oldest_key]





                    