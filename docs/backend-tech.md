# CookRag 后端技术文档

## 1. 文档目标

本文档基于 `docs/requirements.md`，定义 CookRag 后端的技术实现方案、接口契约与落地标准，用于指导开发、联调与验收。

项目目标：
- 提供中文菜谱语义检索能力（Ollama `bge-m3` + Milvus 向量索引）。
- 提供菜谱详情、用户注册登录、点赞能力。
- 通过可重复执行的导入脚本，将 `recipes/**/*.md` 导入菜单主库，并同步检索索引。

## 2. 技术栈与组件

- 运行框架：FastAPI
- 数据库：MongoDB（菜单主数据、用户、点赞）+ Milvus（向量检索索引与元数据）
- Embedding：Ollama（模型 `bge-m3`）
- 后端语言：Python 3.10+
- 依赖：`pymilvus`、`pymongo`、`httpx`、`tenacity`、`python-frontmatter`

组件职责：
- API 层：请求校验、鉴权、响应组装。
- Service 层：Embedding 调用、Mongo 查询、Milvus 向量检索、导入同步编排。
- 存储层：MongoDB（Recipe + User + Like）与 Milvus（向量 + 检索元数据）。

## 3. 后端架构设计

### 3.1 运行时架构

1. 前端调用 `POST /api/search`，传入中文 query。
2. 后端调用 Ollama 生成 query embedding。
3. 后端调用 Milvus `search` 接口，基于向量相似度获取候选 `recipe_id + score`，同时返回存储的 metadata（title_zh, tags 等）。
4. 后端回查 MongoDB 获取完整菜单详情与点赞数，再执行混合排序（`score + like_norm`）并返回结果。
5. 前端调用 `GET /api/recipes/{id}` 获取详情。

### 3.2 导入架构

1. 脚本递归扫描 `recipes/**/*.md`。
2. 解析 Markdown（优先 LLM 结构化，失败时回退规则解析）。
3. 先写入 MongoDB `recipes`（菜单主数据），确保主库幂等。
4. 生成 `content_zh` 聚合文本并调用 embedding。
5. Upsert Milvus `recipes` Collection（向量 + metadata 字段）。
6. 首次导入时检查并创建 Milvus Collection 与向量索引。

## 4. 目录与模块建议

建议后端目录结构保持如下语义：

- `backend/app/main.py`：应用启动、路由注册、依赖初始化
- `backend/app/config.py`：环境变量配置
- `backend/app/models/`：请求/响应与领域模型
- `backend/app/api/`：`search`、`recipes`、`auth` 路由
- `backend/app/services/`：embedding、milvus、ingest、auth、like 服务
- `backend/scripts/ingest.py`：离线导入入口

## 5. 数据模型（MongoDB 主库 + Milvus 向量索引）

### 5.1 MongoDB（菜单与互动主库）

集合设计：

- `recipes`
  - `_id: ObjectId`
  - `recipe_id: string`（唯一，对外主键）
  - `title_zh: string`
  - `content_zh: string`
  - `ingredients: string[]`
  - `tags: string[]`
  - `cook_time_minutes: number | null`
  - `steps: string[]`
  - `like_count: number`（默认 0）
  - `created_at: datetime`
  - `updated_at: datetime`

- `users`
  - `_id: ObjectId`
  - `user_id: string`（UUID，对外返回）
  - `nickname: string`（唯一索引）
  - `password_hash: string`
  - `created_at: datetime`

- `recipe_likes`
  - `_id: ObjectId`
  - `user_id: string`
  - `recipe_id: string`
  - `created_at: datetime`

Mongo 索引建议：

```javascript
db.recipes.createIndex({ recipe_id: 1 }, { unique: true })
db.recipes.createIndex({ tags: 1 })
db.users.createIndex({ nickname: 1 }, { unique: true })
db.users.createIndex({ user_id: 1 }, { unique: true })
db.recipe_likes.createIndex({ user_id: 1, recipe_id: 1 }, { unique: true })
db.recipe_likes.createIndex({ recipe_id: 1 })
```

### 5.2 Milvus（向量检索索引域）

Collection 名称：`recipes`

#### Schema 定义

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `recipe_id` | VARCHAR(64) | 主键，对应 MongoDB 的 `recipe_id` |
| `title_zh` | VARCHAR(256) | 菜谱标题，用于结果展示 |
| `content_zh` | VARCHAR(4096) | 聚合文本内容，用于辅助检索展示 |
| `ingredients` | ARRAY<VARCHAR(128)> | 食材列表，可用于元数据过滤 |
| `tags` | ARRAY<VARCHAR(64)> | 标签列表，可用于元数据过滤 |
| `cook_time_minutes` | INT32 | 烹饪时间（分钟），可用于范围过滤 |
| `embedding` | FLOAT_VECTOR(1024) | bge-m3 生成的向量（维度 1024） |

#### 索引配置

```python
from pymilvus import FieldSchema, CollectionSchema, DataType, Collection

# Field definitions
fields = [
    FieldSchema(name="recipe_id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
    FieldSchema(name="title_zh", dtype=DataType.VARCHAR, max_length=256),
    FieldSchema(name="content_zh", dtype=DataType.VARCHAR, max_length=4096),
    FieldSchema(name="ingredients", dtype=DataType.ARRAY, element_type=DataType.VARCHAR, max_length=128, max_capacity=50),
    FieldSchema(name="tags", dtype=DataType.ARRAY, element_type=DataType.VARCHAR, max_length=64, max_capacity=20),
    FieldSchema(name="cook_time_minutes", dtype=DataType.INT32),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1024),
]

schema = CollectionSchema(fields, description="Recipe vector index with metadata")
collection = Collection(name="recipes", schema=schema)

# 创建向量索引（IVF_FLAT 或 HNSW）
index_params = {
    "metric_type": "COSINE",
    "index_type": "HNSW",
    "params": {"M": 16, "efConstruction": 200}
}
collection.create_index(field_name="embedding", index_params=index_params)
```

#### 元数据过滤支持

Milvus 支持在向量检索时附加标量过滤条件：

```python
# 示例：检索包含特定食材的菜谱
expr = "array_contains(ingredients, '鸡蛋')"
results = collection.search(
    data=[query_embedding],
    anns_field="embedding",
    param={"metric_type": "COSINE", "params": {"ef": 64}},
    limit=top_k,
    expr=expr,
    output_fields=["recipe_id", "title_zh", "tags"]
)
```

说明：
- Milvus 承担向量检索索引，同时存储关键元数据用于过滤和展示。
- 排序所需 `like_count` 以 MongoDB `recipes.like_count` 为准（不在 Milvus 中存储，避免双写一致性问题）。

### 5.3 Milvus 与 MongoDB 数据同步策略

| 操作 | MongoDB | Milvus |
|------|---------|--------|
| 导入菜谱 | 插入/更新 `recipes` 集合 | Upsert `recipes` Collection（向量 + metadata） |
| 更新菜谱内容 | 更新文档 | Upsert 对应记录 |
| 删除菜谱 | 删除文档 | 删除对应记录 |
| 点赞/取消点赞 | 更新 `like_count` | 不操作（避免双写） |

幂等策略：
- 导入脚本以 `recipe_id` 为唯一键，重复导入时执行 Upsert 操作。
- Milvus 使用 `recipe_id` 作为主键，确保同 ID 不会产生重复记录。

点赞计数维护建议：
- 点赞成功（插入 `recipe_likes`）后，MongoDB `recipes.like_count += 1`
- 取消点赞成功（删除 `recipe_likes`）后，MongoDB `recipes.like_count = max(like_count-1, 0)`
- `recipe_likes` 通过唯一键保证幂等。

## 6. API 契约

### 6.1 搜索接口

- `POST /api/search`
- 请求体：
  - `query: string`（必填，中文）
  - `topK: number`（1-50，默认 8）
  - `rank.alpha: number`（0-1，默认 0.8）
  - `rank.beta: number`（>=0，默认 0.2）

响应字段：
- `query`
- `results[]`：
  - `id`
  - `title_zh`
  - `score`
  - `like_count`
  - `final_score`
  - `snippet`（可选）

校验规则：
- 非中文 query 返回 `400`（错误码与提示信息固定）。
- 返回按 `final_score` 降序。

### 6.2 菜谱详情接口

- `GET /api/recipes/{id}`
- 成功返回：`id/title_zh/ingredients/tags/cook_time_minutes/content_zh/steps/like_count/meta`
- 不存在时返回 `404`

### 6.3 用户接口

- `POST /api/auth/register`
  - 入参：`nickname(1-32)`、`password(>=8)`
  - 成功：`{ user: { id, nickname } }`
  - 昵称重复：`409`

- `POST /api/auth/login`
  - 入参：`nickname/password`
  - 成功：`{ token, user }`
  - 密码错误：`401`

### 6.4 点赞接口

- `POST /api/recipes/{id}/like`
- `DELETE /api/recipes/{id}/like`
- 需登录（`Authorization: Bearer <token>`）
- 行为幂等：重复点赞不增加，重复取消不为负
- `liked_by_me` 从 MongoDB `recipe_likes` 查询
- `like_count` 从 MongoDB `recipes.like_count` 返回

## 7. 排序策略（相关度 + 热度）

候选集：
- 先取向量检索候选（推荐 `candidateK = topK * 5`，最小 20）。

归一化：
- `like_norm = log(1 + like_count) / log(1 + max_like_count)`，当分母为 0 时取 0。

最终分数：

```text
final_score = alpha * score + beta * like_norm
```

默认参数建议：
- `alpha = 0.8`
- `beta = 0.2`

设计原则：
- 语义相关度优先，热度只做轻量加权，避免“高赞低相关”排在前列。

## 8. 导入策略与容错

### 8.1 输入范围

- 递归读取 `recipes/**/*.md`
- 忽略非 `.md` 文件

### 8.2 结构化解析策略

优先级：
1. LLM 结构化解析（固定 JSON Schema）
2. frontmatter 增强
3. 规则回退（标题、列表步骤等）

Schema（字段必须存在，可空）：
- `id`
- `title_zh`
- `ingredients`
- `tags`
- `cook_time_minutes`
- `steps`
- `content_zh`

### 8.3 幂等策略

- `MERGE (r:Recipe {id})`，同 ID 重复导入只更新内容与向量。
- 导入可重复执行，不产生同 ID 重复节点。

## 9. 安全与非功能需求

- CORS 仅允许前端白名单域名。
- 密码仅存哈希（推荐 `bcrypt`）。
- 不记录 embedding 原始向量到日志。
- 关键日志：导入进度、embedding 失败、Milvus 查询异常、Mongo 写入异常、鉴权失败。
- 性能目标：`/api/search` 常规场景可交互（目标 <2s，视硬件和 Ollama 负载）。

## 10. 配置项（环境变量）

- Milvus：`MILVUS_HOST`、`MILVUS_PORT`、`MILVUS_COLLECTION_NAME`
- MongoDB：`MONGODB_URI`、`MONGODB_DB_NAME`
- Ollama：`OLLAMA_HOST`、`OLLAMA_EMBEDDING_MODEL`、`OLLAMA_TIMEOUT_S`
- 后端：`APP_NAME`、`PORT`、`CORS_ALLOW_ORIGINS`
- 向量索引：`VECTOR_INDEX_NAME`（默认与 `MILVUS_COLLECTION_NAME` 一致）
- 鉴权（新增）：`JWT_SECRET`、`JWT_EXPIRE_MINUTES`

## 11. 部署与运行

### 11.1 本地启动建议

1. 启动 Milvus（Docker Compose，包含 etcd、minio、standalone）
2. 启动 MongoDB（本机或 Docker）
3. 启动 Ollama（本机服务）
4. 执行导入（先写 Mongo，再同步 Milvus 索引）：
   - `python backend/scripts/ingest.py --recipes-dir recipes`
5. 启动后端：
   - `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

#### Milvus Docker Compose 示例

```yaml
version: '3.5'

services:
  etcd:
    container_name: milvus-etcd
    image: quay.io/coreos/etcd:v3.5.5
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000
      - ETCD_QUOTA_BACKEND_BYTES=4294967296
    volumes:
      - ${DOCKER_VOLUME_DIRECTORY:-.}/volumes/etcd:/etcd
    command: etcd -advertise-client-urls=http://127.0.0.1:2379 -listen-client-urls http://0.0.0.0:2379 --data-dir /etcd

  minio:
    container_name: milvus-minio
    image: minio/minio:RELEASE.2023-03-20T20-16-18Z
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
    volumes:
      - ${DOCKER_VOLUME_DIRECTORY:-.}/volumes/minio:/minio_data
    command: minio server /minio_data
    ports:
      - "9001:9001"

  standalone:
    container_name: milvus-standalone
    image: milvusdb/milvus:v2.3.3
    command: ["milvus", "run", "standalone"]
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
    volumes:
      - ${DOCKER_VOLUME_DIRECTORY:-.}/volumes/milvus:/var/lib/milvus
    ports:
      - "19530:19530"
      - "9091:9091"
    depends_on:
      - etcd
      - minio
```

### 11.2 健康检查建议

- `GET /healthz`：检查进程可用
- `GET /readyz`：检查 Milvus、MongoDB 与 Ollama 连通性

## 12. 验收映射清单

- [ ] `recipes/**/*.md` 至少 3 份可成功导入
- [ ] `/api/search` 支持中文检索，`topK` 生效
- [ ] 返回 `score + like_count + final_score`
- [ ] `/api/recipes/{id}` 成功/404 行为正确
- [ ] 注册/登录/错误码行为正确（409/401）
- [ ] 点赞接口幂等
- [ ] 重复导入不重复创建 Recipe（Milvus 主键去重）
- [ ] 混合排序在可控样本下可观察
