# HPC Lab Startup Scripts

**Mac Studio → DGX Spark → HPC Lab Orchestration**

## 🎮 Quick Start from Your Mac

### **One-Command Deployment:**
```bash
# Deploy and start all HPC systems
./startup-scripts/mac-orchestrator.sh deploy

# View unified dashboard
./startup-scripts/mac-orchestrator.sh dashboard
```

## 📋 Available Commands

### **Mac Studio Orchestration:**
```bash
# Main orchestrator (run from your Mac)
./mac-orchestrator.sh dashboard     # Show unified lab status
./mac-orchestrator.sh deploy        # Deploy to all systems
./mac-orchestrator.sh stop          # Stop all services
./mac-orchestrator.sh deploy-hpc1   # Deploy only HPC-1
./mac-orchestrator.sh deploy-hpc2   # Deploy only HPC-2  
./mac-orchestrator.sh deploy-hpc3   # Deploy only HPC-3
./mac-orchestrator.sh status        # Check service status
./mac-orchestrator.sh resources     # Show resource usage
./mac-orchestrator.sh logs hpc1     # Show system logs
```

### **Individual System Startup:**
```bash
# HPC-1 (Primary Production - 192GB VRAM)
ssh hpc-1.lab
./start-hpc-1.sh

# HPC-2 (Multi-User - 3x RTX 5090)
ssh hpc-2.lab  
./start-hpc-2.sh

# HPC-3 (Development - L40 48GB)
ssh hpc-3.lab
./start-hpc-3.sh
```

## 🚀 System-Specific Features

### **HPC-1 (Primary Production):**
- **Hardware:** 2x RTX PRO 6000 Blackwell (192GB VRAM)
- **Strategy:** Multi-GPU Data Parallel
- **Optimization:** BF16 precision, batch size 16
- **Best For:** Largest models, complex processing
- **Endpoints:** 
  - API: `http://hpc-1:8001`
  - UI: `http://hpc-1:3001`

### **HPC-2 (Multi-User Server):**
- **Hardware:** 3x RTX 5090 (96GB total VRAM)
- **Strategy:** Pipeline Parallel Processing
- **Optimization:** FP16 precision, 3-stage pipeline
- **Best For:** Multiple users, parallel workloads
- **Endpoints:**
  - API: `http://hpc-2:8002`
  - UI: `http://hpc-2:3002`

### **HPC-3 (Development):**
- **Hardware:** NVIDIA L40 (48GB VRAM)
- **Strategy:** Single GPU with quantization
- **Features:** Code server, experiment tracking
- **Best For:** Development, testing, experimentation
- **Endpoints:**
  - API: `http://hpc-3:8003`
  - UI: `http://hpc-3:3003`
  - Code Server: `http://hpc-3:8080` (password: hpc3-dev-2024)

## 🔧 Configuration Details

### **Automatic Optimizations:**
- **GPU Detection:** Scripts auto-detect and configure GPUs
- **Memory Management:** Optimized for each system's VRAM
- **Cooling Support:** Takes advantage of your watercooling setup
- **Network:** Configured for 10GbE lab network

### **Monitoring & Logging:**
- **Real-time Stats:** GPU utilization, memory, temperature
- **Health Checks:** Automatic service monitoring
- **Performance Metrics:** Inference speed, queue depth
- **Log Location:** `/data/logs/` on each system

### **Development Tools (HPC-3):**
- **Code Server:** Web-based VS Code for remote development
- **Experiment Tracking:** Built-in experiment logging
- **Model Testing:** Quick test scripts for validation
- **Resource Monitoring:** Lightweight development monitoring

## 🌐 Access URLs After Deployment

```bash
# Production Services
HPC-1 API:        http://hpc-1.lab:8001
HPC-1 UI:         http://hpc-1.lab:3001

# Multi-User Services  
HPC-2 API:        http://hpc-2.lab:8002
HPC-2 UI:         http://hpc-2.lab:3002

# Development Services
HPC-3 API:        http://hpc-3.lab:8003
HPC-3 UI:         http://hpc-3.lab:3003
HPC-3 Code:       http://hpc-3.lab:8080
```

## 🎯 Typical Workflow

### **Daily Development:**
```bash
# 1. Check status from Mac
./mac-orchestrator.sh dashboard

# 2. Deploy if needed
./mac-orchestrator.sh deploy

# 3. Develop on HPC-3
open http://hpc-3.lab:8080

# 4. Test on HPC-1 when ready
curl -X POST http://hpc-1.lab:8001/edit ...
```

### **Production Deployment:**
```bash
# 1. Test on HPC-3
./mac-orchestrator.sh deploy-hpc3

# 2. Validate on HPC-2  
./mac-orchestrator.sh deploy-hpc2

# 3. Deploy to production HPC-1
./mac-orchestrator.sh deploy-hpc1

# 4. Monitor all systems
./mac-orchestrator.sh dashboard
```

## 🛠️ Troubleshooting

### **Common Issues:**
```bash
# Check connectivity
ping hpc-1.lab
ssh hpc-1.lab

# Check GPU status
ssh hpc-1.lab "nvidia-smi"

# Check service logs
./mac-orchestrator.sh logs hpc1

# Restart specific system
ssh hpc-1.lab "cd /data/qwen-ai-workbench-project && docker-compose down && ./start-hpc-1.sh"
```

### **Performance Tuning:**
- **HPC-1:** Increase batch size to 24+ if stable
- **HPC-2:** Adjust pipeline parallel size based on workload
- **HPC-3:** Enable quantization for faster iteration

## 💡 Pro Tips

1. **Start with HPC-3** for development and testing
2. **Use HPC-1** for final validation and production
3. **Scale with HPC-2** when you need multiple users
4. **Monitor watercooling** - your setup can handle sustained loads
5. **Use the dashboard** regularly to monitor all systems

Your lab setup is optimized for the **best AI development experience** with seamless Mac integration! 🚀