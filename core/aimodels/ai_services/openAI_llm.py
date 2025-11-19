# 标准库
from typing import Any, List, Optional, cast
import json

# 第三方库
from openai import AsyncOpenAI,APIStatusError
from pydantic import BaseModel

# 本地模块
from base import CharCaption, ChatMessage,ToolChatMessage
from utilities.web_search import Web_search


class OpenAI_LLM:
    def __init__(self,client:AsyncOpenAI) -> None:
        self.client=client

    async def deepseek_fetch_json_content(self,model_name:str,messages:List[ChatMessage|ToolChatMessage|dict])->str|None:
        try:
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
        except APIStatusError as e:
            return f"错误消息:{e.status_code},{e.response.text}"

    async def deepseek_get_response(self,model_name:str,messages:List)->str:
        response = await self.client.chat.completions.create(
                    model=model_name,
                    messages=cast(Any, messages), 
                    stream=False
                )
        ai_response=cast(str,response.choices[0].message.content)
        return ai_response
        

    async def gemini_fetch_json_content(
            self,
            model_name,
            messages:List[ChatMessage|ToolChatMessage|dict],
            )->str|None:
        class WebSearch(BaseModel):
            web_search_switch:bool=False
            web_search_query:Optional[str]=None
        class MetaprogramSwitch(BaseModel):
            is_enabled:bool=False
            code_snippet:Optional[str]=None

        class AIResponseModel(BaseModel):
            Text: Optional[str] = None
            At: Optional[List[int]] = None
            AtAll:Optional[bool] = None
            Web_search:Optional[WebSearch]=None# 网络搜索功能
            metaprogram:Optional[MetaprogramSwitch]#元编程可执行代码
            #绘图部分
            prompt: Optional[str] = None
            negative_prompt: Optional[str] = None
            # 角色和坐标信息
            char_captions: Optional[List[CharCaption]] = None

        response = await self.client.beta.chat.completions.parse(
            model=model_name,
            messages=cast(Any, messages),  # 类型转换以避免类型检查错误
            response_format=AIResponseModel,
            timeout=60.0,
        )
        # parsed 返回的是 AIResponseModel 对象，需要转换为 JSON 字符串
        if parsed_model := response.choices[0].message.parsed:
            try:
                ai_response_json = parsed_model.model_dump_json()
                return ai_response_json
            except APIStatusError as e:
                return f"错误消息:{e.status_code},{e.response.text}"
            
    async def fetch_json_from_ai_model(self,model_name:str,messages:List[ChatMessage|ToolChatMessage|dict],web_search:Web_search|None=None,tools:list|None=None)->str|None:
        if "deepseek" in model_name:
            ai_response_json=await self.deepseek_fetch_json_content(model_name=model_name,messages=messages)
            return ai_response_json
        elif "gemini" in model_name:
            ai_response_json=await self.gemini_fetch_json_content(model_name=model_name,messages=messages)
            return ai_response_json
        else:
            return None
        

        
        


