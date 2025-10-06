# 标准库
import base64
from io import BytesIO

# 第三方库
from google import genai
from PIL import Image


async def text_and_image_to_image(client: genai.Client, prompt: str, image_base64: str, model_name: str) -> str | None:
    # 将 base64 字符串转换为 PIL Image 对象 (PNG 格式)
    image_data = base64.b64decode(image_base64)
    image = Image.open(BytesIO(image_data)).convert('RGB')
    
    response = await client.aio.models.generate_content(
        model=model_name,
        contents=[prompt, image],
    )
    
    if not response.candidates or not response.candidates[0].content or not response.candidates[0].content.parts:
        return None
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None and part.inline_data.data is not None:
            image_base_64 = base64.b64encode(part.inline_data.data).decode('utf-8')
            return image_base_64
    return None