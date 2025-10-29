# 标准库
import json
from pathlib import Path
import asyncio
from typing import Any, Dict, List, Optional, Union

# 第三方库
import faiss
import httpx
import numpy as np
import yaml

class RAGSearchEnhancer:
    def __init__(
        self, 
        index_path: Union[str, Path], 
        text_mapping_path: Union[str, Path], 
        embedded_model_api_key: str, 
        yaml_dictionary: Union[str, Path],
        fast_track_proxy:httpx.AsyncClient
        ) -> None:
        self.embedded_model_api_key: str = embedded_model_api_key
        self.faiss_index = faiss.read_index(index_path)
        self.fast_track_proxy=fast_track_proxy
        with open(text_mapping_path, 'r', encoding="utf-8") as f:
            self.mapping_data: Dict[int, str] = json.load(f)
        with open(yaml_dictionary, "r", encoding="utf-8") as f:
            self.yaml_content: Dict[str, Any] = yaml.load(f, Loader=yaml.FullLoader)
    
    async def get_embedding_values(self, input_txt: List[str]) -> Optional[Dict[str, Any]]:
        max_retries=5#重试5次
        url = "https://api.siliconflow.cn/v1/embeddings"
        payload = {
            "model": "Qwen/Qwen3-Embedding-8B",
            "input": input_txt
        }
        headers = {
            "Authorization": f"Bearer {self.embedded_model_api_key}",
            "Content-Type": "application/json"
        }
        for attempt in range(max_retries):
            try:
                response = await self.fast_track_proxy.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.RequestError:
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
        return None
        
    async def query_most_similar_entries(self, query_text: str, top_k: int = 20) -> Optional[List[str]]:
        """
        使用 Faiss 索引根据查询文本找到最相似的前 top_k 个条目。
        """
        # 获取向量表示
        api_response = await self.get_embedding_values([query_text])
        if not (api_response and 'data' in api_response and api_response['data']):
            return None  
        # api_response返回是一个普通的python_list,需要先转化为 NumPy 格式的、float32 类型的数组,用[...]形式把他变成一个(1, D)的二维数组，表示1个 D 维的查询向量
        query_vector = np.array([api_response['data'][0]['embedding']]).astype('float32')
        # 归一化
        faiss.normalize_L2(query_vector)
        # 开始搜索,返回距离和索引,这里的索引和text_mapping是一一对应的
        distances, indices = self.faiss_index.search(query_vector, top_k)
        # 遍历indices,提取对应的text_mapping映射文本,如果查询不到可能会返回-1,需要过滤掉
        top_results = [self.mapping_data[i] for i in indices[0] if i != -1]
        return top_results
    
    async def get_vector_query_results(self, user_input: str) -> Optional[List[str]]:
        # 执行查询
        best_matches = await self.query_most_similar_entries(user_input)
        if not best_matches:
            return None
        return best_matches
    
    def get_details_from_yaml_by_names(self, best_matches:List[str]) -> Dict[str, Any]:
        """根据相似度匹配的名称从YAML内容中获取详细信息"""
        result_collection = {}
        for name in best_matches:
            for key, value in self.yaml_content.items():
                if value["name"] == name:
                    result_collection.update({f"{key}": value})
        return result_collection
        
        
        