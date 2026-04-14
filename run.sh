#!/bin/bash

# CookRag Unified Run Script
# Provides easy management for all project services

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Function to display help
show_help() {
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}  CookRag - 智能菜谱检索系统${NC}"
    echo -e "${GREEN}================================================${NC}"
    echo ""
    echo -e "${CYAN}用法:${NC}"
    echo -e "  ./run.sh <command>"
    echo ""
    echo -e "${CYAN}可用命令:${NC}"
    echo -e "  ${YELLOW}start${NC}         启动所有服务（前端 + 后端）"
    echo -e "  ${YELLOW}start-backend${NC}  仅启动后端服务"
    echo -e "  ${YELLOW}start-frontend${NC} 仅启动前端服务"
    echo -e "  ${YELLOW}start-infra${NC}    启动基础设施（MongoDB + Milvus + Ollama）"
    echo -e "  ${YELLOW}stop${NC}           停止所有服务"
    echo -e "  ${YELLOW}status${NC}         查看服务状态"
    echo -e "  ${YELLOW}logs${NC}           查看服务日志"
    echo -e "  ${YELLOW}install${NC}        安装所有依赖"
    echo -e "  ${YELLOW}ingest${NC}         导入菜谱数据"
    echo -e "  ${YELLOW}clean${NC}          清理临时文件和虚拟环境"
    echo -e "  ${YELLOW}help${NC}           显示此帮助信息"
    echo ""
    echo -e "${CYAN}示例:${NC}"
    echo -e "  ${YELLOW}./run.sh start${NC}          # 启动所有服务"
    echo -e "  ${YELLOW}./run.sh start-backend${NC}  # 仅启动后端"
    echo -e "  ${YELLOW}./run.sh status${NC}         # 查看服务状态"
    echo -e "  ${YELLOW}./run.sh ingest${NC}         # 导入菜谱数据"
    echo ""
    echo -e "${GREEN}访问地址:${NC}"
    echo -e "  前端应用: ${BLUE}http://localhost:5173${NC}"
    echo -e "  后端 API: ${BLUE}http://localhost:8000${NC}"
    echo -e "  API 文档: ${BLUE}http://localhost:8000/docs${NC}"
    echo ""
}

# Function to check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}检查前置条件...${NC}"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}✗ Python 3 未安装${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Python 3: $(python3 --version)${NC}"
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        echo -e "${RED}✗ Node.js 未安装${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Node.js: $(node --version)${NC}"
    
    # Check Docker (for infrastructure)
    if command -v docker &> /dev/null; then
        echo -e "${GREEN}✓ Docker: $(docker --version)${NC}"
    else
        echo -e "${YELLOW}⚠ Docker 未安装（如需使用 Docker 启动 MongoDB/Milvus）${NC}"
    fi
    
    echo ""
}

# Function to install dependencies
install_dependencies() {
    echo -e "${GREEN}=====================================${NC}"
    echo -e "${GREEN}  安装依赖${NC}"
    echo -e "${GREEN}=====================================${NC}"
    echo ""
    
    # Backend dependencies
    echo -e "${YELLOW}安装后端依赖...${NC}"
    cd "$SCRIPT_DIR/backend"
    
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}创建 Python 虚拟环境...${NC}"
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    pip install -r requirements.txt --quiet
    echo -e "${GREEN}✓ 后端依赖安装完成${NC}"
    
    cd "$SCRIPT_DIR"
    
    # Frontend dependencies
    echo -e "${YELLOW}安装前端依赖...${NC}"
    cd "$SCRIPT_DIR/frontend"
    npm install --silent
    echo -e "${GREEN}✓ 前端依赖安装完成${NC}"
    
    cd "$SCRIPT_DIR"
    echo ""
    echo -e "${GREEN}所有依赖安装完成！${NC}"
}

# Function to start infrastructure (MongoDB, Milvus)
start_infrastructure() {
    echo -e "${GREEN}=====================================${NC}"
    echo -e "${GREEN}  启动基础设施${NC}"
    echo -e "${GREEN}=====================================${NC}"
    echo ""
    
    if [ ! -f "docker-compose.yml" ]; then
        echo -e "${RED}✗ docker-compose.yml 文件不存在${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}启动 MongoDB 和 Milvus...${NC}"
    docker-compose up -d
    
    echo ""
    echo -e "${GREEN}✓ 基础设施启动完成${NC}"
    echo -e "${YELLOW}等待服务就绪...${NC}"
    sleep 5
    
    echo -e "${GREEN}MongoDB:  localhost:27017${NC}"
    echo -e "${GREEN}Milvus:   localhost:19530${NC}"
    echo ""
}

# Function to start backend
start_backend() {
    echo -e "${GREEN}=====================================${NC}"
    echo -e "${GREEN}  启动后端服务${NC}"
    echo -e "${GREEN}=====================================${NC}"
    echo ""
    
    cd "$SCRIPT_DIR/backend"
    
    # Activate virtual environment
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}创建虚拟环境...${NC}"
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    
    # Load .env file
    if [ -f "$SCRIPT_DIR/.env" ]; then
        echo -e "${YELLOW}加载环境变量...${NC}"
        set -a
        source "$SCRIPT_DIR/.env"
        set +a
    elif [ -f "$SCRIPT_DIR/.env.example" ]; then
        echo -e "${YELLOW}从 .env.example 创建 .env 文件...${NC}"
        cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
        set -a
        source "$SCRIPT_DIR/.env"
        set +a
        echo -e "${YELLOW}请检查并更新 .env 文件中的配置${NC}"
    fi
    
    echo -e "${GREEN}启动 FastAPI 服务器...${NC}"
    echo -e "${GREEN}API 服务: http://localhost:8000${NC}"
    echo -e "${GREEN}API 文档: http://localhost:8000/docs${NC}"
    echo -e "${YELLOW}按 Ctrl+C 停止服务${NC}"
    echo ""
    
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
}

# Function to start frontend
start_frontend() {
    echo -e "${GREEN}=====================================${NC}"
    echo -e "${GREEN}  启动前端服务${NC}"
    echo -e "${GREEN}=====================================${NC}"
    echo ""
    
    cd "$SCRIPT_DIR/frontend"
    
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}安装前端依赖...${NC}"
        npm install
    fi
    
    echo -e "${GREEN}启动 Vite 开发服务器...${NC}"
    echo -e "${GREEN}前端应用: http://localhost:5173${NC}"
    echo -e "${YELLOW}按 Ctrl+C 停止服务${NC}"
    echo ""
    
    npm run dev
}

# Function to start all services
start_all() {
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}  启动 CookRag 所有服务${NC}"
    echo -e "${GREEN}================================================${NC}"
    echo ""
    
    # Check prerequisites
    check_prerequisites
    
    # Install dependencies if needed
    if [ ! -d "$SCRIPT_DIR/backend/venv" ] || [ ! -d "$SCRIPT_DIR/frontend/node_modules" ]; then
        install_dependencies
    fi
    
    # Start infrastructure
    echo -e "${YELLOW}是否启动基础设施 (MongoDB + Milvus)? (y/n)${NC}"
    read -r start_infra
    if [[ "$start_infra" =~ ^[Yy]$ ]]; then
        start_infrastructure
    fi
    
    echo ""
    echo -e "${BLUE}启动后端服务（后台运行）...${NC}"
    "$SCRIPT_DIR/start-backend.sh" &
    BACKEND_PID=$!
    
    sleep 3
    
    echo -e "${BLUE}启动前端服务（后台运行）...${NC}"
    "$SCRIPT_DIR/start-frontend.sh" &
    FRONTEND_PID=$!
    
    echo ""
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}  所有服务已启动${NC}"
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}前端应用: http://localhost:5173${NC}"
    echo -e "${GREEN}后端 API: http://localhost:8000${NC}"
    echo -e "${GREEN}API 文档: http://localhost:8000/docs${NC}"
    echo ""
    echo -e "${YELLOW}后端 PID:  $BACKEND_PID${NC}"
    echo -e "${YELLOW}前端 PID: $FRONTEND_PID${NC}"
    echo ""
    echo -e "${YELLOW}按 Ctrl+C 停止所有服务${NC}"
    echo ""
    
    # Cleanup function
    cleanup() {
        echo ""
        echo -e "${YELLOW}正在停止服务...${NC}"
        kill $BACKEND_PID 2>/dev/null
        kill $FRONTEND_PID 2>/dev/null
        wait $BACKEND_PID 2>/dev/null
        wait $FRONTEND_PID 2>/dev/null
        echo -e "${GREEN}所有服务已停止${NC}"
        exit 0
    }
    
    trap cleanup SIGINT SIGTERM
    
    wait $BACKEND_PID
    wait $FRONTEND_PID
}

# Function to stop all services
stop_all() {
    echo -e "${YELLOW}正在停止所有服务...${NC}"
    
    # Stop Docker services
    if [ -f "docker-compose.yml" ]; then
        docker-compose down
    fi
    
    # Kill any running uvicorn or vite processes
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    
    echo -e "${GREEN}✓ 所有服务已停止${NC}"
}

# Function to show status
show_status() {
    echo -e "${GREEN}=====================================${NC}"
    echo -e "${GREEN}  服务状态${NC}"
    echo -e "${GREEN}=====================================${NC}"
    echo ""
    
    # Check backend
    if curl -s http://localhost:8000/healthz > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 后端服务: 运行中 (http://localhost:8000)${NC}"
    else
        echo -e "${RED}✗ 后端服务: 未运行${NC}"
    fi
    
    # Check frontend
    if curl -s http://localhost:5173 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 前端服务: 运行中 (http://localhost:5173)${NC}"
    else
        echo -e "${RED}✗ 前端服务: 未运行${NC}"
    fi
    
    # Check MongoDB
    if command -v mongosh > /dev/null 2>&1; then
        if mongosh --eval "db.runCommand('ping')" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ MongoDB: 运行中${NC}"
        else
            echo -e "${RED}✗ MongoDB: 未运行${NC}"
        fi
    else
        if docker ps --format '{{.Names}}' | grep -q mongo; then
            echo -e "${GREEN}✓ MongoDB (Docker): 运行中${NC}"
        else
            echo -e "${RED}✗ MongoDB: 未运行${NC}"
        fi
    fi
    
    # Check Milvus
    if docker ps --format '{{.Names}}' | grep -q milvus; then
        echo -e "${GREEN}✓ Milvus (Docker): 运行中${NC}"
    else
        echo -e "${RED}✗ Milvus: 未运行${NC}"
    fi
    
    # Check Ollama
    if curl -s http://localhost:11434 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Ollama: 运行中${NC}"
    else
        echo -e "${RED}✗ Ollama: 未运行${NC}"
    fi
    
    echo ""
}

# Function to ingest recipe data
ingest_data() {
    echo -e "${GREEN}=====================================${NC}"
    echo -e "${GREEN}  导入菜谱数据${NC}"
    echo -e "${GREEN}=====================================${NC}"
    echo ""
    
    cd "$SCRIPT_DIR/backend"
    
    if [ ! -d "venv" ]; then
        echo -e "${RED}✗ 虚拟环境不存在，请先运行: ./run.sh install${NC}"
        exit 1
    fi
    
    source venv/bin/activate
    
    if [ -f "$SCRIPT_DIR/.env" ]; then
        set -a
        source "$SCRIPT_DIR/.env"
        set +a
    fi
    
    echo -e "${YELLOW}开始导入菜谱数据...${NC}"
    python scripts/ingest.py --recipes-dir "$SCRIPT_DIR/recipes"
    
    echo ""
    echo -e "${GREEN}✓ 数据导入完成${NC}"
}

# Function to clean up
clean_up() {
    echo -e "${YELLOW}清理临时文件...${NC}"
    
    # Clean Python cache
    find "$SCRIPT_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$SCRIPT_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
    
    # Clean backend venv
    if [ -d "$SCRIPT_DIR/backend/venv" ]; then
        echo -e "${YELLOW}删除 Python 虚拟环境...${NC}"
        rm -rf "$SCRIPT_DIR/backend/venv"
    fi
    
    # Clean frontend node_modules
    if [ -d "$SCRIPT_DIR/frontend/node_modules" ]; then
        echo -e "${YELLOW}删除 node_modules...${NC}"
        rm -rf "$SCRIPT_DIR/frontend/node_modules"
    fi
    
    echo -e "${GREEN}✓ 清理完成${NC}"
}

# Main command handler
case "${1:-help}" in
    start)
        start_all
        ;;
    start-backend)
        check_prerequisites
        start_backend
        ;;
    start-frontend)
        check_prerequisites
        start_frontend
        ;;
    start-infra)
        start_infrastructure
        ;;
    stop)
        stop_all
        ;;
    status)
        show_status
        ;;
    logs)
        echo -e "${YELLOW}查看后端日志:${NC}"
        tail -f "$SCRIPT_DIR/backend/logs/*.log" 2>/dev/null || echo "日志文件不存在"
        ;;
    install)
        install_dependencies
        ;;
    ingest)
        ingest_data
        ;;
    clean)
        clean_up
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}未知命令: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
