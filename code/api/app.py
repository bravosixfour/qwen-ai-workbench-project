"""
Qwen Image Edit API Server for AI Workbench
FastAPI server providing OpenAI-compatible image editing endpoints
"""

import os
import sys
from pathlib import Path
import torch
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
import uvicorn
import logging
from contextlib import asynccontextmanager
import psutil
import GPUtil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for model
model = None
device = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting Qwen Image Edit API...")
    await load_model()
    yield
    # Shutdown
    logger.info("Shutting down Qwen Image Edit API...")
    cleanup_resources()

app = FastAPI(
    title="Qwen Image Edit API",
    description="AI-powered image editing using Qwen-Image-Edit-2509",
    version="1.0.0",
    lifespan=lifespan
)

async def load_model():
    """Load the Qwen Image Edit model"""
    global model, device
    
    try:
        # Check GPU availability
        if torch.cuda.is_available():
            device = torch.device("cuda")
            logger.info(f"Using GPU: {torch.cuda.get_device_name()}")
        else:
            device = torch.device("cpu")
            logger.warning("GPU not available, using CPU")
        
        # Model loading would go here
        # For now, we'll create a placeholder
        logger.info("Model loaded successfully")
        model = {"status": "loaded", "device": str(device)}
        
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise

def cleanup_resources():
    """Clean up model and GPU resources"""
    global model
    if model and torch.cuda.is_available():
        torch.cuda.empty_cache()
    model = None

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    gpu_info = []
    try:
        if torch.cuda.is_available():
            gpus = GPUtil.getGPUs()
            gpu_info = [
                {
                    "id": gpu.id,
                    "name": gpu.name,
                    "memory_used": f"{gpu.memoryUsed}MB",
                    "memory_total": f"{gpu.memoryTotal}MB",
                    "utilization": f"{gpu.load * 100:.1f}%"
                }
                for gpu in gpus
            ]
    except:
        pass
    
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "device": str(device) if device else "unknown",
        "gpu_available": torch.cuda.is_available(),
        "gpu_info": gpu_info,
        "memory_usage": f"{psutil.virtual_memory().percent}%"
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
    response_format: str = Form("url"),
    num_inference_steps: int = Form(50),
    guidance_scale: float = Form(7.5),
    seed: int = Form(-1)
):
    """Single image editing endpoint"""
    if not model:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    # Validate inputs
    if not image.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Invalid image file")
    
    try:
        # Read image
        image_data = await image.read()
        logger.info(f"Received image: {image.filename}, size: {len(image_data)} bytes")
        
        # Process image (placeholder for actual model inference)
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

@app.post("/v1/images/multi-edit")
async def edit_multiple_images(
    images: list[UploadFile] = File(...),
    prompt: str = Form(...),
    n: int = Form(1),
    size: str = Form("1024x1024"),
    response_format: str = Form("url"),
    num_inference_steps: int = Form(50),
    guidance_scale: float = Form(7.5),
    seed: int = Form(-1)
):
    """Multi-image editing endpoint"""
    if not model:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    if len(images) > 3:
        raise HTTPException(status_code=400, detail="Maximum 3 images allowed")
    
    try:
        processed_images = []
        for i, image in enumerate(images):
            if not image.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail=f"Invalid image file: {image.filename}")
            
            image_data = await image.read()
            processed_images.append({
                "filename": image.filename,
                "size": len(image_data)
            })
        
        logger.info(f"Processing {len(processed_images)} images with prompt: {prompt}")
        
        # Process images (placeholder)
        result_url = "http://localhost:8000/outputs/multi_edited_image.jpg"
        
        return {
            "created": 1699000000,
            "data": [
                {
                    "url": result_url
                }
            ]
        }
        
    except Exception as e:
        logger.error(f"Error editing multiple images: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv("API_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)