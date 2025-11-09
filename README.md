# Qwen Image Edit AI Workbench Project

Enterprise-ready deployment of Qwen-Image-Edit-2509 AI model optimized for NVIDIA DGX systems and AI Workbench.

## 🚀 Features

- **Multi-GPU Support**: Optimized for DGX Spark and other NVIDIA systems
- **AI Workbench Native**: Deploy across multiple servers with one click
- **Production Ready**: Built-in health checks, logging, and monitoring
- **Web UI Included**: Mango Editor for easy image editing
- **Scalable**: Redis queue management for high-throughput processing

## 📋 Requirements

### Hardware
- **GPU**: NVIDIA GPU with 48GB+ VRAM (RTX 6000 Ada, A100, H100)
- **DGX Systems**: Optimized for DGX Spark, DGX A100, DGX H100
- **RAM**: 32GB+ system memory
- **Storage**: 100GB+ for models and outputs

### Software
- **NVIDIA AI Workbench**: Latest version
- **CUDA**: 12.0+ (included in base image)
- **Internet**: For initial model download

## 🛠️ Installation

### 1. Clone in AI Workbench

1. Open NVIDIA AI Workbench
2. Click "Clone Project"
3. Enter this repository URL
4. Select your GPU configuration

### 2. Configure Environment

Set these secrets in AI Workbench:
- `HF_TOKEN`: Your HuggingFace token (for gated models)
- `API_KEY`: Optional API key for security

### 3. Build Project

AI Workbench will automatically:
- Install all dependencies
- Download required models
- Configure the environment
- Set up Redis cache

## 🎮 Usage

### Start Services

From AI Workbench UI:
1. Click "Start All" to launch all services
2. Or start individually:
   - **Qwen API**: Core inference API
   - **Mango Editor**: Web UI for editing
   - **Redis Cache**: Queue management

### Access Points

- **Mango Editor**: Opens automatically (port 3002)
- **API Documentation**: http://localhost:8000/docs
- **JupyterLab**: Available for development

### API Examples

```bash
# Health check
curl http://localhost:8000/health

# Edit single image
curl -X POST http://localhost:8000/v1/images/edits \
  -F "image=@input.jpg" \
  -F "prompt=Make the sky sunset orange"

# Multi-image editing
curl -X POST http://localhost:8000/v1/images/multi-edit \
  -F "images=@img1.jpg" \
  -F "images=@img2.jpg" \
  -F "prompt=Blend these images naturally"
```

## 🔧 Configuration

### GPU Selection

Edit `.project/spec.yaml`:
```yaml
resources:
    gpu:
        requested: 2  # For multi-GPU
```

### Model Configuration

Set in environment variables:
- `MODEL_NAME`: Default "Qwen/Qwen-Image-Edit-2509"
- `BATCH_SIZE`: Adjust for your GPU memory
- `NUM_WORKERS`: API worker processes

### Performance Tuning

For DGX Spark optimization:
```bash
# Enable MIG mode for multiple instances
nvidia-smi -mig 1

# Configure specific GPU
export CUDA_VISIBLE_DEVICES=0,1
```

## 📊 Monitoring

### Built-in Dashboards
- API metrics: `/metrics`
- Health status: `/health`
- GPU usage: JupyterLab terminal

### Logs
All logs stored in `/project/data/logs/`:
- `api.log`: API server logs
- `editor.log`: UI logs
- `redis.log`: Cache logs

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐
│  Mango Editor   │────▶│   Qwen API      │
│   (Port 3002)   │     │  (Port 8000)    │
└─────────────────┘     └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │      Redis      │
                        │  (Port 6379)    │
                        └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │   GPU + Model   │
                        │  (48GB+ VRAM)   │
                        └─────────────────┘
```

## 🚨 Troubleshooting

### Model Loading Issues
```bash
# Check model files
ls -la /project/models/

# Re-download models
python /project/code/scripts/download_models.py
```

### GPU Memory Errors
- Reduce batch size
- Use single image mode
- Enable model quantization

### API Not Responding
```bash
# Check service status
curl http://localhost:8000/health

# View logs
tail -f /project/data/logs/api.log
```

## 🔐 Security

- Set `API_KEY` for production deployments
- Use AI Workbench secrets for sensitive data
- Enable HTTPS proxy in production
- Restrict network access as needed

## 📈 Scaling

### Multi-Server Deployment
1. Export project from AI Workbench
2. Import on target DGX system
3. Configure GPU allocation
4. Start services

### Load Balancing
Use AI Workbench's built-in load balancer or deploy behind nginx.

## 🤝 Contributing

1. Fork the project
2. Create feature branch
3. Test on AI Workbench
4. Submit pull request

## 📄 License

Private deployment - see LICENSE file

## 🆘 Support

- AI Workbench issues: [NVIDIA Forums](https://forums.developer.nvidia.com)
- Project issues: Create GitHub issue
- DGX support: NVIDIA Enterprise Support