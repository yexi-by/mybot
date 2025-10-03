from pydantic import BaseModel
from typing import Dict, Any, List, Union, Tuple,Optional, cast, Any,Literal

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
    role: Literal["system", "user", "assistant", "developer"]
    content: str

