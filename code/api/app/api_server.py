#!/usr/bin/env python3
"""
OpenAI-Compatible API Server for Qwen-Image-Edit-2509
Supports MULTI-IMAGE editing (1-3 images) + Single image editing
Compatible with Open WebUI and other OpenAI-compatible clients

Key Features:
- Multi-image editing (person + scene, person + product, etc.)
- Natural language editing with advanced consistency
- ControlNet support (depth, edge, keypoint, sketch)
- OpenAI-compatible REST API

Usage:
    python3 api_server.py

API Endpoints:
    - POST /v1/images/edits - Edit images (single or multi-image)
    - POST /v1/images/multi-edit - Multi-image editing (explicit)
    - POST /v1/images/generations - Generate images (placeholder)
    - GET /v1/models - List available models
    - GET /health - Health check
"""

import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import torch
from diffusers import DiffusionPipeline
from PIL import Image
import io
import base64
from datetime import datetime
import random
from typing import Optional, List
import uvicorn
from pydantic import BaseModel
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
#  CONFIGURATION
# ============================================================

API_HOST = "0.0.0.0"
API_PORT = 8000
MODEL_NAME = "Qwen/Qwen-Image-Edit-2509"

# ============================================================
#  LOAD MODEL
# ============================================================

print("=" * 60)
print("  Qwen-Image-Edit-2509 API Server")
print("  OpenAI-Compatible | Multi-Image Support | Open WebUI Ready")
print("=" * 60)
print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"Loading model: {MODEL_NAME}")
print()

try:
    pipe = DiffusionPipeline.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.bfloat16,
        trust_remote_code=True
    )
    pipe = pipe.to("cuda")
    print("✓ Model loaded successfully!")
    print("✓ Multi-image editing: ENABLED (1-3 images)")
    print("✓ Natural language editing: ENABLED")
    print()
except Exception as e:
    print(f"✗ Error loading model: {e}")
    exit(1)

# ============================================================
#  FASTAPI APP
# ============================================================

app = FastAPI(
    title="Qwen-Image-Edit-2509 API",
    description="OpenAI-compatible API with Multi-Image Editing Support",
    version="2.0.0"
)

# Enable CORS for Open WebUI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve output images
os.makedirs("./outputs", exist_ok=True)
app.mount("/outputs", StaticFiles(directory="./outputs"), name="outputs")

# ============================================================
#  MODELS
# ============================================================

class ImageEditRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = " "  # Single space recommended
    num_inference_steps: Optional[int] = 40
    true_cfg_scale: Optional[float] = 4.0
    guidance_scale: Optional[float] = 1.0
    seed: Optional[int] = -1
    num_images_per_prompt: Optional[int] = 1

class MultiImageEditRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = " "
    num_inference_steps: Optional[int] = 40
    true_cfg_scale: Optional[float] = 4.0
    guidance_scale: Optional[float] = 1.0
    seed: Optional[int] = -1

# ============================================================
#  HELPER FUNCTIONS
# ============================================================

def image_to_base64(image: Image.Image, format: str = "PNG") -> str:
    """Convert PIL Image to base64 string"""
    buffered = io.BytesIO()
    image.save(buffered, format=format)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str

def base64_to_image(base64_string: str) -> Image.Image:
    """Convert base64 string to PIL Image"""
    img_data = base64.b64decode(base64_string)
    return Image.open(io.BytesIO(img_data))

def save_output(image: Image.Image, prefix: str = "api") -> str:
    """Save image to outputs directory"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_id = random.randint(1000, 9999)
    filename = f"{prefix}_{timestamp}_{random_id}.png"
    filepath = os.path.join("./outputs", filename)
    image.save(filepath)
    return filename

async def load_images_from_uploads(files: List[UploadFile]) -> List[Image.Image]:
    """Load multiple images from uploaded files"""
    images = []
    for file in files:
        image_data = await file.read()
        img = Image.open(io.BytesIO(image_data)).convert("RGB")
        images.append(img)
    return images

# ============================================================
#  API ENDPOINTS
# ============================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Qwen-Image-Edit-2509 API Server",
        "version": "2.0.0",
        "model": MODEL_NAME,
        "features": {
            "multi_image_editing": True,
            "max_images": 3,
            "natural_language": True,
            "controlnet_support": True
        },
        "endpoints": {
            "edit_single": "POST /v1/images/edits",
            "edit_multi": "POST /v1/images/multi-edit",
            "models": "GET /v1/models",
            "health": "GET /health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model_loaded": True,
        "gpu_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "vram_used_mb": torch.cuda.memory_allocated(0) / 1024 / 1024 if torch.cuda.is_available() else 0
    }

@app.get("/v1/models")
async def list_models():
    """List available models (OpenAI-compatible)"""
    return {
        "object": "list",
        "data": [
            {
                "id": "qwen-image-edit-2509",
                "object": "model",
                "created": 1709251200,
                "owned_by": "qwen",
                "capabilities": {
                    "multi_image": True,
                    "max_images": 3,
                    "controlnet": True,
                    "natural_language": True
                }
            }
        ]
    }

@app.post("/v1/images/edits")
async def edit_image(
    image: UploadFile = File(...),
    prompt: str = Form(...),
    negative_prompt: str = Form(" "),
    n: int = Form(1),
    num_inference_steps: int = Form(40),
    true_cfg_scale: float = Form(4.0),
    guidance_scale: float = Form(1.0),
    seed: int = Form(-1),
    response_format: str = Form("url")
):
    """
    Edit single image using natural language prompt (OpenAI-compatible)

    This endpoint supports single image editing.
    For multi-image editing, use /v1/images/multi-edit
    """
    try:
        logger.info(f"Single image edit request: {prompt}")

        # Read uploaded image
        image_data = await image.read()
        input_image = Image.open(io.BytesIO(image_data)).convert("RGB")

        # Handle seed
        if seed == -1:
            seed = random.randint(0, 2**32 - 1)
        generator = torch.Generator(device="cuda").manual_seed(seed)

        logger.info(f"Processing with steps={num_inference_steps}, cfg={true_cfg_scale}, seed={seed}")

        # Generate edited image - MUST pass as list
        result = pipe(
            image=[input_image],  # Must be a list!
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=num_inference_steps,
            true_cfg_scale=true_cfg_scale,
            guidance_scale=guidance_scale,
            generator=generator,
            num_images_per_prompt=n
        ).images[0]

        # Save output
        filename = save_output(result, prefix="edit_single")
        logger.info(f"Saved result: {filename}")

        # Format response
        if response_format == "b64_json":
            b64_image = image_to_base64(result)
            return {
                "created": int(datetime.now().timestamp()),
                "data": [{"b64_json": b64_image}]
            }
        else:
            # URL format (default)
            return {
                "created": int(datetime.now().timestamp()),
                "data": [{"url": f"/outputs/{filename}"}]
            }

    except Exception as e:
        logger.error(f"Error in single image edit: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/images/multi-edit")
async def multi_image_edit(
    images: List[UploadFile] = File(...),
    prompt: str = Form(...),
    negative_prompt: str = Form(" "),
    num_inference_steps: int = Form(40),
    true_cfg_scale: float = Form(4.0),
    guidance_scale: float = Form(1.0),
    seed: int = Form(-1),
    response_format: str = Form("url")
):
    """
    Multi-image editing (1-3 images)

    Combines multiple images based on natural language instructions.

    Examples:
    - 2 images: "Person A and Person B standing together in a park"
    - 3 images: "Place person from image 1 in scene from image 2 holding object from image 3"

    Optimal: 1-3 images
    """
    try:
        num_images = len(images)
        logger.info(f"Multi-image edit request: {num_images} images, prompt: {prompt}")

        if num_images > 3:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum 3 images supported (received {num_images}). Optimal: 1-3 images."
            )

        # Load all images
        input_images = await load_images_from_uploads(images)

        # Handle seed
        if seed == -1:
            seed = random.randint(0, 2**32 - 1)
        generator = torch.Generator(device="cuda").manual_seed(seed)

        logger.info(f"Processing {num_images} images with steps={num_inference_steps}, cfg={true_cfg_scale}")

        # Multi-image editing
        result = pipe(
            image=input_images,  # List of images
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=num_inference_steps,
            true_cfg_scale=true_cfg_scale,
            guidance_scale=guidance_scale,
            generator=generator
        ).images[0]

        # Save output
        filename = save_output(result, prefix=f"edit_multi{num_images}")
        logger.info(f"Saved multi-image result: {filename}")

        # Format response
        if response_format == "b64_json":
            b64_image = image_to_base64(result)
            return {
                "created": int(datetime.now().timestamp()),
                "num_input_images": num_images,
                "data": [{"b64_json": b64_image}]
            }
        else:
            return {
                "created": int(datetime.now().timestamp()),
                "num_input_images": num_images,
                "data": [{"url": f"/outputs/{filename}"}]
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in multi-image edit: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/outputs/{filename}")
async def get_output_image(filename: str):
    """Serve generated images"""
    filepath = os.path.join("./outputs", filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(filepath, media_type="image/png")

@app.post("/v1/images/generations")
async def generate_image(request: dict):
    """
    Image generation endpoint (placeholder)

    Note: This API is optimized for image editing.
    For text-to-image generation, use Qwen-Image base model.
    """
    return JSONResponse(
        status_code=501,
        content={
            "error": {
                "message": "Image generation not available. This API is for image editing. Use /v1/images/edits (single) or /v1/images/multi-edit (multi-image).",
                "type": "not_implemented",
                "code": "model_not_available"
            }
        }
    )

@app.post("/v1/chat/completions")
async def chat_completion(request: dict):
    """
    Chat completions endpoint for Open WebUI compatibility

    Provides information about the image editing API.
    """
    messages = request.get("messages", [])

    response_text = """# Qwen-Image-Edit-2509 API

I'm an advanced image editing API with **multi-image support**!

## Capabilities

**Single Image Editing:**
- Natural language editing: "Change sky to sunset", "Make it anime style"
- No manual masking required - AI understands your intent
- Identity preservation (faces, products, logos)
- Style transfer, background replacement, object addition/removal

**Multi-Image Editing (1-3 images):**
- Person + Scene: Place people in different backgrounds
- Person + Person: Combine multiple people in one image
- Person + Product: Product placement with people
- Scene composition from multiple sources

## API Endpoints

**Single Image:**
```bash
POST /v1/images/edits
- Upload: 1 image
- Prompt: "Your editing instruction"
```

**Multi-Image:**
```bash
POST /v1/images/multi-edit
- Upload: 2-3 images
- Prompt: "Describe how to combine them"
```

## Example Prompts

**Single Image:**
- "Replace the sky with a dramatic sunset"
- "Transform into anime art style"
- "Change the car color to red"
- "Add flowers in the foreground"

**Multi-Image (2 images):**
- "Place the person from image 1 in the scene from image 2"
- "Combine these two people standing together"
- "Person holding the product, professional marketing photo"

**Multi-Image (3 images):**
- "Person from image 1 in scene from image 2 holding object from image 3"

## Parameters

- `num_inference_steps`: 20-100 (default: 40)
  - 20-30: Fast, good quality
  - 40-60: Excellent quality (recommended)
  - 80-100: Maximum quality

- `true_cfg_scale`: 1.0-10.0 (default: 4.0)
  - 3.5-5.0: Balanced, natural results
  - 6.0-8.0: Stronger prompt adherence

- `seed`: -1 for random, or specific number for reproducibility

For API documentation: http://localhost:8000/docs"""

    return {
        "id": f"chatcmpl-{random.randint(1000000, 9999999)}",
        "object": "chat.completion",
        "created": int(datetime.now().timestamp()),
        "model": "qwen-image-edit-2509",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": len(str(messages)),
            "completion_tokens": len(response_text),
            "total_tokens": len(str(messages)) + len(response_text)
        }
    }

# ============================================================
#  STARTUP
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  Starting API Server")
    print("=" * 60)
    print()
    print(f"API Server: http://{API_HOST}:{API_PORT}")
    print(f"API Docs: http://localhost:{API_PORT}/docs")
    print(f"OpenAPI JSON: http://localhost:{API_PORT}/openapi.json")
    print()
    print("Endpoints:")
    print(f"  - POST /v1/images/edits          (Single image)")
    print(f"  - POST /v1/images/multi-edit     (Multi-image: 1-3 images)")
    print(f"  - GET  /v1/models                (List models)")
    print(f"  - GET  /health                   (Health check)")
    print()
    print("Features:")
    print(f"  ✓ Multi-image editing (1-3 images)")
    print(f"  ✓ Natural language instructions")
    print(f"  ✓ Identity preservation")
    print(f"  ✓ OpenAI-compatible API")
    print()
    print("For Open WebUI:")
    print(f"  1. Add API URL: http://YOUR_SERVER_IP:{API_PORT}/v1")
    print(f"  2. No API key required")
    print(f"  3. Select model: qwen-image-edit-2509")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()

    uvicorn.run(
        app,
        host=API_HOST,
        port=API_PORT,
        log_level="info"
    )
