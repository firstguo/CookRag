# CookRag

中文菜谱 + 语义检索（Ollama `bge-m3` + Neo4j 向量索引）。

## 环境依赖

1. MongoDB + Neo4j：使用 Docker Compose
2. Ollama：本机已启动（默认 `http://localhost:11434`），并可用 embedding 模型 `bge-m3`
3. Python 依赖（FastAPI 后端）
4. 前端（React + Vite）

## 启动步骤（本地）

### 1) 启动 MongoDB + Neo4j

```bash
docker compose up -d
```

### 2) 配置环境变量

复制 `./.env.example` 到 `./.env`（或在你的 shell 中导出同名变量）。示例中 MongoDB 使用 `27017`，Neo4j 使用 `7687`，Ollama 使用本机 `11434`。

### 3) 启动后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --app-dir . --host 0.0.0.0 --port 8000 --reload
```

### 4) 导入菜谱（Mongo 主库 + Neo4j 索引，首次必做）

确保目录 `recipes/` 内有 `.md` 菜谱文件，然后运行：

```bash
python scripts/ingest.py --recipes-dir recipes
```

导入会先写入 MongoDB，再同步 Neo4j 检索索引。导入完成后再启动/打开前端页面即可。

### 5) 启动前端

```bash
cd frontend
npm install
npm run dev
```

打开浏览器访问 `http://localhost:5173`。

## 验收（Acceptance）

1. 导入后 MongoDB 的 `recipes` 集合有数据，Neo4j 中存在 `:RecipeIndex` 节点。
2. `POST /api/search` 能返回 `topK` 结构正确的结果。
3. 输入英文/日文 query 时，能返回语义相关的中文菜谱候选。
4. 点击结果进入 `/recipes/{id}`，能展示标题、食材、步骤与正文内容。
