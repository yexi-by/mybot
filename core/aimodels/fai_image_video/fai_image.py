import types


async def get_image(
        fal_client:types.ModuleType,
        prompt:str,
        model_path:str="fal-ai/bytedance/seedream/v4/edit",
        image_base64s:list|None=None,
        image_size:tuple[int,int]|None=None,
    )->str:
    arguments: dict[str, str|bool | list[str] | dict] = {"prompt":prompt,"sync_mode":True,"enable_safety_checker":False}
    if image_base64s:
        image_base64s_list=[f"data:image/png;base64,{image_base64}" for image_base64 in image_base64s]
        arguments["image_urls"]=image_base64s_list
    if image_size:
        width,height=image_size
        output_image_size={
            "width": width,
            "height": height
        }
        arguments["image_size"]=output_image_size

    handler=await fal_client.submit_async(
        application=model_path,
        arguments=arguments

    )
    result = await handler.get()
    img_url  = result["images"][0]["url"]
    if not isinstance(img_url, str):
        raise ValueError(f"Unexpected image url type: {type(img_url)}")
    if img_url.startswith("data:"):
        header, b64_str = img_url.split(",", 1)     
    return b64_str


async def qqbot_get_image(
        fal_client:types.ModuleType,
        prompt:str,
        image_base64s:str|None,
        image_size:tuple[int,int]|None=None,
    ):
    image_base64s_list=[image_base64s]
    b64_str=await get_image(
        fal_client=fal_client,
        prompt=prompt,
        image_size=image_size,
        image_base64s=image_base64s_list,

    )
    return b64_str