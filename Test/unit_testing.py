import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utilities.utils import is_reply_and_get_message_id,get_text_segment

class FakeMessage:
    def __init__(self, message_data):
        self.message = message_data

fake_msg_data_reply = [{'type': 'reply', 'data': {'id': '12345'}}, {'type': 'text', 'data': {'text': ' /真人化'}}]
msg_reply = FakeMessage(message_data=fake_msg_data_reply)
message=get_text_segment(msg=msg_reply,offset=2)
if message=="真人化":
    print(len(message))
else:
    print(message)