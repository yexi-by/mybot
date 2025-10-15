from volcenginesdkarkruntime import AsyncArk 

async def get_volcengine_image(
        client:AsyncArk,
        prompt:str,
        iamgebase64:str|None=None,
        model_name:str="doubao-seedream-4-0-250828",
        size:str="2K",
        sequential_image_generation:str="disabled",#生成图片数量"auto"为自动,"disabled"为1
        response_format:str="b64_json",
        watermark:bool=False
    ):
    image=None
    if iamgebase64:
        image=[f"data:image/png;base64,{iamgebase64}"]
    imagesresponse=await client.images.generate(
        model=model_name,
        prompt=prompt,
        image=image,
        size=size,
        sequential_image_generation = sequential_image_generation,
        response_format=response_format,
        watermark=watermark,
        )
    for image in imagesresponse.data:
        return image.b64_json

