#!/bin/bash
# DGX Spark Setup Commands
# Run these commands on your DGX Spark to prepare for AI Workbench integration

set -e

echo "🚀 DGX Spark AI Workbench Integration Setup"
echo "=============================================="

# Check if running on DGX system
if [ ! -f /etc/dgx-release ] && [ ! -f /etc/nv-tegra-release ]; then
    echo "⚠️  Warning: This script is designed for DGX systems"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install essential packages
echo "🛠️ Installing essential packages..."
sudo apt install -y \
    curl wget git \
    htop nvtop \
    build-essential \
    python3-pip \
    nodejs npm \
    redis-server \
    nginx

# Setup Docker with NVIDIA runtime (if not already configured)
echo "🐳 Configuring Docker with NVIDIA runtime..."
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
fi

# Configure NVIDIA Container Toolkit
if ! docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi &> /dev/null; then
    echo "Configuring NVIDIA Container Runtime..."
    distribution=$(. /etc/os-release;echo $ID$VERSION_ID) \
        && curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add - \
        && curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
    
    sudo apt update
    sudo apt install -y nvidia-docker2
    sudo systemctl restart docker
fi

# Setup AI Workbench CLI on DGX Spark
echo "🧠 Installing AI Workbench CLI..."
mkdir -p $HOME/.nvwb/bin
curl -L https://workbench.download.nvidia.com/stable/workbench-cli/$(curl -L -s https://workbench.download.nvidia.com/stable/workbench-cli/LATEST)/nvwb-cli-$(uname)-$(uname -m) --output $HOME/.nvwb/bin/nvwb-cli
chmod +x $HOME/.nvwb/bin/nvwb-cli

# Add to PATH
echo 'export PATH="$HOME/.nvwb/bin:$PATH"' >> $HOME/.bashrc
export PATH="$HOME/.nvwb/bin:$PATH"

# Install AI Workbench
echo "Installing AI Workbench on DGX Spark..."
sudo -E $HOME/.nvwb/bin/nvwb-cli install

# Create workspace directories
echo "📁 Creating workspace directories..."
sudo mkdir -p /workspace/{models,data,logs,cache}
sudo chown -R $USER:$USER /workspace
mkdir -p $HOME/ai-workbench-projects

# Setup model cache
echo "🗂️ Configuring model cache..."
export HF_HOME=/workspace/models
export TRANSFORMERS_CACHE=/workspace/models
echo 'export HF_HOME=/workspace/models' >> $HOME/.bashrc
echo 'export TRANSFORMERS_CACHE=/workspace/models' >> $HOME/.bashrc

# Configure Git (if not already done)
echo "📝 Configuring Git..."
if [ -z "$(git config --global user.name)" ]; then
    read -p "Enter your Git username: " git_username
    git config --global user.name "$git_username"
fi

if [ -z "$(git config --global user.email)" ]; then
    read -p "Enter your Git email: " git_email
    git config --global user.email "$git_email"
fi

# Setup SSH for HPC lab connectivity
echo "🔑 Setting up SSH for HPC lab..."
if [ ! -f $HOME/.ssh/id_rsa ]; then
    ssh-keygen -t rsa -b 4096 -f $HOME/.ssh/id_rsa -N ""
    echo "📋 Copy this public key to your HPC systems:"
    cat $HOME/.ssh/id_rsa.pub
    echo ""
    read -p "Press Enter after copying the key to HPC systems..."
fi

# Setup SSH config for HPC systems
cat > $HOME/.ssh/config << EOF
# HPC Lab Configuration
Host hpc-1.lab
    HostName hpc-1.lab
    User $USER
    IdentityFile ~/.ssh/id_rsa
    StrictHostKeyChecking no

Host hpc-2.lab
    HostName hpc-2.lab
    User $USER
    IdentityFile ~/.ssh/id_rsa
    StrictHostKeyChecking no

Host hpc-3.lab
    HostName hpc-3.lab
    User $USER
    IdentityFile ~/.ssh/id_rsa
    StrictHostKeyChecking no
EOF

chmod 600 $HOME/.ssh/config

# Test HPC connectivity
echo "🌐 Testing HPC lab connectivity..."
for host in hpc-1.lab hpc-2.lab hpc-3.lab; do
    echo -n "Testing $host... "
    if ssh -o ConnectTimeout=5 $host "echo 'ok'" 2>/dev/null; then
        echo "✅ Connected"
    else
        echo "❌ Failed"
    fi
done

# Setup NVIDIA monitoring
echo "📊 Setting up NVIDIA monitoring..."
cat > /tmp/dgx-monitor.py << 'EOF'
#!/usr/bin/env python3
import time
import subprocess
import json
import psutil
from datetime import datetime

def get_gpu_stats():
    try:
        result = subprocess.run([
            'nvidia-smi', 
            '--query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw',
            '--format=csv,noheader,nounits'
        ], capture_output=True, text=True)
        
        gpus = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                parts = [p.strip() for p in line.split(',')]
                gpus.append({
                    'index': int(parts[0]),
                    'name': parts[1],
                    'utilization': int(parts[2]),
                    'memory_used': int(parts[3]),
                    'memory_total': int(parts[4]),
                    'temperature': int(parts[5]),
                    'power': float(parts[6])
                })
        return gpus
    except:
        return []

def log_system_stats():
    stats = {
        'timestamp': datetime.now().isoformat(),
        'hostname': subprocess.run(['hostname'], capture_output=True, text=True).stdout.strip(),
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory': {
            'total': psutil.virtual_memory().total,
            'available': psutil.virtual_memory().available,
            'percent': psutil.virtual_memory().percent
        },
        'disk': {
            'total': psutil.disk_usage('/workspace').total,
            'free': psutil.disk_usage('/workspace').free,
            'percent': psutil.disk_usage('/workspace').percent
        },
        'gpus': get_gpu_stats()
    }
    
    with open('/workspace/logs/dgx-stats.json', 'a') as f:
        f.write(json.dumps(stats) + '\n')
    
    # Keep only last 1000 entries
    try:
        with open('/workspace/logs/dgx-stats.json', 'r') as f:
            lines = f.readlines()
        if len(lines) > 1000:
            with open('/workspace/logs/dgx-stats.json', 'w') as f:
                f.writelines(lines[-900:])
    except:
        pass

if __name__ == '__main__':
    while True:
        log_system_stats()
        time.sleep(60)  # Log every minute
EOF

chmod +x /tmp/dgx-monitor.py
cp /tmp/dgx-monitor.py /usr/local/bin/dgx-monitor

# Create systemd service for monitoring
sudo tee /etc/systemd/system/dgx-monitor.service > /dev/null << EOF
[Unit]
Description=DGX Spark Monitoring Service
After=network.target

[Service]
Type=simple
User=$USER
ExecStart=/usr/bin/python3 /usr/local/bin/dgx-monitor
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable dgx-monitor
sudo systemctl start dgx-monitor

# Setup Nginx reverse proxy for AI Workbench
echo "🌐 Configuring Nginx reverse proxy..."
sudo tee /etc/nginx/sites-available/ai-workbench > /dev/null << EOF
server {
    listen 80 default_server;
    server_name _;
    
    # AI Workbench JupyterLab
    location /jupyter/ {
        proxy_pass http://localhost:8888/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # AI Workbench VS Code
    location /vscode/ {
        proxy_pass http://localhost:8080/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # Qwen API
    location /api/ {
        proxy_pass http://localhost:8001/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
    
    # Default redirect to JupyterLab
    location / {
        return 301 /jupyter/;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/ai-workbench /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

# Create welcome script
cat > /workspace/welcome-dgx.sh << 'EOF'
#!/bin/bash
echo "🚀 Welcome to DGX Spark AI Workbench Environment!"
echo "=================================================="
echo ""
echo "🖥️ System Info:"
echo "  Hostname: $(hostname)"
echo "  OS: $(lsb_release -d | cut -f2)"
echo "  Kernel: $(uname -r)"
echo ""
echo "🔧 GPU Info:"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
echo ""
echo "📊 Resource Usage:"
echo "  CPU: $(nproc) cores, Load: $(uptime | awk -F'load average:' '{print $2}')"
echo "  Memory: $(free -h | awk '/^Mem:/ {print $3 "/" $2}')"
echo "  Disk: $(df -h /workspace | awk 'NR==2 {print $3 "/" $2 " (" $5 " used)"}')"
echo ""
echo "🌐 Access URLs:"
echo "  JupyterLab: http://$(hostname)/jupyter/"
echo "  VS Code: http://$(hostname)/vscode/"
echo "  Qwen API: http://$(hostname)/api/"
echo ""
echo "🛠️ Useful Commands:"
echo "  nvwb --help          # AI Workbench CLI help"
echo "  nvidia-smi           # GPU status"
echo "  htop                 # CPU monitoring"
echo "  nvtop                # GPU monitoring"
echo "  docker ps            # Running containers"
echo ""
echo "📁 Important Directories:"
echo "  /workspace/models    # Model cache"
echo "  /workspace/data      # Data directory"
echo "  /workspace/logs      # System logs"
echo "  $HOME/ai-workbench-projects  # AI Workbench projects"
EOF

chmod +x /workspace/welcome-dgx.sh

# Add welcome script to bashrc
echo "" >> $HOME/.bashrc
echo "# DGX Spark AI Workbench Welcome" >> $HOME/.bashrc
echo "/workspace/welcome-dgx.sh" >> $HOME/.bashrc

# Final setup verification
echo ""
echo "🎉 DGX Spark Setup Complete!"
echo "=============================="
echo ""
echo "✅ System Configuration:"
echo "  ✓ AI Workbench CLI installed"
echo "  ✓ Docker with NVIDIA runtime"
echo "  ✓ Workspace directories created"
echo "  ✓ SSH keys configured"
echo "  ✓ HPC lab connectivity setup"
echo "  ✓ Monitoring service enabled"
echo "  ✓ Nginx reverse proxy configured"
echo ""
echo "🔧 Next Steps:"
echo "1. Restart your shell: source ~/.bashrc"
echo "2. Test AI Workbench: nvwb --help"
echo "3. Connect from Mac using NVIDIA Sync"
echo "4. Clone your Qwen project: nvwb clone <project-url>"
echo ""
echo "📝 SSH Public Key (copy to HPC systems):"
cat $HOME/.ssh/id_rsa.pub
echo ""
echo "🌐 Access your DGX Spark at: http://$(hostname)"
echo ""
echo "🎮 Ready for AI Workbench integration! 🚀"