import asyncio
from ncatbot.core import GroupMessageEvent,BotClient
from group_context import GroupContext
from ai_command_handler import AICommandHandler
from .ai_services.openAI_llm import OpenAI_LLM
from utilities.embedding_search import RAGSearchEnhancer
class AiGroupManager:
    def __init__(
    self,
    deepseek_model_name: str,
    gemini_model_name: str,
    chatSystemPrompt: str,
    drawing_system_prompt:str,
    novelai_api_key: str,
    groupChatKnowledgeBase:str,
    bot:BotClient,
    openai_llm:OpenAI_LLM,
    rgasearchenhancer:RAGSearchEnhancer,
    novelai_api_lock:asyncio.Lock

    ) -> None:
        self.novelai_api_lock = novelai_api_lock
        self.group_context=GroupContext(
            chatSystemPrompt=chatSystemPrompt,
            groupChatKnowledgeBase=groupChatKnowledgeBase,
            drawing_system_prompt=drawing_system_prompt,
            llm_model_name=gemini_model_name,
            novelai_api_key=novelai_api_key
        )
        self.aicommandhandler=AICommandHandler(
            bot=bot,
            groupcontext=self.group_context,
            openai_llm=openai_llm,
            rgasearchenhancer=rgasearchenhancer,
        )
        asyncio.create_task(self.aicommandhandler.remove_timed_out_messages())

        