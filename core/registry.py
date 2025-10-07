# 容器
# 标准库
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List

# 第三方库
import json5
import httpx
from google import genai
from ncatbot.core import BotClient
from openai import AsyncOpenAI

# 本地模块
from utilities.my_logging import logger
from base import ChatMessage, ImageData, UserIdDate
from core.aimodels.ai_services.openAI_llm import OpenAI_LLM
from utilities.embedding_search import RAGSearchEnhancer
from config.setting import gemini_api_key, gemini_base_url,siliconflow_api_key


def _load_nano_banana_prompts():
    """读取nanobanana预设词文件"""
    try:
        with open("prompt/Nano_Banana.jsonc","r",encoding="utf-8")as f:
            return json5.load(f)
    except Exception as e:
        logger.error(f"读取Nano_Banana.jsonc失败,错误:{e}")
        return {}

_NANO_BANANA_PROMPTS = _load_nano_banana_prompts()

@dataclass
class ServiceDependencies:
    """存放服务依赖项"""
    gemini_client: genai.Client
    novelai_api_lock: asyncio.Lock
    bot: BotClient
    proxy_client:httpx.AsyncClient
    fast_track_proxy:httpx.AsyncClient
    openai_llm: OpenAI_LLM = field(init=False)
    openai_client: AsyncOpenAI=field(init=False)
    rgasearchenhancer: RAGSearchEnhancer=field(init=False)
    
    def __post_init__(self):
        self.openai_client=AsyncOpenAI(api_key=gemini_api_key,base_url=gemini_base_url,http_client=self.proxy_client)
        self.openai_llm = OpenAI_LLM(client=self.openai_client)
        self.rgasearchenhancer=RAGSearchEnhancer(
            index_path="vector/vector.index",
            text_mapping_path="vector/text_mapping.json",
            embedded_model_api_key=siliconflow_api_key,
            yaml_dictionary="vector/danbooru.yaml",
            fast_track_proxy=self.fast_track_proxy
        )


@dataclass
class AppConfig:
    """储存单群上下文以及各项配置"""
    chatSystemPrompt: str
    groupChatKnowledgeBase: str
    drawing_system_prompt: str
    llm_model_name: str
    novelai_api_key: str
    ai_mode_active: bool = True
    root_id:str="2172959822"
    imageIdBase64Map: Dict[str, ImageData] = field(default_factory=dict)#{唯一消息ID:{图片base64编码,时间}}
    userIdContentMap: Dict[str, dict] = field(default_factory=dict)#{userID:{text,类型}}
    messages: List[ChatMessage] = field(init=False)
    image_messages: List[ChatMessage] = field(init=False)
    nano_banana_prompts: dict = field(init=False)

    def __post_init__(self):
        self.nano_banana_prompts = _NANO_BANANA_PROMPTS
        self.messages = [ChatMessage(role="system", content=self.chatSystemPrompt + self.groupChatKnowledgeBase)]
        self.image_messages = [ChatMessage(role="system", content=self.drawing_system_prompt)]


    




