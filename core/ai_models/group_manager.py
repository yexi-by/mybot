import asyncio
import inspect
from typing import Any, Dict
from ncatbot.core import GroupMessageEvent,BotClient
from .group_context import GroupContext
from .ai_command_handler import AICommandHandler
from .ai_services.openAI_llm import OpenAI_LLM
from utilities.embedding_search import RAGSearchEnhancer
from dataclasses import dataclass

@dataclass
class AiManagerConfig:
    deepseek_model_name: str
    gemini_model_name: str
    chat_system_prompt: str  
    drawing_system_prompt: str
    novelai_api_key: str
    group_chat_knowledge_base: str

class AiGroupManager:
    def __init__(
        self,
        config: AiManagerConfig,
        bot: BotClient,
        openai_llm: OpenAI_LLM,
        rgasearchenhancer: RAGSearchEnhancer,
        novelai_api_lock: asyncio.Lock
    ) -> None:
        self.novelai_api_lock = novelai_api_lock
        self.group_context = GroupContext(
            chatSystemPrompt=config.chat_system_prompt,
            groupChatKnowledgeBase=config.group_chat_knowledge_base,
            drawing_system_prompt=config.drawing_system_prompt,
            llm_model_name=config.gemini_model_name,
            novelai_api_key=config.novelai_api_key
        )
        self.aicommandhandler = AICommandHandler(
            bot=bot,
            groupcontext=self.group_context,
            openai_llm=openai_llm,
            rgasearchenhancer=rgasearchenhancer,
        )
        asyncio.create_task(self.aicommandhandler.remove_timed_out_messages())

    async def globalRouteDispatcher(self, msg: GroupMessageEvent):
        handlers=[
            self.aicommandhandler.switch_ai_personality,
            self.aicommandhandler.log_user_message_and_id,
            self.aicommandhandler.generate_image,
            self.aicommandhandler.generateDelayedImageResponse,
            self.aicommandhandler.generateImageResponse,
            self.aicommandhandler.controlAiMode,
            self.aicommandhandler.retract_sent_image,
            self.aicommandhandler.handle_group_message_response,
        ]
        for handler in handlers:
            sig = inspect.signature(handler)
            params = sig.parameters
            kwargs_to_pass:Dict[str, Any] = {'msg': msg}
            if 'novelai_api_lock' in params:
                kwargs_to_pass['novelai_api_lock'] = self.novelai_api_lock
            if await handler(**kwargs_to_pass):
                return True
        return False