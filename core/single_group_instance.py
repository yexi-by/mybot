import asyncio
from typing import Any, Dict, List, Optional,Tuple
from utilities.utils import read_prompt_file
from ncatbot.core import GroupMessageEvent,BotClient
from .ai_models.group_manager import AiGroupManager, AiManagerConfig
from .ai_models.ai_services.openAI_llm import OpenAI_LLM
from utilities.embedding_search import RAGSearchEnhancer
from config.setting import (
    novelai_api_key,
    deepseek_model_name,
    gemini_model_name,
    groups_config,
)

def readPromptFiles(groups_config:dict,msg:GroupMessageEvent)->Tuple:

    chat_prompt_file_name=groups_config[int(msg.group_id)]["chat_prompt"]
    chat_knowledge_prompt_file_name=groups_config[int(msg.group_id)]["知识库"]
    drawing_system_prompt_file_name=groups_config[int(msg.group_id)]["image_prompt"]    
    chat_prompt=read_prompt_file(filepath=chat_prompt_file_name)
    chat_knowledge_prompt=read_prompt_file(filepath=chat_knowledge_prompt_file_name)
    drawing_system_prompt=read_prompt_file(filepath=drawing_system_prompt_file_name)
    return chat_prompt,chat_knowledge_prompt,drawing_system_prompt

group_ai_instances :Dict[int,AiGroupManager]= {}
def setupGroupInstance(
        msg:GroupMessageEvent,
        bot:BotClient,
        openai_llm:OpenAI_LLM,
        rgasearchenhancer:RAGSearchEnhancer,
        novelai_api_lock:asyncio.Lock
        )->Optional[AiGroupManager]:
    if not int(msg.group_id) in groups_config:
        return None
    if int(msg.group_id) in group_ai_instances:
        return group_ai_instances[int(msg.group_id)]
    chat_prompt, chat_knowledge_prompt, drawing_system_prompt = readPromptFiles(groups_config=groups_config, msg=msg)

    aimanagerconfig=AiManagerConfig(
        deepseek_model_name=deepseek_model_name,
        gemini_model_name=gemini_model_name,
        chat_system_prompt=chat_prompt,
        drawing_system_prompt=drawing_system_prompt,
        novelai_api_key=novelai_api_key,
        group_chat_knowledge_base=chat_knowledge_prompt,
    )
    aigroupmanager=AiGroupManager(
        config=aimanagerconfig,
        bot=bot,
        openai_llm=openai_llm,
        rgasearchenhancer=rgasearchenhancer,
        novelai_api_lock=novelai_api_lock
    )
    group_ai_instances[int(msg.group_id)]=aigroupmanager
    return aigroupmanager
