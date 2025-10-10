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
            # 系统控制命令 - 优先处理
            self.groupChatTriggerWords.switch_ai_personality,
            self.groupChatTriggerWords.controlAiMode,
            # 管理操作
            self.groupChatTriggerWords.retract_sent_image,
            # 帮助功能
            self.groupChatTriggerWords.listHelpFunctions,
            # 管理员特权操作
            self.othersHandles.dangerous_metacode_injection,
            # 延迟响应 - 处理之前记录的用户请求
            self.delayedAIResponseModule.generateDelayedImageResponse,
            self.delayedAIResponseModule.generateVideoWithImageDelay,
            # 即时响应 - 图生图和文生图和图生视频和文生视频
            self.realTimeAIResponse.generateImageResponse,
            self.realTimeAIResponse.replyWithVideoFromImage,
            self.realTimeAIResponse.generate_image,
            self.realTimeAIResponse.get_videos,
            #自动td
            self.groupChatTriggerWords.sendMessageOnAllMention,
            # 记录用户消息 
            self.groupChatTriggerWords.log_user_message_and_id,
            # 智能水群 - 兜底处理
            self.realTimeAIResponse.handle_group_message_response
        ]
        for handle in handles:
            result = await handle(msg=msg)
            if result:
                return True
        return False
    