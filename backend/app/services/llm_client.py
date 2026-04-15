from __future__ import annotations

import json
from typing import Any, Dict, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import Settings
from app import setup_logger

logger = setup_logger(__name__)


class LLMClient:
    """LangChain-based LLM client for field extraction.
    
    Supports multiple providers:
    - Qwen/Tongyi Qianwen (DashScope)
    - DeepSeek
    - Ollama (local)
    """
    
    def __init__(self, settings: Settings):
        self._settings = settings
        self._llm = self._initialize_llm()
        self._parser = JsonOutputParser()
    
    def _initialize_llm(self) -> ChatOpenAI:
        """Initialize LLM based on provider configuration."""
        provider = self._settings.LLM_PROVIDER.lower()
        
        logger.info(f"Initializing LLM with provider: {provider}")
        
        if provider == "qwen":
            return self._init_qwen()
        elif provider == "deepseek":
            return self._init_deepseek()
        elif provider == "ollama":
            return self._init_ollama()
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}. Choose from: qwen, deepseek, ollama")
    
    def _init_qwen(self) -> ChatOpenAI:
        """Initialize Qwen/Tongyi Qianwen via DashScope."""
        if not self._settings.QWEN_API_KEY:
            raise ValueError("QWEN_API_KEY is required for Qwen provider")
        
        logger.info(f"Initializing Qwen model: {self._settings.QWEN_MODEL}")
        
        return ChatOpenAI(
            model=self._settings.QWEN_MODEL,
            api_key=self._settings.QWEN_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            temperature=0.1,
            max_tokens=500,
        )
    
    def _init_deepseek(self) -> ChatOpenAI:
        """Initialize DeepSeek API."""
        if not self._settings.DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY is required for DeepSeek provider")
        
        logger.info(f"Initializing DeepSeek model: {self._settings.DEEPSEEK_MODEL}")
        
        return ChatOpenAI(
            model=self._settings.DEEPSEEK_MODEL,
            api_key=self._settings.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com/v1",
            temperature=0.1,
            max_tokens=500,
        )
    
    def _init_ollama(self) -> ChatOpenAI:
        """Initialize Ollama local LLM."""
        logger.info(f"Initializing Ollama model: {self._settings.OLLAMA_LLM_MODEL}")
        
        return ChatOpenAI(
            model=self._settings.OLLAMA_LLM_MODEL,
            base_url=f"{self._settings.OLLAMA_HOST.rstrip('/')}/v1",
            api_key="ollama",  # Ollama doesn't require API key
            temperature=0.1,
            max_tokens=500,
        )
    
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
        logger.debug(f"Extracting fields from query: {query}")
        
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的中文菜谱搜索助手。你的任务是从用户的搜索 query 中提取结构化信息。

请提取以下信息并以 JSON 格式返回：
- recipe_names: 提到的菜谱名称列表，如果没有则为空数组
- ingredients: 提到的食材/材料名称列表，如果没有则为空数组
- tags: 提到的标签/分类（如：素食、快手菜、川菜、辣等），如果没有则为空数组
- cook_time_minutes: 如果提到时间要求，转换为分钟数（整数），否则为 null
- raw_query: 去除过滤条件后的核心搜索 query 字符串

重要规则：
1. 必须返回有效的 JSON 格式
2. 所有字段都必须存在，不能省略
3. 食材名称要具体（如"鸡蛋"、"土豆"），不要包含量词（如"个"、"斤"）
4. 如果无法提取某个字段，使用空数组 [] 或 null
5. raw_query 应该保留搜索意图的核心描述，去除明确的过滤条件
6. 只返回 JSON，不要包含任何其他文字或解释"""),
            ("human", "用户 query: {query}")
        ])
        
        try:
            # Create chain: prompt -> LLM -> parser
            chain = prompt | self._llm | self._parser
            
            # Execute the chain
            result = await chain.ainvoke({"query": query})
            
            # Validate and normalize result
            extracted = self._normalize_extracted_fields(result)
            
            logger.info(f"Successfully extracted fields: {extracted}")
            return extracted
            
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            # Return default structure if extraction fails
            return {
                "recipe_names": [],
                "ingredients": [],
                "tags": [],
                "cook_time_minutes": None,
                "raw_query": query,
            }
    
    def _normalize_extracted_fields(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and validate extracted fields."""
        return {
            "recipe_names": result.get("recipe_names", []) or [],
            "ingredients": result.get("ingredients", []) or [],
            "tags": result.get("tags", []) or [],
            "cook_time_minutes": result.get("cook_time_minutes", None),
            "raw_query": result.get("raw_query", "").strip() or "",
        }
