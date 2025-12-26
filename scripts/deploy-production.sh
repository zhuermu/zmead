#!/bin/bash
# AAE Production Deployment Script
# 部署到当前服务器

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "AAE Production Deployment"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 检查必要的环境变量
check_env() {
    local missing=0
    
    if [ ! -f "$PROJECT_ROOT/backend/.env.production" ]; then
        echo -e "${RED}Missing: backend/.env.production${NC}"
        missing=1
    fi
    
    if [ ! -f "$PROJECT_ROOT/ai-orchestrator/.env.production" ]; then
        echo -e "${RED}Missing: ai-orchestrator/.env.production${NC}"
        missing=1
    fi
    
    if [ ! -f "$PROJECT_ROOT/frontend/.env.production" ]; then
        echo -e "${RED}Missing: frontend/.env.production${NC}"
        missing=1
    fi
    
    if [ $missing -eq 1 ]; then
        echo -e "${RED}Please create the missing .env.production files${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ All environment files found${NC}"
}

# 复制生产环境配置
setup_env() {
    echo ""
    echo "Setting up production environment..."
    
    cp "$PROJECT_ROOT/backend/.env.production" "$PROJECT_ROOT/backend/.env"
    cp "$PROJECT_ROOT/ai-orchestrator/.env.production" "$PROJECT_ROOT/ai-orchestrator/.env"
    cp "$PROJECT_ROOT/frontend/.env.production" "$PROJECT_ROOT/frontend/.env.local"
    
    echo -e "${GREEN}✓ Environment files copied${NC}"
}

# 启动 Redis (本地)
start_redis() {
    echo ""
    echo "Starting Redis..."
    
    if command -v redis-server &> /dev/null; then
        if ! pgrep -x "redis-server" > /dev/null; then
            redis-server --daemonize yes
            echo -e "${GREEN}✓ Redis started${NC}"
        else
            echo -e "${YELLOW}Redis already running${NC}"
        fi
    else
        echo -e "${YELLOW}Redis not installed, using docker...${NC}"
        docker run -d --name aae-redis -p 6379:6379 redis:7-alpine || true
    fi
}

# 测试数据库连接
test_db() {
    echo ""
    echo "Testing database connection..."
    
    source "$PROJECT_ROOT/backend/.env"
    
    if mysql -h "$MYSQL_HOST" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT 1" &> /dev/null; then
        echo -e "${GREEN}✓ Database connection successful${NC}"
    else
        echo -e "${RED}✗ Database connection failed${NC}"
        echo "Please check your database credentials in backend/.env"
        exit 1
    fi
}

# 运行数据库迁移
run_migrations() {
    echo ""
    echo "Running database migrations..."
    
    cd "$PROJECT_ROOT/backend"
    
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    alembic upgrade head
    
    echo -e "${GREEN}✓ Migrations completed${NC}"
}

# 启动后端服务
start_backend() {
    echo ""
    echo "Starting backend service..."
    
    cd "$PROJECT_ROOT/backend"
    
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    # 停止已有进程
    pkill -f "uvicorn app.main:app.*8000" || true
    sleep 2
    
    # 启动服务 (生产模式)
    nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 > /tmp/backend.log 2>&1 &
    
    sleep 3
    
    if curl -s http://localhost:8000/health > /dev/null; then
        echo -e "${GREEN}✓ Backend started on port 8000${NC}"
    else
        echo -e "${RED}✗ Backend failed to start${NC}"
        tail -20 /tmp/backend.log
        exit 1
    fi
}

# 启动 AI Orchestrator
start_ai_orchestrator() {
    echo ""
    echo "Starting AI Orchestrator..."
    
    cd "$PROJECT_ROOT/ai-orchestrator"
    
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    # 停止已有进程
    pkill -f "uvicorn app.main:app.*8001" || true
    sleep 2
    
    # 启动服务
    nohup uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 2 > /tmp/ai-orchestrator.log 2>&1 &
    
    sleep 3
    
    if curl -s http://localhost:8001/health > /dev/null; then
        echo -e "${GREEN}✓ AI Orchestrator started on port 8001${NC}"
    else
        echo -e "${RED}✗ AI Orchestrator failed to start${NC}"
        tail -20 /tmp/ai-orchestrator.log
        exit 1
    fi
}

# 构建并启动前端
start_frontend() {
    echo ""
    echo "Building and starting frontend..."
    
    cd "$PROJECT_ROOT/frontend"
    
    # 安装依赖
    npm install --production=false
    
    # 构建
    npm run build
    
    # 停止已有进程
    pkill -f "next start" || true
    pkill -f "node.*\.next" || true
    sleep 2
    
    # 启动服务
    nohup npm start > /tmp/frontend.log 2>&1 &
    
    sleep 5
    
    if curl -s http://localhost:3000 > /dev/null; then
        echo -e "${GREEN}✓ Frontend started on port 3000${NC}"
    else
        echo -e "${RED}✗ Frontend failed to start${NC}"
        tail -20 /tmp/frontend.log
        exit 1
    fi
}

# 显示状态
show_status() {
    echo ""
    echo "=========================================="
    echo "Deployment Complete!"
    echo "=========================================="
    echo ""
    echo "Services:"
    echo "  - Backend:        http://localhost:8000"
    echo "  - AI Orchestrator: http://localhost:8001"
    echo "  - Frontend:       http://localhost:3000"
    echo ""
    echo "External Access:"
    echo "  - Domain:         https://aiad.zmead.com"
    echo "  - CloudFront:     https://d3nynzibdod5e8.cloudfront.net"
    echo ""
    echo "Logs:"
    echo "  - Backend:        /tmp/backend.log"
    echo "  - AI Orchestrator: /tmp/ai-orchestrator.log"
    echo "  - Frontend:       /tmp/frontend.log"
    echo ""
    echo -e "${YELLOW}Note: Make sure ALB is configured to forward traffic to this server${NC}"
}

# 主流程
main() {
    check_env
    setup_env
    start_redis
    test_db
    run_migrations
    start_backend
    start_ai_orchestrator
    start_frontend
    show_status
}

# 解析参数
case "${1:-}" in
    --env-only)
        check_env
        setup_env
        ;;
    --backend-only)
        setup_env
        start_backend
        ;;
    --frontend-only)
        setup_env
        start_frontend
        ;;
    --status)
        echo "Backend:        $(curl -s http://localhost:8000/health || echo 'Not running')"
        echo "AI Orchestrator: $(curl -s http://localhost:8001/health || echo 'Not running')"
        echo "Frontend:       $(curl -s -o /dev/null -w '%{http_code}' http://localhost:3000 || echo 'Not running')"
        ;;
    *)
        main
        ;;
esac
