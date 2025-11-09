#!/usr/bin/env python3
"""
Model download script for Qwen Image Edit AI Workbench Project
Downloads required models to the project models directory
"""

import os
import sys
from pathlib import Path
from huggingface_hub import hf_hub_download, login, snapshot_download
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen-Image-Edit-2509")
HF_HOME = os.getenv("HF_HOME", "/project/models")
HF_TOKEN = os.getenv("HF_TOKEN")

def download_qwen_model():
    """Download the Qwen Image Edit model"""
    logger.info(f"Downloading model: {MODEL_NAME}")
    logger.info(f"Target directory: {HF_HOME}")
    
    # Ensure models directory exists
    os.makedirs(HF_HOME, exist_ok=True)
    
    # Login if token is provided
    if HF_TOKEN:
        logger.info("Logging in to HuggingFace...")
        login(token=HF_TOKEN)
    else:
        logger.warning("No HF_TOKEN provided - may fail for gated models")
    
    try:
        # Download the entire model
        logger.info("Starting model download...")
        local_dir = os.path.join(HF_HOME, MODEL_NAME.split("/")[-1])
        
        snapshot_download(
            repo_id=MODEL_NAME,
            local_dir=local_dir,
            cache_dir=HF_HOME,
            local_files_only=False,
            resume_download=True
        )
        
        logger.info(f"Model successfully downloaded to: {local_dir}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to download model: {e}")
        return False

def verify_model():
    """Verify model files are present"""
    model_path = os.path.join(HF_HOME, MODEL_NAME.split("/")[-1])
    
    required_files = [
        "config.json",
        "pytorch_model.bin",  # or model.safetensors
        "tokenizer.json"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(os.path.join(model_path, file)):
            # Check for .safetensors alternative
            if file == "pytorch_model.bin":
                if not os.path.exists(os.path.join(model_path, "model.safetensors")):
                    missing_files.append(file)
            else:
                missing_files.append(file)
    
    if missing_files:
        logger.warning(f"Missing model files: {missing_files}")
        return False
    
    logger.info("Model verification complete - all required files present")
    return True

def main():
    """Main execution function"""
    logger.info("=== Qwen Model Download Script ===")
    
    # Check if model already exists
    model_path = os.path.join(HF_HOME, MODEL_NAME.split("/")[-1])
    if os.path.exists(model_path) and verify_model():
        logger.info("Model already exists and verified")
        return 0
    
    # Download model
    if download_qwen_model():
        if verify_model():
            logger.info("Model download and verification successful!")
            return 0
        else:
            logger.error("Model verification failed")
            return 1
    else:
        logger.error("Model download failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())