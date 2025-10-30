# 创建单群实例
# 标准库
from typing import Dict, Optional, Tuple

# 第三方库
from ncatbot.core import GroupMessage

# 本地模块
from config.setting import gemini_model_name, groups_config, novelai_api_key,volcengine_model_name,deepseek_model_name
from utilities.utils import read_prompt_file

from .aimodels.group_manager import AiGroupManager
from .registry import AppConfig, ServiceDependencies

def readPromptFiles(groups_config:dict,msg:GroupMessage)->Tuple:

    chat_prompt_file_name=groups_config[int(msg.group_id)]["chat_prompt"]
    chat_knowledge_prompt_file_name=groups_config[int(msg.group_id)]["知识库"]
    drawing_system_prompt_file_name=groups_config[int(msg.group_id)]["image_prompt"]    
    chat_prompt=read_prompt_file(filepath=chat_prompt_file_name)
    chat_knowledge_prompt=read_prompt_file(filepath=chat_knowledge_prompt_file_name)
    drawing_system_prompt=read_prompt_file(filepath=drawing_system_prompt_file_name)
    return chat_prompt,chat_knowledge_prompt,drawing_system_prompt

group_ai_instances :Dict[int,AiGroupManager]= {}

def setupGroupInstance(
        msg:GroupMessage,
        servicedependencies: ServiceDependencies,
        )->Optional[AiGroupManager]:
    """注册单群实例"""
    if not int(msg.group_id) in groups_config:
        return None
    if int(msg.group_id) in group_ai_instances:
        return group_ai_instances[int(msg.group_id)]
    chat_prompt, chat_knowledge_prompt, drawing_system_prompt = readPromptFiles(groups_config=groups_config, msg=msg)

    appconfig=AppConfig(
        chatSystemPrompt=chat_prompt,
        groupChatKnowledgeBase=chat_knowledge_prompt,
        drawing_system_prompt=drawing_system_prompt,
        llm_model_name=gemini_model_name,
        novelai_api_key=novelai_api_key,
        volcengine_model_name=volcengine_model_name,
        deepseek_model_name=deepseek_model_name
    )

    aigroupmanager=AiGroupManager(
        servicedependencies=servicedependencies,
        appconfig=appconfig
    )
    group_ai_instances[int(msg.group_id)]=aigroupmanager
    return aigroupmanager
