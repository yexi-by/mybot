# 标准库
import asyncio

# 第三方库
import httpx
from google import genai
from ncatbot.core import BotClient, GroupMessage
from openai import AsyncOpenAI

# 本地模块
from config.setting import gemini_api_key, gemini_base_url, siliconflow_api_key,system_proxies
from core.registry import ServiceDependencies
from core.single_group_instance import setupGroupInstance
from utilities.embedding_search import RAGSearchEnhancer
from utilities.my_logging import logger
my_proxy={
    "https://": system_proxies,
}
servicedependencies =ServiceDependencies(
    gemini_client=genai.Client(api_key=gemini_api_key,http_options={"client_args": {"proxies": my_proxy}}),# type: ignore
    novelai_api_lock=asyncio.Lock(),
    jimeng_api_lock=asyncio.Lock(),
    proxy_client=httpx.AsyncClient(proxy=system_proxies,trust_env=False,timeout=60.0),
    bot=BotClient(),
    fast_track_proxy=httpx.AsyncClient(trust_env=False,timeout=15.0)#直连代理,主要用于国内服务
)

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
