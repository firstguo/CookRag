# LLM Client Refactoring Summary

## Changes Overview

The LLM client has been successfully refactored from a custom Ollama-only implementation to a **LangChain-based multi-provider solution**.

## What Changed

### 1. **New Dependencies**

Added to `requirements.txt`:
```txt
langchain==0.3.9
langchain-openai==0.2.9
langchain-community==0.3.7
dashscope==1.20.0
```

### 2. **Configuration Updates**

**Old** (`.env`):
```bash
OLLAMA_LLM_MODEL=qwen2.5:7b
```

**New** (`.env`):
```bash
# Select provider
LLM_PROVIDER=qwen  # qwen | deepseek | ollama

# Qwen config
QWEN_API_KEY=sk-xxx
QWEN_MODEL=qwen-turbo

# DeepSeek config
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_MODEL=deepseek-chat

# Ollama config (local)
OLLAMA_LLM_MODEL=qwen2.5:7b
```

### 3. **Code Changes**

#### File: `app/services/llm_client.py`

**Before**:
```python
class OllamaLLMClient:
    def __init__(self, settings: Settings):
        self._model = settings.OLLAMA_LLM_MODEL
        self._base_url = settings.OLLAMA_HOST.rstrip('/')
    
    async def _chat(self, prompt: str) -> str:
        # Manual HTTP request to Ollama
        url = f"{self._base_url}/api/generate"
        # ... manual request handling
```

**After**:
```python
class LLMClient:
    def __init__(self, settings: Settings):
        self._llm = self._initialize_llm()  # LangChain ChatOpenAI
        self._parser = JsonOutputParser()
    
    def _init_qwen(self) -> ChatOpenAI:
        return ChatOpenAI(
            model=settings.QWEN_MODEL,
            api_key=settings.QWEN_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    
    async def extract_search_fields(self, query: str) -> Dict[str, Any]:
        # LangChain chain: prompt -> llm -> parser
        chain = prompt | self._llm | self._parser
        result = await chain.ainvoke({"query": query})
```

#### File: `app/main.py`

**Before**:
```python
from app.services.llm_client import OllamaLLMClient
app.state.llm_client = OllamaLLMClient(settings)
```

**After**:
```python
from app.services.llm_client import LLMClient
app.state.llm_client = LLMClient(settings)
```

#### File: `app/api/search.py`

**Before**:
```python
from app.services.llm_client import OllamaLLMClient
llm_client: OllamaLLMClient = request.app.state.llm_client
```

**After**:
```python
from app.services.llm_client import LLMClient
llm_client: LLMClient = request.app.state.llm_client
```

## Key Improvements

### ✅ Benefits

1. **Multi-Provider Support**
   - Qwen/Tongyi Qianwen (recommended for Chinese)
   - DeepSeek (good alternative)
   - Ollama (local, free)

2. **Better Code Quality**
   - LangChain's standardized interface
   - Prompt templates for maintainability
   - JSON output parser for reliable parsing
   - Cleaner error handling

3. **Production Ready**
   - Automatic retry (3 attempts)
   - Comprehensive logging
   - Graceful fallback on errors
   - Field normalization

4. **Flexibility**
   - Switch providers via environment variable
   - No code changes needed
   - Easy to add new providers

5. **Maintainability**
   - Standard LangChain patterns
   - Well-documented
   - Easy to test
   - Clear separation of concerns

## Migration Checklist

- [x] Add LangChain dependencies to requirements.txt
- [x] Update Settings class with new LLM configs
- [x] Refactor llm_client.py to use LangChain
- [x] Update main.py initialization
- [x] Update search.py imports
- [x] Update .env.example with new configs
- [x] Create comprehensive documentation

## Testing Guide

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Provider

**Option A: Qwen (Recommended)**
```bash
# Get API key from: https://dashscope.console.aliyun.com/
echo 'LLM_PROVIDER=qwen' >> .env
echo 'QWEN_API_KEY=sk-your-key' >> .env
echo 'QWEN_MODEL=qwen-turbo' >> .env
```

**Option B: DeepSeek**
```bash
# Get API key from: https://platform.deepseek.com/
echo 'LLM_PROVIDER=deepseek' >> .env
echo 'DEEPSEEK_API_KEY=sk-your-key' >> .env
echo 'DEEPSEEK_MODEL=deepseek-chat' >> .env
```

**Option C: Ollama (Local)**
```bash
# Install Ollama: https://ollama.ai
ollama pull qwen2.5:7b

echo 'LLM_PROVIDER=ollama' >> .env
echo 'OLLAMA_LLM_MODEL=qwen2.5:7b' >> .env
```

### 3. Test the API

```bash
# Start the backend
cd backend
uvicorn app.main:app --reload

# Test search with LLM extraction
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "我想找有鸡蛋和土豆的快手菜，20分钟内能做完的",
    "use_llm_extraction": true,
    "min_similarity": 0.6
  }'
```

### 4. Verify Logs

Check for these log messages:
```
INFO - Initializing LLM with provider: qwen
INFO - Initializing Qwen model: qwen-turbo
INFO - Using LLM for field extraction
INFO - Successfully extracted fields: {...}
```

## Provider Comparison

| Feature | Qwen | DeepSeek | Ollama |
|---------|------|----------|--------|
| Chinese Support | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Speed | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Cost | Low | Low | Free |
| Setup | Easy | Easy | Medium |
| Quality | High | High | Medium-High |
| Privacy | Cloud | Cloud | Local |

## Performance Metrics

**Expected Latency** (field extraction):
- Qwen-turbo: ~500ms
- Qwen-plus: ~800ms
- DeepSeek: ~1000ms
- Ollama 7B: ~2000ms
- Ollama 14B: ~3000ms

**Cost Estimate** (Qwen-turbo):
- Per query: ~¥0.006
- 1000 queries/day: ~¥180/month

## Troubleshooting

### Common Issues

1. **Import Error**: `ModuleNotFoundError: No module named 'langchain'`
   ```bash
   pip install -r requirements.txt
   ```

2. **Missing API Key**: `QWEN_API_KEY is required`
   ```bash
   # Add to .env
   QWEN_API_KEY=sk-your-actual-key
   ```

3. **Wrong Provider Name**: `Unsupported LLM provider`
   ```bash
   # Use lowercase: qwen, deepseek, or ollama
   LLM_PROVIDER=qwen
   ```

4. **Ollama Not Running**: Connection refused
   ```bash
   ollama serve
   ollama pull qwen2.5:7b
   ```

## Rollback Plan

If issues arise, you can rollback to the old implementation:

1. Revert git changes:
   ```bash
   git checkout HEAD~1 -- backend/app/services/llm_client.py
   ```

2. Remove LangChain dependencies:
   ```bash
   pip uninstall langchain langchain-openai langchain-community dashscope
   ```

3. Restore old .env configuration

## Next Steps

1. **Monitor**: Watch logs for extraction accuracy
2. **Test**: Try different providers and compare results
3. **Optimize**: Adjust prompts if needed
4. **Cache**: Consider adding Redis cache for common queries
5. **Metrics**: Track extraction success rate and latency

## Documentation

- **Full Guide**: [docs/llm-client-guide.md](./llm-client-guide.md)
- **Search Optimization**: [docs/search-optimization.md](./search-optimization.md)
- **LangChain Docs**: https://python.langchain.com/docs/
- **Qwen API**: https://help.aliyun.com/zh/dashscope/
- **DeepSeek API**: https://platform.deepseek.com/api-docs/

## Support

For issues or questions:
1. Check the comprehensive documentation
2. Review error logs
3. Verify environment configuration
4. Test with different providers
