#!/bin/bash
# Post-build script for Qwen AI Workbench Project

echo "=== Qwen AI Workbench Post-Build Script ==="

# Install Python packages
echo "Installing Python packages..."
pip install -r requirements.txt

# Setup Mango Editor
echo "Setting up Mango Editor..."
cd /project/code/editor && npm install

# Download models (if HF_TOKEN is set)
if [ ! -z "$HF_TOKEN" ]; then
    echo "Downloading Qwen models..."
    python /project/code/scripts/download_models.py
else
    echo "Warning: HF_TOKEN not set, skipping model download"
fi

# Configure Redis
echo "Configuring Redis..."
mkdir -p /project/data/redis

# Set permissions
echo "Setting permissions..."
chmod -R 755 /project/code
chmod -R 777 /project/data

echo "Post-build complete! Project ready for deployment."