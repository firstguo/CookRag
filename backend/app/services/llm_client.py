from __future__ import annotations

import json
from typing import Any, Dict, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import Settings
from app import setup_logger

logger = setup_logger(__name__)


class OllamaLLMClient:
    """Client for interacting with Ollama LLM for field extraction."""
    
    def __init__(self, settings: Settings):
        self._settings = settings
        self._model = settings.OLLAMA_LLM_MODEL
        self._base_url = settings.OLLAMA_HOST.rstrip('/')
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, max=3.0))
    async def extract_search_fields(self, query: str) -> Dict[str, Any]:
        """
        Extract structured search fields from user query using LLM.
        
        Args:
            query: User's search query
            
        Returns:
            Dictionary with extracted fields:
            - recipe_names: List of recipe names mentioned
            - ingredients: List of ingredient names mentioned
            - tags: List of tags/categories mentioned
            - cook_time_minutes: Optional cooking time filter
            - raw_query: The refined search query (without filters)
        """
        prompt = f"""你是一个中文菜谱搜索助手。请从用户的搜索 query 中提取以下信息，并以 JSON 格式返回：

{{
  "recipe_names": [],  // 提到的菜谱名称列表，如果没有则为空数组
  "ingredients": [],   // 提到的食材/材料名称列表，如果没有则为空数组
  "tags": [],          // 提到的标签/分类（如：素食、快手菜、川菜等），如果没有则为空数组
  "cook_time_minutes": null,  // 如果提到时间要求，转换为分钟数（整数），否则为 null
  "raw_query": ""      // 去除过滤条件后的核心搜索 query 字符串
}}

用户 query: "{query}"

注意：
1. 只返回 JSON，不要包含其他文字
2. 所有字段都必须存在
3. 食材名称要具体（如"鸡蛋"、"土豆"），不要包含量词
4. 如果无法提取某个字段，使用空数组或 null
5. raw_query 应该保留搜索意图的核心描述"""

        logger.debug(f"Extracting fields from query: {query}")
        
        result = await self._chat(prompt)
        
        try:
            # Parse JSON from LLM response
            extracted = json.loads(result)
            logger.info(f"Extracted fields: {extracted}")
            return extracted
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}, response: {result}")
            # Return default structure if parsing fails
            return {
                "recipe_names": [],
                "ingredients": [],
                "tags": [],
                "cook_time_minutes": None,
                "raw_query": query,
            }
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, max=3.0))
    async def _chat(self, prompt: str) -> str:
        """
        Send a chat request to Ollama.
        
        Args:
            prompt: The prompt to send
            
        Returns:
            LLM response text
        """
        url = f"{self._base_url}/api/generate"
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for consistent extraction
                "num_predict": 500,
            }
        }
        
        timeout = httpx.Timeout(self._settings.OLLAMA_TIMEOUT_S)
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        
        response_text = data.get("response", "").strip()
        logger.debug(f"LLM response: {response_text}")
        return response_text
