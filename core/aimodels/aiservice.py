# 标准库
import asyncio
import random
import traceback
import textwrap
from pathlib import Path
from typing import Any, Dict, cast,Literal,Optional

# 第三方库
import yaml
from ncatbot.core import GroupMessage, Image, MessageChain,Video
from pypinyin import Style, pinyin

# 本地模块
from base import ChatMessage, UserIdDate
from core.registry import AppConfig, ServiceDependencies
from utilities.json_parser import buildTextToImagePrompt, parse_llm_json_to_message_array
from utilities.my_logging import logger
from utilities.utils import (
    checkMentionBehavior,
    get_text_segment,
    is_image_message_return_base64,
    is_reply_and_get_message_id,
    read_prompt_file,
    starts_with_keyword,
    store_image_base64_with_message_id_and_timestamp,
    is_message_only_keyword,
    check_at_all
)

from .ai_services.gemini_image import text_and_image_to_image
from .nai_image.character_reference_image import get_character_reference_image
from .volcengine.get_seedance_video import post_video
from .volcengine.get_jimemg_video import get_videos
from.volcengine.volcengineimage import get_volcengine_image

class AiService:
    """辅助类"""
    def __init__(
        self,
        servicedependencies:ServiceDependencies,
        appconfig:AppConfig
        ) -> None:
        self.servicedependencies=servicedependencies
        self.appconfig=appconfig

    async def generate_image(
            self,
            ai_response_json:str,
            reference_image_base64:str|None=None,

        ):
        """需要构建nai提示词的生图方法"""
        prompt,negative_prompt,char_captions=buildTextToImagePrompt(ai_response_json)
        if not prompt or not negative_prompt or not char_captions:
            logger.error(f"构建生图提示词失败: {ai_response_json}")
            return False
        
        if image_base64:=await get_character_reference_image(
            novelai_api_lock=self.servicedependencies.novelai_api_lock,
            novelai_api_key=self.appconfig.novelai_api_key,
            prompt=prompt,
            new_negative_prompt=negative_prompt,
            width=1024,
            height=1024,
            image_base_64_string=reference_image_base64,
            v4_prompt_char_captions=char_captions,
            proxy_client=self.servicedependencies.proxy_client
            ):
            return image_base64
    async def insert_vectorized_data_dynamically(
            self,
            user_input_text
        ):
        """动态插入向量化数据到系统提示词并且构建image_messages"""
        if not (best_matches:=await self.servicedependencies.rgasearchenhancer.get_vector_query_results(user_input=user_input_text)):
            return None
        if not (result_collection:=self.servicedependencies.rgasearchenhancer.get_details_from_yaml_by_names(best_matches=best_matches)):
            return None       
        system_prompt=self.appconfig.image_messages[0].content
        image_messages=[ChatMessage(role="system", content=f"{system_prompt}\n\n以下是向量动态插入字典对照表,请甄别后参考\n{result_collection}")]
        image_messages.append(ChatMessage(role="user", content=user_input_text))
        return image_messages
    
    async def process_user_input_to_novlai_image(
            self,
            msg:GroupMessage,
            user_input_text:str,
            type:Literal["gemini", "novelai","volcengine_即梦4.0"],
            reference_image_base64:str|None=None,
        ):
        """集成了novelai和gemini和火山即梦4.0的高度集成抽象封装,一键生图!"""
        await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,at=msg.user_id,text=f"正在生成图片,请耐心等待片刻")
        if type=="novelai":
            if not(image_messages := await self.insert_vectorized_data_dynamically(user_input_text=user_input_text)):
                await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,text="构建带有向量化动态词典的生图提示词失败!请重试")
                return True
            ai_response_json = await self.servicedependencies.openai_llm.fetch_json_from_ai_model(model_name=self.appconfig.llm_model_name,messages=image_messages)
            if not ai_response_json:
                await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,at=msg.user_id,text=f"错误消息:未知错误")
                return True
            if ai_response_json.startswith("错误消息:"):
                await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,at=msg.user_id,text=ai_response_json)
                return True
            image_base64 = await self.generate_image(
                ai_response_json=ai_response_json,
                reference_image_base64=reference_image_base64
            )
        elif type=="gemini"and reference_image_base64:
            image_base64=await text_and_image_to_image(
                client=self.servicedependencies.gemini_client,
                prompt=user_input_text,
                image_base64=reference_image_base64,
                model_name="gemini-2.5-flash-image",
            )
        elif type=="volcengine_即梦4.0":
            image_base64=await get_volcengine_image(
                client=self.servicedependencies.volcengine_client,
                prompt=user_input_text,
                iamgebase64=reference_image_base64,
            )
        else:
            await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,at=msg.user_id,text="数据列表错误,我一会来修")
            return True
        if not image_base64:
            await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,at=msg.user_id,text="图片生成失败")
            return True
        image_MessageChain=MessageChain([Image(f"base64://{image_base64}")])
        await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,at=msg.user_id,text="图片生成完成")
        response = cast(Dict[str, Any], await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,rtf=image_MessageChain))
        store_image_base64_with_message_id_and_timestamp(response=response,appconfig=self.appconfig,base64_image=image_base64)
        return True
    
    async def generateVolcanoEngineVideo(
            self,
            msg:GroupMessage,
            prompt:str|None,
            reference_image_base64:str|None=None
            ):
        """火山引擎生成视频抽象封装"""
        if not prompt:
            await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,text="输入为空亦或者获取提示词失败")
            return True
        if reference_image_base64:
            store_image_base64_with_message_id_and_timestamp(appconfig=self.appconfig,base64_image=reference_image_base64,message_id=msg.message_id)
        lock=self.servicedependencies.volcengine_api_lock
        if lock.locked():
            await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,at=msg.user_id,text="目前有人正在占用事件循环,处理完他的在处理你的")
        async with lock:
            await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,at=msg.user_id,text="正在生成视频,请稍等片刻")
            try:
                video_url=await post_video(
                    client=self.servicedependencies.volcengine_client,
                    prompt=prompt,
                    model_name=self.appconfig.volcengine_model_name,
                    image_base64=reference_image_base64,
                )
            except:
                await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,at=msg.user_id,text="不是哥们,你发的什么,过不了审核啊") 
                return True
            if not video_url:
                await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,at=msg.user_id,text="视频生成失败了,这傻逼字节跳动") 
                return True
        video_message=MessageChain(Video(video_url))
        await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,at=msg.user_id,text="视频生成完成") 
        await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,rtf=video_message) 
        return True

        
            
class GroupChatTriggerWords:
    def __init__(
        self,
        servicedependencies:ServiceDependencies,
        appconfig:AppConfig,
        aiservice:AiService
        ) -> None:
        """控制固定触发词交互"""
        self.servicedependencies=servicedependencies
        self.appconfig=appconfig
        self.aiservice=aiservice

    @staticmethod
    def to_pinyin_string(text: str) -> str:
        """将汉字字符串转换为无声调、无空格的拼音字符串。"""
        chinese_chars = "".join(filter(str.isalpha, text))
        pinyin_list = pinyin(chinese_chars, style=Style.NORMAL)
        return "".join(item[0] for item in pinyin_list)  

    async def switch_ai_personality(self,msg:GroupMessage)->bool:
        keyword="切换形态"
        if not starts_with_keyword(msg=msg,keyword=keyword):
            return False
        if not (text:=get_text_segment(msg=msg,offset=len(f"/{keyword}"))):
            return False
        system_prompts_path=Path("prompt/system_prompts")
        if text=="随机人格":
            characterPrompts=[read_prompt_file(prompts) for prompts in system_prompts_path.iterdir() if prompts.is_file()]
            system_prompt=random.choice(characterPrompts)
        else:
            text_pinyin=GroupChatTriggerWords.to_pinyin_string(text=text)
            system_prompt=read_prompt_file(f"{system_prompts_path/text_pinyin}.md")
        if not system_prompt:
            await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,text="切换形态失败,未找到人格文件")
            return True
        self.appconfig.messages.clear()
        await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,text="人格已切换")
        self.appconfig.messages=[ChatMessage(role="system", content=system_prompt+self.appconfig.groupChatKnowledgeBase)]
        return True
    
    async def controlAiMode(self,msg:GroupMessage)->bool:
        """控制ai回复模式开关"""
        command_map = {
            "开启ai回复模式": (True, "ai回复模式已开启"),
            "关闭ai回复模式": (False, "ai回复模式已关闭"),
        }
        for keyword, (is_active_state, reply_text) in command_map.items():
            if starts_with_keyword(msg=msg, keyword=keyword):
                self.appconfig.ai_mode_active=is_active_state
                await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,text=reply_text)
                return True
        return False
    
    async def log_user_message_and_id(self,msg:GroupMessage)->bool:
        """储存用户提示词和消息id"""
        if is_reply_and_get_message_id(msg=msg):
            return False
        image_keword="参考生图"
        video_keyword="参考图片生成视频"
        volcengine_image_keyword="1参考生图"
        if starts_with_keyword(msg=msg,keyword=image_keword):
            user_input_text=get_text_segment(msg=msg,offset=len(f"/{image_keword}"))
            if not user_input_text:
              await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,text="提示词为空,请重新输入")
              return True  
            self.appconfig.userIdContentMap[str(msg.user_id)]={"user_input_text":user_input_text,"type":"novelai"}
            await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,text="请发送图片")
            return True
        elif starts_with_keyword(msg=msg,keyword=video_keyword):
            user_input_text=get_text_segment(msg=msg,offset=len(f"/{video_keyword}"))
            if not user_input_text:
              await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,text="提示词为空,请重新输入")
              return True 
            self.appconfig.userIdContentMap[str(msg.user_id)]={"user_input_text":user_input_text,"type":"volcengine"}
            await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,text="请发送图片")
            return True
        elif starts_with_keyword(msg=msg,keyword=volcengine_image_keyword):
            user_input_text=get_text_segment(msg=msg,offset=len(f"/{volcengine_image_keyword}"))
            if not user_input_text:
              await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,text="提示词为空,请重新输入")
              return True 
            self.appconfig.userIdContentMap[str(msg.user_id)]={"user_input_text":user_input_text,"type":"volcengine_即梦4.0"}
            await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,text="请发送图片")
            return True       
        user_input = get_text_segment(msg=msg,offset=1)
        if not user_input:
            return False
        if user_input in self.appconfig.nano_banana_prompts:
            user_input_text=self.appconfig.nano_banana_prompts.get(user_input,{}).get("prompt","")
            self.appconfig.userIdContentMap[str(msg.user_id)]={"user_input_text":user_input_text,"type":"gemini"}
            await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,text="请发送图片")
            return True
        return False
            

    
    async def retract_sent_image(self,msg:GroupMessage)->bool:
        """撤回ai发送的图片"""
        reply_message_id=is_reply_and_get_message_id(msg=msg)
        if not reply_message_id:
            return False
        if not starts_with_keyword(msg=msg,keyword="撤回"):
            return False
        if not reply_message_id in self.appconfig.imageIdBase64Map:
            await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,text="撤回的消息不在储存的列表里")
            return True
        try:
            await self.servicedependencies.bot.api.delete_msg(message_id=reply_message_id)
            del self.appconfig.imageIdBase64Map[reply_message_id]
            return True
        except Exception as e:
            logger.error(f"撤回图片失败: {e}")
            await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,text="撤回图片失败")
        return False
    
    async def listHelpFunctions(self,msg:GroupMessage):
        """help指令"""
        for keyword in self.appconfig.help_texts:
            if not is_message_only_keyword(msg=msg,keyword=keyword):
                continue
            text=self.appconfig.help_texts[keyword]
            await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,text=text)
            return True
        return False
    
    async def sendMessageOnAllMention(self,msg:GroupMessage):  
        """自动TD"""   
        if not check_at_all(msg=msg):
            return False
        text="td"
        await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,text=text)
        return True
        

    
class DelayedAIResponseModule:
    """延迟ai回复模块"""
    def __init__(
        self,
        servicedependencies:ServiceDependencies,
        appconfig:AppConfig,
        aiservice:AiService,  
        ) -> None:
        self.servicedependencies=servicedependencies
        self.appconfig=appconfig
        self.aiservice=aiservice
    
    async def generateDelayedImageResponse(
            self,
            msg:GroupMessage,
        ):
        """延迟图生图(参考模式)"""
        if not str(msg.user_id) in self.appconfig.userIdContentMap:
            return False
        if not (reference_image_base64:=await is_image_message_return_base64(msg=msg,client=self.servicedependencies.fast_track_proxy)):
            return False
        type=self.appconfig.userIdContentMap.get(str(msg.user_id),{}).get("type","")
        if type=="volcengine":
            return False
        # 这里有个我不知道算不算bug的东西:如果用户回复了图片,也可以触发
        store_image_base64_with_message_id_and_timestamp(appconfig=self.appconfig,base64_image=reference_image_base64,message_id=str(msg.message_id))
        user_input_text=self.appconfig.userIdContentMap.get(str(msg.user_id),{}).get("user_input_text","")
        if not user_input_text:
            await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,text="获取列表里的用户提示词失败,我一会去修")
            return True
        if await self.aiservice.process_user_input_to_novlai_image(
            msg=msg,
            user_input_text=user_input_text,
            type=type,
            reference_image_base64=reference_image_base64,
            ):
            if str(msg.user_id) in self.appconfig.userIdContentMap:
                del self.appconfig.userIdContentMap[str(msg.user_id)]
            return True
        return False
    
    async def generateVideoWithImageDelay(self,msg:GroupMessage):
        """延迟参考图片生成视频"""
        if not str(msg.user_id) in self.appconfig.userIdContentMap:
            return False
        if not (reference_image_base64:=await is_image_message_return_base64(msg=msg,client=self.servicedependencies.fast_track_proxy)):
            return False
        type=self.appconfig.userIdContentMap.get(str(msg.user_id),{}).get("type","")
        if type != "volcengine":
            return False
        store_image_base64_with_message_id_and_timestamp(appconfig=self.appconfig,base64_image=reference_image_base64,message_id=str(msg.message_id))
        user_input_text=self.appconfig.userIdContentMap.get(str(msg.user_id),{}).get("user_input_text","")
        if not user_input_text:
            await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,text="获取列表里的用户提示词失败,我一会去修")
            return True
        if await self.aiservice.generateVolcanoEngineVideo(
            msg=msg,
            prompt=user_input_text,
            reference_image_base64=reference_image_base64
            ):
            if str(msg.user_id) in self.appconfig.userIdContentMap:
                del self.appconfig.userIdContentMap[str(msg.user_id)]
            return True
        return False
        
    
class RealTimeAIResponse:
    """即时ai回复模块"""
    def __init__(
        self,
        servicedependencies:ServiceDependencies,
        appconfig:AppConfig,
        aiservice:AiService, 
    ) -> None:
        self.servicedependencies=servicedependencies
        self.appconfig=appconfig
        self.aiservice=aiservice
        
    async def generateImageResponse(
        self,
        msg:GroupMessage,
        ):
        """即时回复图生图"""
        reply_message_id=is_reply_and_get_message_id(msg=msg)
        if not reply_message_id:
            return False
        if reply_message_id not in self.appconfig.imageIdBase64Map:
            return False
        nai_keyword="参考生图"
        volcengine_image_keword="1参考生图"
        user_input=get_text_segment(msg=msg,offset=1)
        reference_image_base64=self.appconfig.imageIdBase64Map[reply_message_id].base64
        if starts_with_keyword(msg=msg,keyword=nai_keyword):
            type="novelai"
            user_input_text=get_text_segment(msg=msg,offset=len(f"/{nai_keyword}"))
        elif user_input in self.appconfig.nano_banana_prompts:
            type="gemini"
            user_input_text=self.appconfig.nano_banana_prompts.get(user_input,{}).get("prompt","")
        elif starts_with_keyword(msg=msg,keyword=volcengine_image_keword):
            type="volcengine_即梦4.0"
            user_input_text=get_text_segment(msg=msg,offset=len(f"/{volcengine_image_keword}"))
        else:
            return False
        if not user_input_text:
            await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,text="提取提示词失败,哥们一会去看看")
            return True
        if await self.aiservice.process_user_input_to_novlai_image(
            msg=msg,
            user_input_text=user_input_text,
            type=type,
            reference_image_base64=reference_image_base64
        ):
            return True
        return False
    
    async def replyWithVideoFromImage(
            self,
            msg:GroupMessage
        ):
        reply_message_id=is_reply_and_get_message_id(msg=msg)
        if not reply_message_id:
            return False
        if reply_message_id not in self.appconfig.imageIdBase64Map:
            return False
        video_keyword="参考图片生成视频"
        if not starts_with_keyword(msg=msg,keyword=video_keyword):
            return False
        user_input_text=get_text_segment(msg=msg,offset=len(f"/{video_keyword}"))
        image_base64=self.appconfig.imageIdBase64Map[reply_message_id].base64
        return await self.aiservice.generateVolcanoEngineVideo(
                msg=msg,
                prompt=user_input_text,
                reference_image_base64=image_base64  # type: ignore
            )

    async def generate_image(
            self,
            msg:GroupMessage
            )->bool:
        """普通文生图,只支持novelai"""
        nai_keyword="生成图片"
        volcengine_image_keword="1生成图片"
        if starts_with_keyword(msg=msg,keyword=nai_keyword):
            user_input_text=get_text_segment(msg=msg,offset=len(f"/{nai_keyword}"))
            type="volcengine_即梦4.0"
        elif starts_with_keyword(msg=msg,keyword=volcengine_image_keword):
            user_input_text=get_text_segment(msg=msg,offset=len(f"/{volcengine_image_keword}"))
            type="novelai"
        else:
            return False
        if not user_input_text:
            await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,text="输入为空亦或者获取图片提示词失败")
            return True
        if await self.aiservice.process_user_input_to_novlai_image(
            msg=msg,
            user_input_text=user_input_text,
            type=type,
        ):
           return True
        return False 
    
    async def get_videos(
            self,
            msg:GroupMessage
        ):
        """文生视频"""
        video_keyword="生成视频"
        if not starts_with_keyword(msg=msg,keyword=video_keyword):
            return False
        user_input_text=get_text_segment(msg=msg,offset=len(f"/{video_keyword}"))
        return await self.aiservice.generateVolcanoEngineVideo(
            msg=msg,
            prompt=user_input_text,
        )
                   
    async def handle_group_message_response(
            self,
            msg:GroupMessage
            )->bool:
        """ai智能水群"""
        if not self.appconfig.ai_mode_active:
            return False
        if not checkMentionBehavior(msg=msg):
            return False
        user_prompt=(
            f"消息发送者资料 - "
            f"QQ号: {getattr(msg.sender, 'user_id', '未知')}, "
            f"QQ昵称: '{getattr(msg.sender, 'nickname', '未知')}', "
            f"群昵称: '{getattr(msg.sender, 'card', '未知')}', "
            f"消息内容: '{msg.raw_message}'"
        )
        self.appconfig.messages.append(ChatMessage(role="user", content=user_prompt))
        image_base64=await is_image_message_return_base64(msg=msg,client=self.servicedependencies.fast_track_proxy)
        if image_base64:
            store_image_base64_with_message_id_and_timestamp(appconfig=self.appconfig,base64_image=image_base64,message_id=msg.message_id)
            self.appconfig.messages.append(ChatMessage(role="user",content=[{ "type": "image_url", "image_url":{"url":  f"data:image/jpeg;base64,{image_base64}"}}]))
        message_id=is_reply_and_get_message_id(msg=msg)
        if message_id in self.appconfig.imageIdBase64Map:
            image_base64_s=self.appconfig.imageIdBase64Map[message_id].base64
            self.appconfig.messages.append(ChatMessage(role="user",content=[{ "type": "image_url", "image_url":{"url":  f"data:image/jpeg;base64,{image_base64_s}"}}]))
        if ai_response_json:= await self.servicedependencies.openai_llm.fetch_json_from_ai_model(
            model_name=self.appconfig.llm_model_name,
            messages=self.appconfig.messages
            ):
            if ai_response_json.startswith("错误消息:"):
                await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,at=msg.user_id,text=ai_response_json)
                return True
            message=parse_llm_json_to_message_array(ai_response_json)
            await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,rtf=message)
            if image_base64:
                del self.appconfig.messages[-1]
            if message_id in self.appconfig.imageIdBase64Map:
                del self.appconfig.messages[-1]
            self.appconfig.messages.append(ChatMessage(role="assistant", content=ai_response_json))
            if len(self.appconfig.messages) > 31: ## 限制对话历史长度，保留1条系统提示和15轮用户/助手对话（1 + 15*2 = 31）
                system_prompt=self.appconfig.messages[0]
                recent_messages = self.appconfig.messages[-6:]
                self.appconfig.messages.clear()
                self.appconfig.messages.append(system_prompt)
                self.appconfig.messages.extend(recent_messages)
            return True
        else:
            await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,text="ai智能水群失败,群友呢?救一下啊")
            return False
    
class OthersHandles:
    def __init__(
        self,
        servicedependencies:ServiceDependencies,
        appconfig:AppConfig,
        aiservice:AiService,   
    ) -> None:
        self.servicedependencies=servicedependencies
        self.appconfig=appconfig
        self.aiservice=aiservice
    async def remove_timed_out_messages(self):
        """定时清理文本消息"""
        while True:
            await asyncio.sleep(7200)
            logger.info(f"用户id和提示词即将清理,内容:{self.appconfig.userIdContentMap}")
            self.appconfig.userIdContentMap.clear()
            logger.info("用户id和提示词清理成功")

    async def dangerous_metacode_injection(
            self,
            msg:GroupMessage
            )->bool:
        """"元代码注入!危险!危险!危险!"""
        keyword="run:\n"
        if not starts_with_keyword(msg=msg,keyword=keyword):
            return False
        if not self.appconfig.root_id==str(msg.user_id):
                await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,text="不是哥们,不是管理员也想玩代码注入?")
                return True
        code_string=get_text_segment(msg=msg,offset=len(f"/{keyword}"))
        if not code_string:
            await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,text="提取注入代码错误")
            return True
        try:
            local_env = {"self": self, "msg": msg}
            indented_code = textwrap.indent(code_string, "    ")
            exec(f"async def __temp_async_func():\n{indented_code}", {**globals(), **local_env}, local_env)
            await local_env['__temp_async_func']()
            return True
        except Exception as e:
            error_info = traceback.format_exc()
            await self.servicedependencies.bot.api.post_group_msg(group_id=msg.group_id,text=f"代码执行错误,错误{error_info}")
            return True


            

          
        


        
        

            
                

            

        




                
                
                



        
    
        

    



        
        
    

