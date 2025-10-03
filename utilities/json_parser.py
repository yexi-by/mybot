import json
from typing import Dict, Any, List, Union, Tuple,Optional
from base import CharCaption, Center, ChatMessage
from ncatbot.core.event.message_segment import (
    MessageArray,  
    Text,          
    At,            
    AtAll,
    Image,
)
def parse_llm_json_to_message_array(ai_response_json: str) -> MessageArray:
    """解析大语音模型的json文本并且构造MessageArray消息容器"""
    message_elements = []
    response_data = json.loads(ai_response_json)
    
    if "Text" in response_data and isinstance(response_data["Text"], str):
        text = response_data["Text"].strip()
        message_elements.append(Text(text))

    if "At" in response_data and isinstance(response_data["At"], list):
        for user_id in response_data["At"]:
            if isinstance(user_id, (int, str)):
                message_elements.append(At(str(int(user_id))))

    if "AtAll" in response_data and response_data["AtAll"] is True:
        message_elements.append(AtAll())
    
    return MessageArray(message_elements)

def buildTextToImagePrompt(ai_response_json: str) -> Tuple[Optional[str], Optional[str], Optional[List[CharCaption]]]:
    """解析大语音模型的json文本并且构造文生图提示词"""
    response_data = json.loads(ai_response_json)
    prompt=None
    negative_prompt=None
    char_captions=None
    
    
    if "prompt" in response_data and isinstance(response_data["prompt"], str):
        prompt = response_data["prompt"].strip()
    
    if "negative_prompt" in response_data and isinstance(response_data["negative_prompt"], str):
        negative_prompt = response_data["negative_prompt"].strip()
    
    if "char_captions" in response_data and isinstance(response_data["char_captions"], list):
        char_captions = [CharCaption(**caption) for caption in response_data["char_captions"]]
    return prompt,negative_prompt,char_captions

    
    






