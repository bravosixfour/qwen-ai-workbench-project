"""
Simple Qwen Image Edit API Server for AI Workbench
Lightweight FastAPI server for initial testing
"""

import os
import logging
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
import uvicorn
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
model_status = {"loaded": False, "device": "cpu"}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting Qwen Image Edit API (Simple Mode)...")
    await initialize_service()
    yield
    # Shutdown
    logger.info("Shutting down Qwen Image Edit API...")

async def initialize_service():
    """Initialize the service"""
    global model_status
    
    try:
        # Check for GPU availability
        try:
            import torch
            if torch.cuda.is_available():
                model_status["device"] = "cuda"
                logger.info(f"GPU detected: {torch.cuda.get_device_name()}")
            else:
                model_status["device"] = "cpu"
                logger.info("Using CPU mode")
        except ImportError:
            logger.info("PyTorch not available, using basic mode")
        
        model_status["loaded"] = True
        logger.info("Service initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize service: {e}")
        model_status["loaded"] = False

app = FastAPI(
    title="Qwen Image Edit API",
    description="AI-powered image editing using Qwen-Image-Edit-2509",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Qwen Image Edit API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    import psutil
    
    # Basic system info
    cpu_percent = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    
    # GPU info (if available)
    gpu_info = []
    gpu_available = False
    
    try:
        import torch
        if torch.cuda.is_available():
            gpu_available = True
            # Try to get basic GPU info without GPUtil
            for i in range(torch.cuda.device_count()):
                gpu_info.append({
                    "id": i,
                    "name": torch.cuda.get_device_name(i),
                    "memory_allocated": f"{torch.cuda.memory_allocated(i) / 1024**3:.1f}GB",
                    "memory_cached": f"{torch.cuda.memory_reserved(i) / 1024**3:.1f}GB"
                })
    except:
        pass
    
    return {
        "status": "healthy",
        "model_loaded": model_status["loaded"],
        "device": model_status["device"],
        "gpu_available": gpu_available,
        "gpu_info": gpu_info,
        "system": {
            "cpu_percent": f"{cpu_percent}%",
            "memory_percent": f"{memory.percent}%",
            "memory_available": f"{memory.available / 1024**3:.1f}GB"
        }
    }

@app.get("/v1/models")
async def list_models():
    """List available models"""
    return {
        "data": [
            {
                "id": "qwen-image-edit-2509",
                "object": "model",
                "created": 1699000000,
                "owned_by": "qwen"
            }
        ],
        "object": "list"
    }

@app.post("/v1/images/edits")
async def edit_image(
    image: UploadFile = File(...),
    prompt: str = Form(...),
    n: int = Form(1),
    size: str = Form("1024x1024"),
    response_format: str = Form("url")
):
    """Single image editing endpoint"""
    if not model_status["loaded"]:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    # Validate inputs
    if not image.content_type or not image.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Invalid image file")
    
    try:
        # Read image
        image_data = await image.read()
        logger.info(f"Received image: {image.filename}, size: {len(image_data)} bytes")
        logger.info(f"Edit prompt: {prompt}")
        
        # Placeholder for actual model inference
        # In real implementation, this would call the Qwen model
        result_url = "http://localhost:8000/outputs/edited_image.jpg"
        
        return {
            "created": 1699000000,
            "data": [
                {
                    "url": result_url
                }
            ]
        }
        
    except Exception as e:
        logger.error(f"Error editing image: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/test/upload")
async def test_upload(file: UploadFile = File(...)):
    """Test file upload endpoint"""
    try:
        contents = await file.read()
        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(contents),
            "message": "File uploaded successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Upload failed: {str(e)}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)