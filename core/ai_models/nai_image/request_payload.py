from .huashichuan import 预设画师串_二次元_正面,预设画师串_二次元_负面,三d正面,三d负面
from typing import List, Optional
from base import Center, CharCaption

def get_payload(
    prompt:str,
    new_negative_prompt:str,
    width:int,
    height:int,
    seed:int,
    v4_prompt_char_captions: Optional[List[CharCaption]],
    image_base64:str|None=None,
    model="nai-diffusion-4-5-full",

    #char_captions默认格式为:[{"char_caption":"正面提示词",#正面提示词需要boy或者girl或者?起手
    # "centers":[{"x":0.5,"y":0.5}]},#此为坐标
    # {.....第二个角色}]#依次插入其他角色
    #与 负面角色列表和v4_prompt_char_captions同理,不过我看官网好像是负面提示词部分为"",且坐标和必须和其保持一致

  ):

    payload={
        "model": model,  # 使用的AI模型名称
        "action": "generate",  # 执行的操作类型：生成图片
        "parameters": {  # 生成参数配置
            "params_version": 3,  # 参数版本号
            "width": width,  # 生成图片的宽度（像素）
            "height": height,  # 生成图片的高度（像素）
            "scale": 10,  # CFG缩放值，控制生成质量
            "sampler": "k_euler_ancestral",  # 采样器类型
            "steps": 28,  # 采样步数，影响生成质量和时间
            "n_samples": 1,  # 生成图片的数量
            "ucPreset": 0,  # 未分类提示词预设
            "qualityToggle": True,  # 质量切换开关
            "autoSmea": False,  # 自动SMEA功能开关
            "dynamic_thresholding": True,  # 动态阈值处理开关
            "controlnet_strength": 1,  # ControlNet强度
            "legacy": False,  # 是否使用旧版模式
            "add_original_image": True,  # 是否添加原始图片
            "cfg_rescale": 0.7,  # CFG重缩放参数
            "noise_schedule": "karras",  # 噪声调度类型
            "legacy_v3_extend": False,  # 旧版V3扩展功能
            "skip_cfg_above_sigma": None,  # 在指定sigma值以上跳过CFG
            "use_coords": False,  # 是否使用坐标信息(疑似旧参数,暂且不用)
            "normalize_reference_strength_multiple": True,  # 标准化参考强度倍数
            "inpaintImg2ImgStrength": 1,  # 图像修复强度
            "v4_prompt": {  # V4版本提示词配置
            "caption": {  # 标题配置
                "base_caption": f"{prompt},{预设画师串_二次元_正面},",  # 基础标题描述
                "char_captions": []  # 角色标题列表
            },
            "use_coords": False,  # 在V4提示词中使用坐标
            "use_order": True  # 在V4提示词中使用顺序
            },
            "v4_negative_prompt": {  # V4版本负面提示词配置
            "caption": {  # 负面标题配置
                "base_caption": f"{new_negative_prompt},{预设画师串_二次元_负面},",  # 基础负面描述
                "char_captions": []  # 角色负面标题列表
            },
            "legacy_uc": False  # 旧版未分类模式
            },
            "legacy_uc": False,  # 旧版未分类模式（全局）
            "seed": seed,  # 随机种子，用于生成可重现的结果
            "characterPrompts": [],  # 角色提示词列表
            "negative_prompt": "",
            "deliberate_euler_ancestral_bug": False,  # 故意保留Euler祖先采样器的错误
            "prefer_brownian": True  # 偏好布朗运动采样
        }
        }
    if image_base64:
        payload["parameters"]["director_reference_images"] = [image_base64] # 导演参考图像列表
        payload["parameters"]["director_reference_descriptions"] = [{
            "caption": {# 参考描述标题
                "base_caption": "character&style",# 基础参考描述
                "char_captions": []# 角色参考描述列表
            },
            "legacy_uc": False # 旧版未分类模式
        }]# 导演参考描述列表
        payload["parameters"]["director_reference_information_extracted"] = [1] # 提取状态值
        payload["parameters"]["director_reference_strength_values"] = [1]# 参考强度值
    if v4_prompt_char_captions:
        payload["parameters"]["use_coords"]=True
        payload["parameters"]["v4_prompt"]["use_coords"]=True
        for char_caption in v4_prompt_char_captions:
            payload["parameters"]["v4_prompt"]["caption"]["char_captions"].append(char_caption)
            negative_char_data = {
                "char_caption": "",  # 负面提示词为空字符串
                "centers": char_caption.centers  # 使用相同的坐标
            }
            payload["parameters"]["v4_negative_prompt"]["caption"]["char_captions"].append(negative_char_data)
            char_prompt_data = {
                "prompt": char_caption.char_caption,
                "uc": "",
                "center": char_caption.centers[0],  # 注意这里是单个center对象
                "enabled": True
            }
            payload["parameters"]["characterPrompts"].append(char_prompt_data)

            
            
    return payload
