# 标准库
import json
from typing import List, Optional, Tuple

# 第三方库
from ncatbot.core import At, AtAll, MessageChain, Text

# 本地模块
from base import CharCaption


def parse_llm_json_to_message_array(ai_response_json: str) ->tuple[MessageChain,bool] :
    """解析大语音模型的json文本并且构造MessageChain消息容器"""
    message_elements = []

    response_data = json.loads(ai_response_json)
    
    if "Text" in response_data and isinstance(response_data["Text"], str):
        text = response_data["Text"].strip()
        message_elements.append(Text(text))

    if "At" in response_data and isinstance(response_data["At"], list):
        for user_id in response_data["At"]:
            message_elements.append(At(user_id))

    if "AtAll" in response_data and response_data["AtAll"] is True:
        message_elements.append(AtAll())

    if "And_conversation_switch" in response_data:
        and_conversation_switch=response_data["And_conversation_switch"]

    return MessageChain(message_elements),and_conversation_switch

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

    
    






