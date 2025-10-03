from openai import AsyncOpenAI
from ncatbot.core import GroupMessageEvent,BotClient
from core.single_group_instance import setupGroupInstance
from core.ai_models.ai_services.openAI_llm import OpenAI_LLM
from utilities.embedding_search import RAGSearchEnhancer
import asyncio  
from config.setting import (
    deepseek_base_url,
    deepseek_api_key,
    gemini_base_url,
    gemini_api_key,
    siliconflow_api_key,
)
openai_client = AsyncOpenAI(api_key=gemini_api_key,base_url=gemini_base_url)
openai_llm=OpenAI_LLM(client=openai_client)
novelai_api_lock=asyncio.Lock()
rgasearchenhancer=RAGSearchEnhancer(
        index_path="vector.index",
        text_mapping_path="text_mapping.json",
        embedded_model_api_key=siliconflow_api_key,
        yaml_dictionary="date.yaml",
        )
bot = BotClient()
@bot.on_group_message() # type: ignore
async def handle_group_message(msg: GroupMessageEvent):
    if aigroupmanager:=setupGroupInstance(
        msg=msg,
        bot=bot,
        openai_llm=openai_llm,
        rgasearchenhancer=rgasearchenhancer,
        novelai_api_lock=novelai_api_lock
    ):
        await aigroupmanager.globalRouteDispatcher(msg=msg)

if __name__ == "__main__":
    bot.run_frontend()
