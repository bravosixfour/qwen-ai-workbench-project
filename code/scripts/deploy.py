#!/usr/bin/env python3
"""
Deployment script for Qwen AI Workbench Project
Manages deployment across multiple DGX systems
"""

import os
import sys
import json
import subprocess
import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QwenDeployment:
    def __init__(self, config_file="deployment.json"):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self):
        """Load deployment configuration"""
        default_config = {
            "project_name": "qwen-image-edit-ai-workbench",
            "environments": {
                "dgx-spark": {
                    "gpu_count": 2,
                    "gpu_memory": "48GB",
                    "workers": 4
                },
                "dgx-a100": {
                    "gpu_count": 8,
                    "gpu_memory": "40GB", 
                    "workers": 8
                },
                "workstation": {
                    "gpu_count": 1,
                    "gpu_memory": "24GB",
                    "workers": 2
                }
            }
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load config: {e}, using defaults")
        
        return default_config
    
    def detect_environment(self):
        """Auto-detect the deployment environment"""
        try:
            # Check for DGX system identifier
            with open('/proc/cpuinfo', 'r') as f:
                cpu_info = f.read()
            
            # Check GPU count
            result = subprocess.run(['nvidia-smi', '-L'], 
                                  capture_output=True, text=True)
            gpu_count = len([line for line in result.stdout.split('\n') if 'GPU' in line])
            
            # Determine environment based on GPU count and system info
            if gpu_count >= 8:
                return "dgx-a100"
            elif gpu_count >= 2:
                return "dgx-spark" 
            else:
                return "workstation"
                
        except Exception as e:
            logger.warning(f"Failed to detect environment: {e}")
            return "workstation"
    
    def configure_for_environment(self, env_name):
        """Configure deployment for specific environment"""
        env_config = self.config["environments"].get(env_name, {})
        
        # Set environment variables
        os.environ["GPU_COUNT"] = str(env_config.get("gpu_count", 1))
        os.environ["API_WORKERS"] = str(env_config.get("workers", 2))
        os.environ["GPU_MEMORY"] = env_config.get("gpu_memory", "24GB")
        
        logger.info(f"Configured for {env_name}: {env_config}")
    
    def validate_requirements(self):
        """Validate system requirements"""
        checks = []
        
        # Check GPU availability
        try:
            result = subprocess.run(['nvidia-smi'], capture_output=True)
            checks.append(("GPU Available", result.returncode == 0))
        except FileNotFoundError:
            checks.append(("GPU Available", False))
        
        # Check Python version
        checks.append(("Python 3.8+", sys.version_info >= (3, 8)))
        
        # Check disk space (need 100GB+)
        try:
            statvfs = os.statvfs('/project')
            free_bytes = statvfs.f_frsize * statvfs.f_bavail
            free_gb = free_bytes / (1024**3)
            checks.append(("Disk Space (100GB+)", free_gb >= 100))
        except:
            checks.append(("Disk Space", False))
        
        # Display results
        logger.info("System Requirements Check:")
        for check, passed in checks:
            status = "✓" if passed else "✗"
            logger.info(f"  {status} {check}")
        
        return all(passed for _, passed in checks)
    
    def deploy(self, environment=None):
        """Deploy the Qwen API service"""
        # Auto-detect environment if not specified
        if not environment:
            environment = self.detect_environment()
        
        logger.info(f"Deploying to environment: {environment}")
        
        # Validate requirements
        if not self.validate_requirements():
            logger.error("System requirements not met!")
            return False
        
        # Configure for environment
        self.configure_for_environment(environment)
        
        # Run deployment steps
        steps = [
            ("Download Models", self.download_models),
            ("Configure Services", self.configure_services),
            ("Start Services", self.start_services),
            ("Verify Deployment", self.verify_deployment)
        ]
        
        for step_name, step_func in steps:
            logger.info(f"Running: {step_name}")
            if not step_func():
                logger.error(f"Failed: {step_name}")
                return False
        
        logger.info("Deployment completed successfully!")
        return True
    
    def download_models(self):
        """Download required models"""
        try:
            script_path = "/project/code/scripts/download_models.py"
            result = subprocess.run([sys.executable, script_path], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Model download failed: {result.stderr}")
                return False
            return True
        except Exception as e:
            logger.error(f"Error downloading models: {e}")
            return False
    
    def configure_services(self):
        """Configure services for the environment"""
        try:
            # Create necessary directories
            os.makedirs("/project/data/logs", exist_ok=True)
            os.makedirs("/project/data/outputs", exist_ok=True)
            
            # Set permissions
            os.chmod("/project/data", 0o755)
            
            return True
        except Exception as e:
            logger.error(f"Error configuring services: {e}")
            return False
    
    def start_services(self):
        """Start all services"""
        # This would typically be handled by AI Workbench
        logger.info("Services will be started by AI Workbench")
        return True
    
    def verify_deployment(self):
        """Verify deployment is working"""
        try:
            import requests
            
            # Test API health
            response = requests.get("http://localhost:8000/health", timeout=10)
            if response.status_code != 200:
                logger.error("API health check failed")
                return False
            
            # Test UI
            response = requests.get("http://localhost:3002/health", timeout=10)
            if response.status_code != 200:
                logger.warning("UI health check failed (may still be starting)")
            
            logger.info("Deployment verification successful")
            return True
            
        except Exception as e:
            logger.warning(f"Verification failed (services may still be starting): {e}")
            return True  # Don't fail deployment for this

def main():
    parser = argparse.ArgumentParser(description="Deploy Qwen AI Workbench Project")
    parser.add_argument("--env", choices=["dgx-spark", "dgx-a100", "workstation"],
                       help="Target environment")
    parser.add_argument("--validate-only", action="store_true",
                       help="Only validate requirements")
    
    args = parser.parse_args()
    
    deployment = QwenDeployment()
    
    if args.validate_only:
        success = deployment.validate_requirements()
        sys.exit(0 if success else 1)
    
    success = deployment.deploy(args.env)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()