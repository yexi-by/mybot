#储存小的功能函数方便调用
from ncatbot.core import GroupMessageEvent
from pathlib import Path
import base64
import httpx

def starts_with_keyword(msg:GroupMessageEvent,keyword:str)->bool:
    """检测文本是否包含关键字"""
    for segment in msg.message:
        if segment.get("type") == "text":
            text = segment.get("data", {}).get("text", "")
            if text.startswith(f"/{keyword}"):
                return True
    return False

def get_text_segment(msg:GroupMessageEvent,offset:int)->str|None:
    """提取文本内容"""
    for segment in msg.message:
        if segment.get("type") == "text":
            text = segment.get("data", {}).get("text", "")
            return text[offset:].strip()


def checkMentionBehavior(msg:GroupMessageEvent,)->bool:
    """检查是否有艾特机器人行为"""
    for segment in msg.message:
        if segment.get("type") == "at":
            if segment.get("data", {}).get("qq") == msg.self_id:
                return True
    return False

def is_reply_and_get_message_id(msg:GroupMessageEvent)->str|None:
    """检测消息类型是否会回复,并且返回被回复的消息id"""
    for segment in msg.message:
        if segment.get("type") == "reply":
            message_id=segment.get("data",{}).get('id','')
            return message_id
    return None

async def is_image_message_return_base64(msg:GroupMessageEvent)->str|None:
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
    if file_path:=Path(filepath):
        try:
            with open(file_path,"r",encoding="utf8") as f:
                content=f.read()
                return content
        except:
            pass
            




                    