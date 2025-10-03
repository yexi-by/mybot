from pydantic import BaseModel
from openai import AsyncOpenAI
from typing import List, Optional, cast, Any
from ..group_context import ChatMessage
from base import Center, CharCaption
class OpenAI_LLM:
    def __init__(self,client:AsyncOpenAI) -> None:
        self.client=client

    async def deepseek_fetch_json_content(self,model_name:str,messages:List[ChatMessage])->str|None:
        response = await self.client.chat.completions.create(
            model=model_name,
            messages=cast(Any, messages),  # 类型转换以避免类型检查错误
            stream=False,
            response_format={
            "type": "json_object"
            },
            timeout=60.0
        )
        ai_response_json=response.choices[0].message.content
        return ai_response_json

    async def gemini_fetch_json_content(self,model_name,messages:List[ChatMessage])->str|None:
        class AIResponseModel(BaseModel):
            Text: Optional[str] = None
            At: Optional[List[int]] = None
            AtAll:Optional[bool] = None
            #绘图部分
            prompt: Optional[str] = None
            negative_prompt: Optional[str] = None
            # 角色和坐标信息
            char_captions: Optional[List[CharCaption]] = None
            
        response = await self.client.beta.chat.completions.parse(
            model=model_name,
            messages=cast(Any, messages),  # 类型转换以避免类型检查错误
            response_format=AIResponseModel,
            timeout=60.0
        )
        # parsed 返回的是 AIResponseModel 对象，需要转换为 JSON 字符串
        if parsed_model := response.choices[0].message.parsed:
            ai_response_json = parsed_model.model_dump_json()
            return ai_response_json
        
    async def fetch_json_from_ai_model(self,model_name:str,messages:List[ChatMessage])->str|None:
        if "deepseek " in model_name:
            ai_response_json=await self.deepseek_fetch_json_content(model_name=model_name,messages=messages)
            return ai_response_json
        elif "gemini" in model_name:
            ai_response_json=await self.gemini_fetch_json_content(model_name=model_name,messages=messages)
            return ai_response_json
        


