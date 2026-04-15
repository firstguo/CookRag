# Search API Optimization Documentation

## Overview

The search API has been optimized with three major enhancements:

1. **LLM-based Field Extraction** - Uses large language models to extract structured fields from user queries
2. **Intelligent Filtering** - Applies filters based on extracted fields for more precise results
3. **Minimum Similarity Threshold** - Filters out low-similarity results to improve result quality

## Architecture

### Components

1. **OllamaLLMClient** (`app/services/llm_client.py`)
   - Interfaces with Ollama LLM for intelligent query parsing
   - Extracts: recipe names, ingredients, tags, cooking time
   - Includes retry logic and comprehensive logging

2. **Enhanced MilvusClient** (`app/services/milvus_client.py`)
   - Added minimum similarity threshold support
   - Supports filter expressions for structured queries
   - Logs search operations and filtering decisions

3. **Optimized Search API** (`app/api/search.py`)
   - Integrates LLM extraction with fallback mechanism
   - Two-stage filtering: Milvus expression + post-filtering
   - Maintains backward compatibility

## How It Works

### 1. Query Processing Flow

```
User Query
    ↓
LLM Field Extraction (optional)
    ↓
Extract: recipe_names, ingredients, tags, cook_time, raw_query
    ↓
Build Milvus Filter Expression
    ↓
Generate Embedding (using raw_query)
    ↓
Milvus Vector Search (with filter + min_similarity)
    ↓
Post-Filtering (based on extracted fields)
    ↓
Hybrid Ranking (vector score + like count)
    ↓
Return Results
```

### 2. LLM Field Extraction

The LLM extracts structured information from natural language queries:

**Example Query**: "我想找一个有鸡蛋和土豆的快手菜，20分钟内能做完的"

**Extracted Fields**:
```json
{
  "recipe_names": [],
  "ingredients": ["鸡蛋", "土豆"],
  "tags": ["快手菜"],
  "cook_time_minutes": 20,
  "raw_query": "有鸡蛋和土豆的菜"
}
```

**LLM Prompt Strategy**:
- Low temperature (0.1) for consistent extraction
- Structured JSON output format
- Fallback to original query if extraction fails

### 3. Two-Stage Filtering

#### Stage 1: Milvus Filter Expression
Built from extracted fields and applied during vector search:

```python
# Example filter expression
"(ARRAY_CONTAINS(ingredients, '鸡蛋') or ARRAY_CONTAINS(ingredients, '土豆')) 
and (ARRAY_CONTAINS(tags, '快手菜')) 
and (cook_time_minutes <= 20)"
```

#### Stage 2: Post-Filtering
Applied after Milvus search for more precise matching:
- Recipe name matching (substring match in title)
- Ingredient validation (exact match in ingredients array)
- Tag validation (exact match in tags array)
- Cook time validation (numeric comparison)

### 4. Minimum Similarity Threshold

Filters out results below the similarity threshold:
- **Default**: 0.5 (50% similarity)
- **Range**: 0.0 - 1.0
- **Metric**: COSINE similarity
- Applied during Milvus result parsing

## API Usage

### Request Schema

```python
class SearchRequest(BaseModel):
    query: str                              # Search query (required)
    topK: int = 8                          # Number of results (1-50)
    min_similarity: float = 0.5            # Minimum similarity threshold (0.0-1.0)
    use_llm_extraction: bool = True        # Enable LLM field extraction
    rank: Optional[dict] = None            # Ranking weights {alpha, beta}
```

### Example Requests

#### 1. Basic Search (with defaults)
```json
POST /api/search
{
  "query": "西红柿炒鸡蛋"
}
```

#### 2. Search with Custom Similarity Threshold
```json
POST /api/search
{
  "query": "素食菜谱",
  "min_similarity": 0.7,
  "topK": 10
}
```

#### 3. Disable LLM Extraction
```json
POST /api/search
{
  "query": "土豆",
  "use_llm_extraction": false
}
```

#### 4. Complex Natural Language Query
```json
POST /api/search
{
  "query": "我想做有鸡蛋和西红柿的菜，最好30分钟内能完成",
  "min_similarity": 0.6,
  "topK": 5
}
```

## Configuration

### Environment Variables

```bash
# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=bge-m3          # For vector embeddings
OLLAMA_LLM_MODEL=qwen2.5:7b            # For field extraction
OLLAMA_TIMEOUT_S=120
```

### Recommended LLM Models

- **qwen2.5:7b** - Good balance of speed and accuracy (default)
- **qwen2.5:14b** - Better extraction accuracy, slower
- **llama3.1:8b** - Alternative option
- **mistral:7b** - Lightweight option

## Logging

Comprehensive logging at each stage:

```
INFO  - Search requested for query: ...
INFO  - Using LLM for field extraction
INFO  - LLM extracted fields: {...}
DEBUG - Using search query for embedding: ...
DEBUG - Generating embedding for query: ...
DEBUG - Built Milvus filter expression: ...
DEBUG - Searching Milvus with top_k=..., min_similarity=...
INFO  - Milvus search returned X results (after similarity filter)
INFO  - Found X candidate results from Milvus
INFO  - Applying post-filtering based on extracted fields
INFO  - Filtered by ingredients: X results
INFO  - Returning X results for query: ...
```

## Performance Considerations

### LLM Extraction Overhead
- Adds ~1-3 seconds to search latency
- Can be disabled with `use_llm_extraction: false`
- Includes automatic retry (3 attempts)

### Optimization Tips
1. **Higher min_similarity** → Fewer results, faster post-processing
2. **Disable LLM** → Faster response, less intelligent filtering
3. **Smaller topK** → Faster overall response
4. **Filter expressions** → Reduce candidate set early

### Fallback Mechanism
If LLM extraction fails:
- Automatically falls back to original query
- Logs error and continues search
- No disruption to user experience

## Benefits

1. **Better Understanding**: LLM understands natural language queries
2. **Precise Filtering**: Multi-dimensional filtering (ingredients, tags, time)
3. **Quality Control**: Minimum similarity ensures relevant results
4. **Flexibility**: Can enable/disable features as needed
5. **Robustness**: Fallback mechanisms ensure reliability
6. **Observability**: Comprehensive logging for debugging

## Testing

### Test Cases

1. **Simple Query**: "红烧肉"
2. **Ingredient Query**: "有鸡蛋的菜"
3. **Time Constraint**: "20分钟内能做完的菜"
4. **Complex Query**: "素菜的快手菜，有豆腐，15分钟"
5. **Mixed Language**: "我想找tomato egg的菜谱"

### Validation

```bash
# Test basic search
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "西红柿炒鸡蛋"}'

# Test with LLM extraction disabled
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "土豆", "use_llm_extraction": false}'

# Test with high similarity threshold
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "素食", "min_similarity": 0.8}'
```

## Future Enhancements

1. **Multi-turn Conversation**: Remember context from previous searches
2. **Personalization**: Factor in user preferences
3. **Dietary Restrictions**: Filter by vegetarian, vegan, etc.
4. **Difficulty Level**: Filter by cooking difficulty
5. **Cuisine Type**: Better cuisine classification
6. **Semantic Filters**: More intelligent filter expressions

## Troubleshooting

### LLM Not Responding
- Check if Ollama is running: `ollama list`
- Verify model is pulled: `ollama pull qwen2.5:7b`
- Check logs for timeout errors

### No Results After Filtering
- Lower `min_similarity` threshold
- Check if filters are too restrictive
- Review LLM extraction in logs
- Try with `use_llm_extraction: false`

### Slow Performance
- Use smaller LLM model
- Increase `min_similarity` to reduce candidates
- Reduce `topK` value
- Disable LLM extraction if not needed
