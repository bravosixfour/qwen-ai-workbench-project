#!/bin/bash
# HPC-1 Startup Script (192GB VRAM - Primary Production)
# Optimized for 2x RTX PRO 6000 Blackwell GPUs

set -e

echo "🚀 Starting HPC-1 (Primary Production Server)"
echo "System: AMD 7975WX + 2x RTX PRO 6000 Blackwell (192GB VRAM)"

# Environment setup
export CUDA_VISIBLE_DEVICES="0,1"
export NVIDIA_VISIBLE_DEVICES="0,1"
export HF_HOME="/data/models"
export TORCH_CUDA_ARCH_LIST="9.0"  # Blackwell architecture
export NCCL_DEBUG="INFO"
export NCCL_IB_DISABLE="1"

# Create necessary directories
sudo mkdir -p /data/models /data/outputs /data/cache /data/logs
sudo chown $USER:$USER /data/models /data/outputs /data/cache /data/logs

# GPU health check
echo "📊 Checking GPU status..."
nvidia-smi
if [ $? -ne 0 ]; then
    echo "❌ GPU check failed. Please verify GPU passthrough."
    exit 1
fi

# Memory check
echo "💾 Checking memory availability..."
FREE_MEM=$(free -g | awk '/^Mem:/{print $7}')
if [ $FREE_MEM -lt 100 ]; then
    echo "⚠️  Warning: Only ${FREE_MEM}GB free memory. Recommended: 100GB+"
fi

# Start container with HPC-1 optimizations
echo "🐳 Starting Qwen Image Edit service..."
docker-compose -f docker-compose.hpc-1.yml down 2>/dev/null || true
docker-compose -f docker-compose.hpc-1.yml up -d

# Wait for service to be ready
echo "⏳ Waiting for service to start..."
for i in {1..30}; do
    if curl -sf http://localhost:8001/health > /dev/null 2>&1; then
        echo "✅ HPC-1 service ready!"
        break
    fi
    sleep 2
    if [ $i -eq 30 ]; then
        echo "❌ Service failed to start within 60 seconds"
        docker-compose -f docker-compose.hpc-1.yml logs
        exit 1
    fi
done

# Performance monitoring setup
echo "📈 Setting up performance monitoring..."
cat > /tmp/hpc-1-monitor.py << 'EOF'
import time
import psutil
import subprocess
import json

def get_gpu_stats():
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu', 
                               '--format=csv,noheader,nounits'], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        gpus = []
        for i, line in enumerate(lines):
            if line.strip():
                util, mem_used, mem_total, temp = map(int, line.split(', '))
                gpus.append({
                    'gpu_id': i,
                    'utilization': util,
                    'memory_used': mem_used,
                    'memory_total': mem_total,
                    'memory_percent': round((mem_used / mem_total) * 100, 1),
                    'temperature': temp
                })
        return gpus
    except:
        return []

def log_stats():
    stats = {
        'timestamp': time.time(),
        'cpu_percent': psutil.cpu_percent(),
        'memory': psutil.virtual_memory()._asdict(),
        'gpus': get_gpu_stats()
    }
    
    with open('/data/logs/hpc-1-stats.json', 'a') as f:
        f.write(json.dumps(stats) + '\n')

if __name__ == '__main__':
    while True:
        log_stats()
        time.sleep(30)
EOF

# Start monitoring in background
nohup python3 /tmp/hpc-1-monitor.py > /data/logs/hpc-1-monitor.log 2>&1 &
echo $! > /data/logs/hpc-1-monitor.pid

# Display service info
echo ""
echo "🎉 HPC-1 READY!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 API Endpoint:    http://$(hostname):8001"
echo "🎨 Mango Editor:    http://$(hostname):3001"
echo "📚 Documentation:  http://$(hostname):8001/docs"
echo "📊 Health Check:   http://$(hostname):8001/health"
echo "📈 Logs:           /data/logs/"
echo ""
echo "💡 Performance Configuration:"
echo "   • Strategy: Multi-GPU Data Parallel"
echo "   • Precision: BF16 (Blackwell optimized)"
echo "   • Batch Size: 16 (utilizing 192GB VRAM)"
echo "   • Workers: 8"
echo ""
echo "🔧 To stop: docker-compose -f docker-compose.hpc-1.yml down"
echo "📊 Monitor: tail -f /data/logs/hpc-1-stats.json"