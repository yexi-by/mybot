from ncatbot.core import BotClient
from typing import cast
async def unban_user(msg:dict,bot:BotClient):
    if msg.get("notice_type") == "group_ban":
        if msg.get("sub_type") == "ban":  
            group_id = cast(int,msg.get("group_id"))   # 群号
            user_id = msg.get("user_id")      # 被禁言的人
            operator_id = msg.get("operator_id") # 执行禁言的人
            duration = msg.get("duration")
            if user_id==2172959822:
                await bot.api.set_group_ban(group_id=group_id, user_id=user_id, duration=0)