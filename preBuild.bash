#!/bin/bash
# Pre-build script for Qwen AI Workbench Project

echo "=== Qwen AI Workbench Pre-Build Script ==="

# Install system dependencies
echo "Installing system dependencies..."
apt-get update && apt-get install -y \
    redis-server \
    nodejs \
    npm \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1

# Setup model cache directory
echo "Setting up model cache..."
mkdir -p /project/models
mkdir -p /project/data/{outputs,logs,cache}

# Set environment variables
echo "Setting environment variables..."
echo 'export HF_HOME=/project/models' >> ~/.bashrc
echo 'export TRANSFORMERS_CACHE=/project/models' >> ~/.bashrc

echo "Pre-build complete!"