import random
import asyncio
import datetime
import json
from base import ChatMessage
from typing import Dict, List, Union
from .ai_services.openAI_llm import OpenAI_LLM
from .group_context import GroupContext
from utilities.logging import logger
from utilities.json_parser import parse_llm_json_to_message_array,buildTextToImagePrompt
from utilities.embedding_search import RAGSearchEnhancer
from .nai_image.character_reference_image import get_character_reference_image
from pathlib import Path
from ncatbot.core import GroupMessageEvent,BotClient
from pypinyin import pinyin, Style
from base import ChatMessage, ImageData
from ncatbot.core.event.message_segment import(
    MessageArray,  
    Text,          
    At,            
    AtAll,
    Image,
)
from utilities.utils import (
    starts_with_keyword,
    get_text_segment,
    checkMentionBehavior,
    is_reply_and_get_message_id,
    is_image_message_return_base64,
    read_prompt_file,
)
class AICommandHandler:
    def __init__(self,bot:BotClient,groupcontext:GroupContext,openai_llm:OpenAI_LLM,rgasearchenhancer:RAGSearchEnhancer) -> None:
        self.bot=bot
        self.groupcontext=groupcontext
        self.openai_llm=openai_llm
        self.rgasearchenhancer=rgasearchenhancer

    def _store_image_base64_with_message_id_and_timestamp(self,message_id:str,base64_image:str):
        """储存图片base64编码以及对应的消息id,附带时间"""
        self.groupcontext.imageIdBase64Map[message_id] = ImageData(
            base64=base64_image,
            timestamp=datetime.datetime.now().timestamp()
        )
        if len(self.groupcontext.imageIdBase64Map)>=60:
            oldest_key =min(self.groupcontext.imageIdBase64Map, key=lambda k: self.groupcontext.imageIdBase64Map[k].timestamp)
            del self.groupcontext.imageIdBase64Map[oldest_key]

    async def _generate_image(
            self,
            ai_response_json:str,
            novelai_api_lock:asyncio.Lock,
            reference_image_base64:str|None=None
            ):
        """生图模块"""
        prompt,negative_prompt,char_captions=buildTextToImagePrompt(ai_response_json)
        if not prompt or not negative_prompt or not char_captions:
            return False
        
        if image_base64:=await get_character_reference_image(
            novelai_api_lock=novelai_api_lock,
            novelai_api_key=self.groupcontext.novelai_api_key,
            prompt=prompt,
            new_negative_prompt=negative_prompt,
            width=1024,
            height=1024,
            image_base_64_string=reference_image_base64,
            v4_prompt_char_captions=char_captions
            ):
            return image_base64
        
    async def _insert_vectorized_data_dynamically(self,user_input_text:str)->None|List[ChatMessage]:
        """动态插入向量化数据到系统提示词并且构建image_messages"""
        if not (best_matches:=await self.rgasearchenhancer.get_vector_query_results(user_input=user_input_text)):
            return None
        if not (result_collection:=self.rgasearchenhancer.get_details_from_yaml_by_names(best_matches=best_matches)):
            return None
        system_prompt=self.groupcontext.image_messages[0].content
        image_messages=[ChatMessage(role="system", content=f"{system_prompt}\n\n以下是向量动态插入字典对照表,请甄别后参考\n{result_collection}")]
        image_messages.append(ChatMessage(role="user", content=user_input_text))
        return image_messages
    
    async def _process_user_input_to_image(self,msg:GroupMessageEvent,user_input_text:str,novelai_api_lock:asyncio.Lock,reference_image_base64:str|None=None)->bool:
        """整合了从用户输入到生成图片的通用方法"""
        image_messages = await self._insert_vectorized_data_dynamically(user_input_text=user_input_text)
        if not image_messages:
            await self.bot.api.post_group_msg(group_id=msg.group_id,text="向量化插入失败,请重试")
            return True
        if not (ai_response_json:=await self.openai_llm.fetch_json_from_ai_model(model_name=self.groupcontext.llm_model_name,messages=image_messages)):
            return False
        if image_base64:= await self._generate_image(
            ai_response_json=ai_response_json,
            novelai_api_lock=novelai_api_lock,
            reference_image_base64=reference_image_base64
        ):
            image_message=MessageArray([Image(image_base64)])
            await self.bot.api.post_group_msg(group_id=msg.group_id,text="图片生成完成")
            message_id=await self.bot.api.post_group_msg(group_id=msg.group_id,rtf=image_message)
            self._store_image_base64_with_message_id_and_timestamp(message_id=message_id,base64_image=image_base64)
            return True
        return False      

    async def switch_ai_personality(self,msg:GroupMessageEvent)->bool:
        """切换ai核心人格"""
        if not starts_with_keyword(msg=msg,keyword="切换形态"):
            return False
        def to_pinyin_string(text: str) -> str:
            """将汉字字符串转换为无声调、无空格的拼音字符串。"""
            chinese_chars = "".join(filter(str.isalpha, text))
            pinyin_list = pinyin(chinese_chars, style=Style.NORMAL)
            return "".join(item[0] for item in pinyin_list)        
        if not (text:=get_text_segment(msg=msg,offset=5)):
            return False
        system_prompts_path=Path("prompt/system_prompts")
        if text=="随机人格":
            characterPrompts=[read_prompt_file(prompts) for prompts in system_prompts_path.iterdir() if prompts.is_file]
            system_prompt=random.choice(characterPrompts)
            self.groupcontext.messages.clear()
            if system_prompt:
                self.groupcontext.messages=[ChatMessage(role="system", content=system_prompt+self.groupcontext.groupChatKnowledgeBase)]
                return True
        else:
            text_pinyin=to_pinyin_string(text=text)
            system_prompt=read_prompt_file(f"{system_prompts_path/text_pinyin}.md")
            self.groupcontext.messages.clear()
            if system_prompt:
                self.groupcontext.messages=[ChatMessage(role="system", content=system_prompt+self.groupcontext.groupChatKnowledgeBase)]
                return True
        return False
    
    async def remove_timed_out_messages(self):
        """定时清理文本消息"""
        while True:
            await asyncio.sleep(7200)
            self.groupcontext.userMessageIdContentMap.clear()
        
    async def handle_group_message_response(self,msg:GroupMessageEvent)->bool:
        """ai智能水群"""
        if not self.groupcontext.ai_mode_active:
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
        self.groupcontext.messages.append(ChatMessage(role="user", content=user_prompt))
        if ai_response_json:= await self.openai_llm.fetch_json_from_ai_model(model_name=self.groupcontext.llm_model_name,messages=self.groupcontext.messages):
            messagearra=parse_llm_json_to_message_array(ai_response_json)
            await self.bot.api.post_group_msg(group_id=msg.group_id,rtf=messagearra)
            self.groupcontext.messages.append(ChatMessage(role="assistant", content=ai_response_json))
            if len(self.groupcontext.messages) > 31:
                system_prompt=self.groupcontext.messages[0]
                recent_messages = self.groupcontext.messages[-6:]
                self.groupcontext.messages.clear()
                self.groupcontext.messages.append(system_prompt)
                self.groupcontext.messages.extend(recent_messages)
            return True
        return False
    
    async def log_user_message_and_id(self,msg:GroupMessageEvent)->bool:
        """储存用户提示词和消息id"""
        if not starts_with_keyword(msg=msg,keyword="参考生图"):
            return False
        if user_input_text:=get_text_segment(msg=msg,offset=5):
            self.groupcontext.userMessageIdContentMap[msg.message_id]=user_input_text
            return True
        return False
    
    
    async def generate_image(self,msg:GroupMessageEvent,novelai_api_lock:asyncio.Lock)->bool:
        """文生图功能模块"""
        if not starts_with_keyword(msg=msg,keyword="生成图片"):
            return False
        user_input_text=get_text_segment(msg=msg,offset=5)
        if not user_input_text:
            return False
        if user_input_text=="":
            await self.bot.api.post_group_msg(group_id=msg.group_id,text="未检查到有效内容,请重新输入")
            return True
        return await self._process_user_input_to_image(
            msg=msg,
            user_input_text=user_input_text,
            novelai_api_lock=novelai_api_lock
        )       

    async def generateDelayedImageResponse(self,msg:GroupMessageEvent,novelai_api_lock:asyncio.Lock)->bool:
        """延迟图生图(参考模式)"""
        if not msg.message_id in self.groupcontext.userMessageIdContentMap:
            return False
        if not (reference_image_base64:=await is_image_message_return_base64(msg=msg)):
            return False
        if not(user_input_text:=self.groupcontext.userMessageIdContentMap[msg.message_id]):
             return False
        return await self._process_user_input_to_image(
            msg=msg,
            user_input_text=user_input_text,
            novelai_api_lock=novelai_api_lock,
            reference_image_base64=reference_image_base64
        )
    
    async def generateImageResponse(self,msg:GroupMessageEvent,novelai_api_lock:asyncio.Lock)->bool:
        """即时回复图生图(参考模式)"""
        if not (reply_message_id:=is_reply_and_get_message_id(msg=msg)) or reply_message_id not in self.groupcontext.imageIdBase64Map:
            return False
        if not (reference_image_base64:=self.groupcontext.imageIdBase64Map[reply_message_id].base64):
            return False
        if not (user_input_text:=get_text_segment(msg=msg,offset=0)):
            await self.bot.api.post_group_msg(group_id=msg.group_id,text="未检查到有效内容,请重新输入")
            return True
        return await self._process_user_input_to_image(
            msg=msg,
            user_input_text=user_input_text,
            novelai_api_lock=novelai_api_lock,
            reference_image_base64=reference_image_base64
        )
         
    async def controlAiMode(self,msg:GroupMessageEvent)->bool:
        """控制ai开关"""
        if starts_with_keyword(msg=msg,keyword="关闭ai回复模式"):
            self.groupcontext.ai_mode_active=False
            await self.bot.api.post_group_msg(group_id=msg.group_id,text="ai回复模式已关闭")
            return True
        elif starts_with_keyword(msg=msg,keyword="开启ai回复模式"):
            self.groupcontext.ai_mode_active=True
            await self.bot.api.post_group_msg(group_id=msg.group_id,text="ai回复模式已开启")
            return True
        return False
    
    async def retract_sent_image(self,msg:GroupMessageEvent)->bool:
        """撤回ai发送的图片"""
        if not (message_id:=is_reply_and_get_message_id(msg=msg)) or starts_with_keyword(msg=msg,keyword="撤回"):
            return False
        if not message_id in self.groupcontext.imageIdBase64Map:
            return False
        try:
            await self.bot.api.delete_msg(message_id=message_id)
            del self.groupcontext.imageIdBase64Map[message_id]
            return True
        except:
            logger.error(f"撤回图片失败,消息id:{message_id}")
            await self.bot.api.post_group_msg(group_id=msg.group_id,text="撤回图片失败")
        return False

            
        

        
        


        






  


            




























