# CookRag 服务启动脚本

本项目包含三个启动脚本，用于简化前后端服务的启动流程。

## 启动脚本说明

### 1. start-backend.sh - 后端服务启动脚本

启动 FastAPI 后端服务器（端口 8000）。

**功能：**
- 自动检查 Python 3 和 pip 安装
- 自动创建和激活虚拟环境（venv）
- 自动安装 Python 依赖
- 自动加载 .env 配置文件
- 启动带热重载的开发服务器

**使用方法：**
```bash
./start-backend.sh
```

**访问地址：**
- API 服务：http://localhost:8000
- API 文档：http://localhost:8000/docs

---

### 2. start-frontend.sh - 前端服务启动脚本

启动 Vite 前端开发服务器（端口 5173）。

**功能：**
- 自动检查 Node.js 和 npm 安装
- 自动安装前端依赖
- 启动带热重载的开发服务器

**使用方法：**
```bash
./start-frontend.sh
```

**访问地址：**
- 前端应用：http://localhost:5173

---

### 3. start-all.sh - 全部服务启动脚本

同时启动后端和前端服务。

**功能：**
- 在后台同时启动后端和前端服务
- 自动管理进程生命周期
- 提供统一的停止机制（Ctrl+C）

**使用方法：**
```bash
./start-all.sh
```

**访问地址：**
- 前端应用：http://localhost:5173
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

**停止服务：**
按 `Ctrl+C` 即可同时停止所有服务。

---

## 前置要求

### 后端要求
- Python 3.10+
- pip (Python 包管理器)
- MongoDB 服务
- Milvus 服务
- Ollama 服务（用于 embedding）

### 前端要求
- Node.js 16+
- npm (Node 包管理器)

## 配置文件

首次运行后端脚本时，如果 `.env` 文件不存在，会自动从 `.env.example` 创建。

请确保编辑 `.env` 文件，配置正确的：
- MongoDB 连接信息
- Milvus 连接信息
- Ollama 服务地址
- JWT 密钥

## 故障排除

### 后端启动失败
1. 检查 MongoDB 是否运行
2. 检查 Milvus 是否运行
3. 检查 Ollama 是否运行并加载了 bge-m3 模型
4. 查看终端错误信息

### 前端启动失败
1. 确认 Node.js 版本 >= 16
2. 删除 `node_modules` 和 `package-lock.json` 后重新运行
3. 检查端口 5173 是否被占用

### 端口被占用
- 后端默认端口：8000（可在 `.env` 中修改 PORT）
- 前端默认端口：5173（可在 `frontend/vite.config.ts` 中修改）
