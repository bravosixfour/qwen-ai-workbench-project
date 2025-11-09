#!/bin/bash
# HPC-3 Startup Script (48GB VRAM - Development Server)
# Optimized for NVIDIA L40 (Development/Testing)

set -e

echo "🔧 Starting HPC-3 (Development/Testing Server)"
echo "System: AMD 7970X + NVIDIA L40 (48GB VRAM)"

# Environment setup
export CUDA_VISIBLE_DEVICES="0"
export NVIDIA_VISIBLE_DEVICES="0"
export HF_HOME="/data/models"
export TORCH_CUDA_ARCH_LIST="8.9"  # Ada Lovelace
export PYTORCH_CUDA_ALLOC_CONF="max_split_size_mb:2048"

# Create necessary directories
sudo mkdir -p /data/models /data/outputs /data/cache /data/logs /data/experiments
sudo chown $USER:$USER /data/models /data/outputs /data/cache /data/logs /data/experiments

# GPU health check
echo "📊 Checking L40 GPU..."
nvidia-smi
GPU_COUNT=$(nvidia-smi --list-gpus | wc -l)
if [ $GPU_COUNT -ne 1 ]; then
    echo "❌ Expected 1 GPU (L40), found $GPU_COUNT. Check GPU passthrough."
    exit 1
fi

# Memory check
echo "💾 Checking memory availability..."
FREE_MEM=$(free -g | awk '/^Mem:/{print $7}')
if [ $FREE_MEM -lt 50 ]; then
    echo "⚠️  Warning: Only ${FREE_MEM}GB free memory. Recommended: 50GB+"
fi

# Development environment setup
echo "🛠️ Setting up development environment..."

# Install development tools if not present
if ! command -v git &> /dev/null; then
    echo "Installing git..."
    sudo apt-get update && sudo apt-get install -y git
fi

if ! command -v code &> /dev/null && ! command -v code-server &> /dev/null; then
    echo "Setting up code-server for remote development..."
    curl -fsSL https://code-server.dev/install.sh | sh -s -- --method=standalone
    
    # Configure code-server
    mkdir -p ~/.config/code-server
    cat > ~/.config/code-server/config.yaml << EOF
bind-addr: 0.0.0.0:8080
auth: password
password: hpc3-dev-2024
cert: false
EOF
fi

# Start container with HPC-3 optimizations
echo "🐳 Starting Qwen Image Edit service (Development Mode)..."
docker-compose -f docker-compose.hpc-3.yml down 2>/dev/null || true
docker-compose -f docker-compose.hpc-3.yml up -d

# Wait for service to be ready
echo "⏳ Waiting for development service to start..."
for i in {1..30}; do
    if curl -sf http://localhost:8003/health > /dev/null 2>&1; then
        echo "✅ HPC-3 development service ready!"
        break
    fi
    sleep 2
    if [ $i -eq 30 ]; then
        echo "❌ Service failed to start within 60 seconds"
        docker-compose -f docker-compose.hpc-3.yml logs
        exit 1
    fi
done

# Start code-server for remote development
echo "🖥️ Starting code-server..."
nohup ~/.local/bin/code-server --config ~/.config/code-server/config.yaml > /data/logs/code-server.log 2>&1 &
echo $! > /data/logs/code-server.pid

# Performance monitoring setup (lightweight for dev)
echo "📈 Setting up development monitoring..."
cat > /tmp/hpc-3-monitor.py << 'EOF'
import time
import psutil
import subprocess
import json
import os

def get_gpu_stats():
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu', 
                               '--format=csv,noheader,nounits'], capture_output=True, text=True)
        line = result.stdout.strip()
        if line:
            util, mem_used, mem_total, temp = map(int, line.split(', '))
            return {
                'utilization': util,
                'memory_used': mem_used,
                'memory_total': mem_total,
                'memory_percent': round((mem_used / mem_total) * 100, 1),
                'temperature': temp
            }
    except:
        pass
    return {}

def get_model_usage():
    # Check if any models are loaded in memory
    gpu_stats = get_gpu_stats()
    memory_used = gpu_stats.get('memory_used', 0)
    
    if memory_used > 5000:  # More than 5GB suggests model loaded
        return "active"
    elif memory_used > 1000:  # 1-5GB suggests partial load
        return "loading"
    else:
        return "idle"

def log_stats():
    gpu_stats = get_gpu_stats()
    
    stats = {
        'timestamp': time.time(),
        'cpu_percent': psutil.cpu_percent(),
        'memory': psutil.virtual_memory()._asdict(),
        'gpu': gpu_stats,
        'model_status': get_model_usage(),
        'disk_usage': psutil.disk_usage('/data')._asdict()
    }
    
    # Keep only last 1000 entries for dev monitoring
    log_file = '/data/logs/hpc-3-stats.json'
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            lines = f.readlines()
        if len(lines) > 1000:
            with open(log_file, 'w') as f:
                f.writelines(lines[-900:])  # Keep last 900 entries
    
    with open(log_file, 'a') as f:
        f.write(json.dumps(stats) + '\n')

if __name__ == '__main__':
    while True:
        log_stats()
        time.sleep(60)  # Log every minute for dev
EOF

# Start monitoring in background
nohup python3 /tmp/hpc-3-monitor.py > /data/logs/hpc-3-monitor.log 2>&1 &
echo $! > /data/logs/hpc-3-monitor.pid

# Setup development utilities
echo "🔬 Setting up development utilities..."

# Create experiment tracking script
cat > /data/experiments/track_experiment.py << 'EOF'
#!/usr/bin/env python3
import json
import time
import sys
from pathlib import Path

def log_experiment(name, config, results=None):
    """Log experiment with timestamp"""
    experiment = {
        'name': name,
        'timestamp': time.time(),
        'config': config,
        'results': results or {}
    }
    
    log_file = Path('/data/experiments/experiment_log.jsonl')
    with open(log_file, 'a') as f:
        f.write(json.dumps(experiment) + '\n')
    
    print(f"Experiment '{name}' logged to {log_file}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python track_experiment.py <name> <config_json>")
        sys.exit(1)
    
    name = sys.argv[1]
    config = json.loads(sys.argv[2])
    log_experiment(name, config)
EOF

chmod +x /data/experiments/track_experiment.py

# Create model testing script
cat > /data/experiments/test_model.sh << 'EOF'
#!/bin/bash
# Quick model testing script for HPC-3

MODEL_NAME=${1:-"qwen2-vl-7b"}
TEST_IMAGE=${2:-"/data/experiments/test_image.jpg"}

echo "🧪 Testing model: $MODEL_NAME"
echo "📷 Test image: $TEST_IMAGE"

# Basic inference test
curl -X POST http://localhost:8003/edit \
  -F "image=@$TEST_IMAGE" \
  -F "instruction=Remove the background" \
  -F "model=$MODEL_NAME" \
  --max-time 60 \
  -o "/data/experiments/test_output_$(date +%s).jpg"

echo "✅ Test completed. Output saved to /data/experiments/"
EOF

chmod +x /data/experiments/test_model.sh

# Create sample test image if it doesn't exist
if [ ! -f /data/experiments/test_image.jpg ]; then
    echo "📷 Creating sample test image..."
    python3 << 'EOF'
from PIL import Image
import numpy as np

# Create a simple test image
img = Image.new('RGB', (512, 512), color=(135, 206, 235))  # Sky blue
img.save('/data/experiments/test_image.jpg')
print("Sample test image created at /data/experiments/test_image.jpg")
EOF
fi

# Display service info
echo ""
echo "🎉 HPC-3 READY!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 API Endpoint:    http://$(hostname):8003"
echo "🎨 Mango Editor:    http://$(hostname):3003"
echo "🖥️ Code Server:     http://$(hostname):8080 (password: hpc3-dev-2024)"
echo "📚 Documentation:  http://$(hostname):8003/docs"
echo "📊 Health Check:   http://$(hostname):8003/health"
echo "🧪 Experiments:    /data/experiments/"
echo "📈 Logs:           /data/logs/"
echo ""
echo "💡 Development Configuration:"
echo "   • Strategy: Single GPU (L40)"
echo "   • Precision: FP16"
echo "   • Batch Size: 4 (memory conservative)"
echo "   • Quantization: Available (8-bit/4-bit)"
echo "   • Model Cache: /data/models"
echo ""
echo "🛠️ Development Commands:"
echo "   • Test model: /data/experiments/test_model.sh [model_name] [image]"
echo "   • Log experiment: python /data/experiments/track_experiment.py name '{\"config\":\"value\"}'"
echo "   • Monitor GPU: nvidia-smi -l 5"
echo ""
echo "🔧 To stop: docker-compose -f docker-compose.hpc-3.yml down"
echo "📊 Monitor: tail -f /data/logs/hpc-3-stats.json"