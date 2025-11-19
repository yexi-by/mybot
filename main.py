# 标准库
import asyncio
import os

# 第三方库
import httpx
import fal_client
from google import genai
from ncatbot.core import BotClient, GroupMessage
from openai import AsyncOpenAI
from volcenginesdkarkruntime import AsyncArk
from tavily import AsyncTavilyClient

# 本地模块
from config.setting import gemini_api_key, gemini_base_url, siliconflow_api_key,system_proxies,volcengine_api_key,volcengine_base_url,fai_api_key,tavily_api_key
from core.registry import ServiceDependencies
from core.single_group_instance import setupGroupInstance
from utilities.embedding_search import RAGSearchEnhancer
from utilities.my_logging import logger
from utilities.utils import hourlyAnnouncement

os.environ["FAL_KEY"] = fai_api_key
my_proxy={
    "https://": system_proxies,
}
servicedependencies =ServiceDependencies(
    gemini_client=genai.Client(api_key=gemini_api_key,http_options={"client_args": {"proxies": my_proxy}}),# type: ignore
    novelai_api_lock=asyncio.Lock(),
    volcengine_api_lock=asyncio.Lock(),
    volcengine_client=AsyncArk(api_key=volcengine_api_key,base_url=volcengine_base_url),
    proxy_client=httpx.AsyncClient(proxy=system_proxies,trust_env=False,timeout=60.0),
    bot=BotClient(),
    fal_client=fal_client,
    fast_track_proxy=httpx.AsyncClient(trust_env=False,timeout=15.0),#直连代理,主要用于国内服务
    tavily_client=AsyncTavilyClient(api_key=tavily_api_key)
)

#async def handle_startup_message():
    #asyncio.create_task(hourlyAnnouncement(servicedependencies=servicedependencies))

#servicedependencies.bot.add_startup_handler(handle_startup_message)

@servicedependencies.bot.group_event() # type
async def handle_group_message(msg: GroupMessage):
    logger.info(msg)
    if aigroupmanager:=setupGroupInstance(
        msg=msg,
        servicedependencies=servicedependencies
    ):
        await aigroupmanager.handle_group_message(msg=msg)
if __name__ == "__main__":
    servicedependencies.bot.run(bt_uin=742654932)

