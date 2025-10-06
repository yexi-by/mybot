# 创建任务循环
# 标准库
import asyncio

# 第三方库
from ncatbot.core import GroupMessage

# 本地模块
from core.registry import AppConfig, ServiceDependencies

from ..aimodels.aiservice import (
    AiService,
    DelayedAIResponseModule,
    GroupChatTriggerWords,
    OthersHandles,
    RealTimeAIResponse,
)

class AiGroupManager:
    def __init__(
        self,
        servicedependencies:ServiceDependencies,
        appconfig:AppConfig
    ) -> None:
        self.servicedependencies=servicedependencies
        self.appconfig=appconfig
        self.aiservice=AiService(
            servicedependencies=self.servicedependencies,
            appconfig=self.appconfig
        )
        self.groupChatTriggerWords=GroupChatTriggerWords(
            servicedependencies=self.servicedependencies,
            appconfig=self.appconfig,
            aiservice=self.aiservice
        )
        self.delayedAIResponseModule=DelayedAIResponseModule(
            servicedependencies=self.servicedependencies,
            appconfig=self.appconfig,
            aiservice=self.aiservice
        )
        self.realTimeAIResponse=RealTimeAIResponse(
            servicedependencies=self.servicedependencies,
            appconfig=self.appconfig,
            aiservice=self.aiservice
        )
        self.othersHandles=OthersHandles(
            servicedependencies=self.servicedependencies,
            appconfig=self.appconfig,
            aiservice=self.aiservice
        )
        asyncio.create_task(self.othersHandles.remove_timed_out_messages())
    async def handle_group_message(self,msg:GroupMessage)->bool:
        handles=[
            self.groupChatTriggerWords.switch_ai_personality,
            self.groupChatTriggerWords.controlAiMode,
            self.groupChatTriggerWords.log_user_message_and_id,
            self.groupChatTriggerWords.retract_sent_image,
            self.delayedAIResponseModule.generateDelayedImageResponse,
            self.realTimeAIResponse.generateImageResponse,
            self.realTimeAIResponse.generate_image,
            self.realTimeAIResponse.handle_group_message_response
        ]
        for handle in handles:
            result = await handle(msg=msg)
            if result:
                return True
        return False
    