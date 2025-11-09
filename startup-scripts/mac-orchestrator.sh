#!/bin/bash
# Mac Studio Orchestrator Script
# Remotely manage HPC lab deployment from your Mac

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration
DGX_SPARK_HOST="dgx-spark.lab"
HPC_1_HOST="hpc-1.lab"
HPC_2_HOST="hpc-2.lab" 
HPC_3_HOST="hpc-3.lab"
SSH_KEY="$HOME/.ssh/id_rsa"  # Adjust as needed

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${PURPLE}🍎 Mac Studio AI Lab Orchestrator${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Function to check system connectivity
check_system() {
    local host=$1
    local name=$2
    
    echo -n "🔍 Checking $name ($host)... "
    if ping -c 1 -W 2000 "$host" > /dev/null 2>&1; then
        if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$host" "echo 'ok'" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Online${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠️ Ping OK, SSH failed${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ Offline${NC}"
        return 1
    fi
}

# Function to deploy project files to a system
deploy_files() {
    local host=$1
    local name=$2
    
    echo "📤 Deploying project files to $name..."
    
    # Create remote directory
    ssh "$host" "sudo mkdir -p /data && sudo chown $USER:$USER /data"
    
    # Sync project files
    rsync -avz --progress \
        --exclude='.git' \
        --exclude='node_modules' \
        --exclude='*.log' \
        "$PROJECT_DIR/" "$host:/data/qwen-ai-workbench-project/"
    
    echo -e "${GREEN}✅ Files deployed to $name${NC}"
}

# Function to start service on a system
start_system() {
    local host=$1
    local name=$2
    local script_name=$3
    
    echo "🚀 Starting $name service..."
    
    # Copy startup script and make executable
    scp "$SCRIPT_DIR/$script_name" "$host:/tmp/"
    ssh "$host" "chmod +x /tmp/$script_name"
    
    # Run startup script
    ssh "$host" "cd /data/qwen-ai-workbench-project && /tmp/$script_name"
    
    echo -e "${GREEN}✅ $name service started${NC}"
}

# Function to check service status
check_status() {
    local host=$1
    local port=$2
    local name=$3
    
    echo -n "🔍 Checking $name service... "
    if curl -sf "http://$host:$port/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Running${NC}"
    else
        echo -e "${RED}❌ Not responding${NC}"
    fi
}

# Function to show system resources
show_resources() {
    local host=$1
    local name=$2
    
    echo "📊 $name Resources:"
    ssh "$host" "
        echo '  CPU: '$(nproc)' cores, Load: '$(uptime | awk -F'load average:' '{print \$2}')
        echo '  Memory: '$(free -h | awk '/^Mem:/ {print \$3 \"/\" \$2}')
        if command -v nvidia-smi >/dev/null 2>&1; then
            echo '  GPUs:'
            nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader | while read line; do
                echo '    '\$line
            done
        fi
    " 2>/dev/null || echo -e "${RED}  ❌ Resource query failed${NC}"
}

# Function to display unified dashboard
show_dashboard() {
    echo ""
    echo -e "${BLUE}🎮 AI Lab Dashboard${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Check all systems
    check_system "$DGX_SPARK_HOST" "DGX Spark"
    check_system "$HPC_1_HOST" "HPC-1"
    check_system "$HPC_2_HOST" "HPC-2"  
    check_system "$HPC_3_HOST" "HPC-3"
    
    echo ""
    echo -e "${BLUE}🌐 Service Status${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    check_status "$DGX_SPARK_HOST" "8000" "DGX Spark"
    check_status "$HPC_1_HOST" "8001" "HPC-1"
    check_status "$HPC_2_HOST" "8002" "HPC-2"
    check_status "$HPC_3_HOST" "8003" "HPC-3"
    
    echo ""
    echo -e "${BLUE}📊 Resource Utilization${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    show_resources "$HPC_1_HOST" "HPC-1"
    echo ""
    show_resources "$HPC_2_HOST" "HPC-2"
    echo ""
    show_resources "$HPC_3_HOST" "HPC-3"
    
    echo ""
    echo -e "${BLUE}🔗 Access URLs${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🚀 HPC-1 (Primary):   http://$HPC_1_HOST:8001 | UI: http://$HPC_1_HOST:3001"
    echo "⚡ HPC-2 (Multi-GPU):  http://$HPC_2_HOST:8002 | UI: http://$HPC_2_HOST:3002"
    echo "🔧 HPC-3 (Dev):       http://$HPC_3_HOST:8003 | UI: http://$HPC_3_HOST:3003"
    echo "🖥️ HPC-3 Code Server: http://$HPC_3_HOST:8080 (password: hpc3-dev-2024)"
}

# Function to deploy to all systems
deploy_all() {
    echo -e "${YELLOW}🚀 Deploying to all HPC systems...${NC}"
    
    # Check connectivity first
    systems_online=0
    if check_system "$HPC_1_HOST" "HPC-1"; then ((systems_online++)); fi
    if check_system "$HPC_2_HOST" "HPC-2"; then ((systems_online++)); fi
    if check_system "$HPC_3_HOST" "HPC-3"; then ((systems_online++)); fi
    
    if [ $systems_online -eq 0 ]; then
        echo -e "${RED}❌ No systems online. Check network connectivity.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ $systems_online/3 systems online. Proceeding with deployment...${NC}"
    echo ""
    
    # Deploy files to online systems
    if ping -c 1 -W 2000 "$HPC_1_HOST" > /dev/null 2>&1; then
        deploy_files "$HPC_1_HOST" "HPC-1"
        start_system "$HPC_1_HOST" "HPC-1" "start-hpc-1.sh"
        echo ""
    fi
    
    if ping -c 1 -W 2000 "$HPC_2_HOST" > /dev/null 2>&1; then
        deploy_files "$HPC_2_HOST" "HPC-2"
        start_system "$HPC_2_HOST" "HPC-2" "start-hpc-2.sh"
        echo ""
    fi
    
    if ping -c 1 -W 2000 "$HPC_3_HOST" > /dev/null 2>&1; then
        deploy_files "$HPC_3_HOST" "HPC-3"
        start_system "$HPC_3_HOST" "HPC-3" "start-hpc-3.sh"
        echo ""
    fi
    
    echo -e "${GREEN}🎉 Deployment complete! Waiting for services to start...${NC}"
    sleep 30
    show_dashboard
}

# Function to stop all services
stop_all() {
    echo -e "${YELLOW}🛑 Stopping all services...${NC}"
    
    for host in "$HPC_1_HOST" "$HPC_2_HOST" "$HPC_3_HOST"; do
        if ping -c 1 -W 2000 "$host" > /dev/null 2>&1; then
            echo "🛑 Stopping services on $host..."
            ssh "$host" "cd /data/qwen-ai-workbench-project && docker-compose down" 2>/dev/null || true
            ssh "$host" "pkill -f 'python.*monitor' || true" 2>/dev/null || true
            ssh "$host" "pkill -f 'code-server' || true" 2>/dev/null || true
        fi
    done
    
    echo -e "${GREEN}✅ All services stopped${NC}"
}

# Function to show help
show_help() {
    echo "Mac Studio AI Lab Orchestrator"
    echo ""
    echo "Commands:"
    echo "  dashboard     Show unified lab dashboard"
    echo "  deploy        Deploy and start all services"
    echo "  stop          Stop all services"
    echo "  deploy-hpc1   Deploy only to HPC-1"
    echo "  deploy-hpc2   Deploy only to HPC-2"
    echo "  deploy-hpc3   Deploy only to HPC-3"
    echo "  status        Check service status"
    echo "  resources     Show resource utilization"
    echo "  logs <system> Show logs from system (hpc1/hpc2/hpc3)"
    echo "  help          Show this help"
    echo ""
    echo "Examples:"
    echo "  ./mac-orchestrator.sh dashboard"
    echo "  ./mac-orchestrator.sh deploy"
    echo "  ./mac-orchestrator.sh logs hpc1"
}

# Main command handling
case "${1:-dashboard}" in
    "dashboard")
        show_dashboard
        ;;
    "deploy")
        deploy_all
        ;;
    "stop")
        stop_all
        ;;
    "deploy-hpc1")
        if check_system "$HPC_1_HOST" "HPC-1"; then
            deploy_files "$HPC_1_HOST" "HPC-1"
            start_system "$HPC_1_HOST" "HPC-1" "start-hpc-1.sh"
        fi
        ;;
    "deploy-hpc2")
        if check_system "$HPC_2_HOST" "HPC-2"; then
            deploy_files "$HPC_2_HOST" "HPC-2"
            start_system "$HPC_2_HOST" "HPC-2" "start-hpc-2.sh"
        fi
        ;;
    "deploy-hpc3")
        if check_system "$HPC_3_HOST" "HPC-3"; then
            deploy_files "$HPC_3_HOST" "HPC-3"
            start_system "$HPC_3_HOST" "HPC-3" "start-hpc-3.sh"
        fi
        ;;
    "status")
        check_status "$HPC_1_HOST" "8001" "HPC-1"
        check_status "$HPC_2_HOST" "8002" "HPC-2"
        check_status "$HPC_3_HOST" "8003" "HPC-3"
        ;;
    "resources")
        show_resources "$HPC_1_HOST" "HPC-1"
        echo ""
        show_resources "$HPC_2_HOST" "HPC-2"
        echo ""
        show_resources "$HPC_3_HOST" "HPC-3"
        ;;
    "logs")
        case "$2" in
            "hpc1")
                ssh "$HPC_1_HOST" "tail -f /data/logs/hpc-1-stats.json"
                ;;
            "hpc2") 
                ssh "$HPC_2_HOST" "tail -f /data/logs/hpc-2-stats.json"
                ;;
            "hpc3")
                ssh "$HPC_3_HOST" "tail -f /data/logs/hpc-3-stats.json"
                ;;
            *)
                echo "Specify system: logs hpc1|hpc2|hpc3"
                ;;
        esac
        ;;
    "help"|"--help"|"-h")
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        show_help
        ;;
esac