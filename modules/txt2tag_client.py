
import asyncio
import aiohttp
from typing import List, Optional
import time

DEFAULT_REQUEST_RATE = 1/30

class LLMUrlEntry:
    def __init__(self, url: str, request_rate: float = DEFAULT_REQUEST_RATE, in_flight_count: int = 0):
        self.url: str = url
        self.request_rate: float = request_rate
        self.in_flight_count: int = in_flight_count

class Txt2TagClient:
    def __init__(self, urls: List[str]):
        self.llms = [LLMUrlEntry(url) for url in urls]
        
    
    async def _do_request(self, url: str, text: str, timeout=60) -> Optional[dict]:
        txt2tag_prompt = f"You are a tool that helps tag danbooru images when given a textual image description. Provide me with danbooru tags that accurately fit the following description. {text}"
        prompt = f" A chat between a curious user and an artificial intelligence assistant. The assistant gives helpful, detailed, and polite answers to the user's questions. USER: {txt2tag_prompt} ASSISTANT:"
        async with aiohttp.ClientSession() as session:
            try:
                data = {
                    "prompt": prompt,
                    "temperature": 0.6,
                    "top_p": 0.8,
                    "top_k": 40,
                    "repeat_penalty": 1.18,
                    "echo": False,
                    "max_tokens": 64,
                    "stop": [
                        "\n",
                        "</s>",
                        "<s>",
                        "User:"
                    ]
                }
                async with session.post(url, json=data, timeout=timeout) as response:
                    if not response.ok:
                        return None
                    return await response.json()
            except asyncio.TimeoutError:
                return None
    
    def _choose_llm(self) -> LLMUrlEntry:
        def llm_latency(entry: LLMUrlEntry):
            if entry.request_rate <= 0:
                entry.request_rate = DEFAULT_REQUEST_RATE
            
            return entry.in_flight_count / entry.request_rate
        
        return min(self.llms, key=llm_latency)


    async def request_tags(self, text: str, timeout=60) -> Optional[str]:
        llm = self._choose_llm()

        start_time = time.time()
        output = await self._do_request(llm.url, text, timeout)
        if output is None:
            return None
        
        # update request rate
        request_rate = 1 / (time.time() - start_time)
        if llm.request_rate == 0:
            llm.request_rate = request_rate
        else:
            llm.request_rate = request_rate * 1/3 + llm.request_rate * 2/3

        return output["choices"][0]["text"].replace(" ", ", ")

