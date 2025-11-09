#!/bin/bash
# HPC-2 Startup Script (96GB VRAM - Multi-User Server)
# Optimized for 3x RTX 5090 GPUs (Pipeline Parallel)

set -e

echo "⚡ Starting HPC-2 (Multi-User/Parallel Server)"
echo "System: AMD 7975WX + 3x RTX 5090 (96GB total VRAM)"

# Environment setup
export CUDA_VISIBLE_DEVICES="0,1,2"
export NVIDIA_VISIBLE_DEVICES="0,1,2"
export HF_HOME="/data/models"
export TORCH_CUDA_ARCH_LIST="8.9"  # Ada Lovelace
export NCCL_DEBUG="INFO"
export NCCL_IB_DISABLE="1"

# Create necessary directories
sudo mkdir -p /data/models /data/outputs /data/cache /data/logs
sudo chown $USER:$USER /data/models /data/outputs /data/cache /data/logs

# GPU health check
echo "📊 Checking 3x RTX 5090 GPUs..."
nvidia-smi
GPU_COUNT=$(nvidia-smi --list-gpus | wc -l)
if [ $GPU_COUNT -ne 3 ]; then
    echo "❌ Expected 3 GPUs, found $GPU_COUNT. Check GPU passthrough."
    exit 1
fi

# Memory check
echo "💾 Checking memory availability..."
FREE_MEM=$(free -g | awk '/^Mem:/{print $7}')
if [ $FREE_MEM -lt 80 ]; then
    echo "⚠️  Warning: Only ${FREE_MEM}GB free memory. Recommended: 80GB+"
fi

# Start container with HPC-2 optimizations
echo "🐳 Starting Qwen Image Edit service (Pipeline Parallel)..."
docker-compose -f docker-compose.hpc-2.yml down 2>/dev/null || true
docker-compose -f docker-compose.hpc-2.yml up -d

# Wait for service to be ready
echo "⏳ Waiting for multi-GPU service to start..."
for i in {1..45}; do
    if curl -sf http://localhost:8002/health > /dev/null 2>&1; then
        echo "✅ HPC-2 multi-GPU service ready!"
        break
    fi
    sleep 2
    if [ $i -eq 45 ]; then
        echo "❌ Service failed to start within 90 seconds"
        docker-compose -f docker-compose.hpc-2.yml logs
        exit 1
    fi
done

# GPU load balancing check
echo "⚖️ Checking GPU load distribution..."
python3 << 'EOF'
import subprocess
import time

def check_gpu_balance():
    result = subprocess.run(['nvidia-smi', '--query-gpu=index,utilization.gpu,memory.used', 
                           '--format=csv,noheader,nounits'], capture_output=True, text=True)
    
    print("GPU Load Distribution:")
    lines = result.stdout.strip().split('\n')
    total_util = 0
    for line in lines:
        if line.strip():
            gpu_id, util, mem = line.split(', ')
            print(f"  GPU {gpu_id}: {util}% utilization, {mem}MB memory")
            total_util += int(util)
    
    avg_util = total_util / 3
    print(f"Average utilization: {avg_util:.1f}%")
    
    if avg_util > 10:
        print("✅ GPUs are active and processing")
    else:
        print("⏳ GPUs warming up...")

check_gpu_balance()
EOF

# Performance monitoring setup
echo "📈 Setting up multi-GPU monitoring..."
cat > /tmp/hpc-2-monitor.py << 'EOF'
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

def calculate_pipeline_efficiency():
    gpus = get_gpu_stats()
    if len(gpus) == 3:
        utilizations = [gpu['utilization'] for gpu in gpus]
        avg_util = sum(utilizations) / len(utilizations)
        util_variance = sum((u - avg_util) ** 2 for u in utilizations) / len(utilizations)
        efficiency = max(0, 100 - util_variance)  # Lower variance = better pipeline efficiency
        return efficiency
    return 0

def log_stats():
    stats = {
        'timestamp': time.time(),
        'cpu_percent': psutil.cpu_percent(),
        'memory': psutil.virtual_memory()._asdict(),
        'gpus': get_gpu_stats(),
        'pipeline_efficiency': calculate_pipeline_efficiency()
    }
    
    with open('/data/logs/hpc-2-stats.json', 'a') as f:
        f.write(json.dumps(stats) + '\n')

if __name__ == '__main__':
    while True:
        log_stats()
        time.sleep(30)
EOF

# Start monitoring in background
nohup python3 /tmp/hpc-2-monitor.py > /data/logs/hpc-2-monitor.log 2>&1 &
echo $! > /data/logs/hpc-2-monitor.pid

# Setup load balancer health checks
echo "🔍 Setting up health check endpoints..."
cat > /tmp/hpc-2-healthcheck.sh << 'EOF'
#!/bin/bash
# Multi-GPU health check for load balancer

GPU_HEALTH=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits | awk '{sum+=$1; count++} END {print (sum/count < 85) ? "healthy" : "overheating"}')
SERVICE_HEALTH=$(curl -sf http://localhost:8002/health >/dev/null && echo "healthy" || echo "unhealthy")

if [ "$GPU_HEALTH" = "healthy" ] && [ "$SERVICE_HEALTH" = "healthy" ]; then
    echo "healthy"
    exit 0
else
    echo "unhealthy: gpu=$GPU_HEALTH service=$SERVICE_HEALTH"
    exit 1
fi
EOF

chmod +x /tmp/hpc-2-healthcheck.sh

# Display service info
echo ""
echo "🎉 HPC-2 READY!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 API Endpoint:    http://$(hostname):8002"
echo "🎨 Mango Editor:    http://$(hostname):3002"
echo "📚 Documentation:  http://$(hostname):8002/docs"
echo "📊 Health Check:   http://$(hostname):8002/health"
echo "⚖️ Load Balancer:  /tmp/hpc-2-healthcheck.sh"
echo "📈 Logs:           /data/logs/"
echo ""
echo "💡 Performance Configuration:"
echo "   • Strategy: Pipeline Parallel (3-GPU)"
echo "   • Precision: FP16"
echo "   • Batch Size: 8 per GPU"
echo "   • Workers: 6"
echo "   • Pipeline Stages: 3"
echo ""
echo "🔧 To stop: docker-compose -f docker-compose.hpc-2.yml down"
echo "📊 Monitor: tail -f /data/logs/hpc-2-stats.json"