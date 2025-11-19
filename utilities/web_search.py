from tavily import AsyncTavilyClient
import openai
class Web_search:
    def __init__(self,client:AsyncTavilyClient) -> None:
        self.client=client
    
    async def get_web_search(
        self,
        query:str,
    ):
        response = await self.client.search(
            query=query
        )
        return response
