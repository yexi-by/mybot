
from typing import Dict, List, Union
from base import ChatMessage, ImageData

class GroupContext():
    def __init__(self,chatSystemPrompt:str,groupChatKnowledgeBase:str,drawing_system_prompt:str,llm_model_name:str,novelai_api_key:str):
        self.groupChatKnowledgeBase:str =groupChatKnowledgeBase
        self.messages:List[ChatMessage]=[ChatMessage(role="system", content=chatSystemPrompt+self.groupChatKnowledgeBase)]
        self.image_messages:List[ChatMessage]=[ChatMessage(role="system", content=drawing_system_prompt)]
        self.imageIdBase64Map:Dict[str, ImageData] = {}#用来储存图片base64编码以及对应的消息id,附带时间
        self.userMessageIdContentMap:Dict[str,str]={}#用来储存文本消息以及对应的消息id
        self.llm_model_name:str=llm_model_name
        self.ai_mode_active: bool = True
        self.novelai_api_key:str=novelai_api_key

    





    
