# 标准库
from typing import List, Literal,Any,Optional

# 第三方库
from pydantic import BaseModel

class Center(BaseModel):
    x: float
    y: float

class CharCaption(BaseModel):
    char_caption: str
    centers: List[Center]

class ImageData(BaseModel):
    """用于验证imageIdBase64Map中存储的图片数据"""
    base64: str
    timestamp: float

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "developer","tool"]
    content: Any
class ToolChatMessage(BaseModel):
    role:str
    tool_call_id:Any
    content:Any



class UserIdDate(BaseModel):
    """用来验证储存的用户ID(通常是qq号),以及请求类型和用户输入"""
    type:str
    user_input_text:str
    

