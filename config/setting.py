import os
import yaml
def load_yaml_config():
    try:
        with open('config/mybot_config.yaml', 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        return {}
    
config = load_yaml_config()
novelai_api_key=config.get("providers",{}).get("novelai", {}).get("api_key", "")
deepseek_model_name = config.get("providers",{}).get("deepseek", {}).get("model_names", "")
deepseek_base_url = config.get("providers",{}).get("deepseek", {}).get("base_url", "")
deepseek_api_key = config.get("providers",{}).get("deepseek", {}).get("api_key", "")
gemini_model_name = config.get("providers",{}).get("gemini", {}).get("model_name", "")
gemini_base_url = config.get("providers",{}).get("gemini", {}).get("base_url", "")
gemini_api_key = config.get("providers",{}).get("gemini", {}).get("api_key", "")
siliconflow_api_key=os.getenv('SILICONFLOW_API_KEY','')
boot_id=config.get('ids', {}).get('boot', '')
root_id=config.get('ids', {}).get('root', [])

groups_config = config.get("groups", {})