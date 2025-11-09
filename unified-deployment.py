#!/usr/bin/env python3
"""
Unified Deployment Script for Mac → DGX Spark → HPC Lab
Orchestrates Qwen Image Edit deployment across the entire infrastructure
"""

import os
import sys
import json
import subprocess
import argparse
import logging
import time
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class SystemConfig:
    name: str
    type: str  # 'mac', 'dgx-spark', 'hpc'
    host: str
    gpu_count: int
    vram_total: str
    role: str
    priority: int

class UnifiedOrchestrator:
    def __init__(self):
        self.systems = self.load_system_configs()
        self.current_deployment = {}
        
    def load_system_configs(self) -> List[SystemConfig]:
        """Load all system configurations"""
        return [
            SystemConfig(
                name="mac-studio",
                type="mac", 
                host="localhost",
                gpu_count=0,
                vram_total="0GB",
                role="development_control",
                priority=1
            ),
            SystemConfig(
                name="dgx-spark",
                type="dgx-spark",
                host="dgx-spark.lab",  # Update with actual hostname
                gpu_count=2,  # Estimated, update when you research specs
                vram_total="160GB",  # Estimated H100 setup
                role="orchestration_gateway",
                priority=2
            ),
            SystemConfig(
                name="hpc-1",
                type="hpc",
                host="hpc-1.lab",
                gpu_count=2,
                vram_total="192GB",
                role="primary_inference",
                priority=3
            ),
            SystemConfig(
                name="hpc-2", 
                type="hpc",
                host="hpc-2.lab",
                gpu_count=3,
                vram_total="96GB",
                role="multi_user_serving",
                priority=4
            ),
            SystemConfig(
                name="hpc-3",
                type="hpc", 
                host="hpc-3.lab",
                gpu_count=1,
                vram_total="48GB",
                role="development_backup",
                priority=5
            )
        ]
    
    def detect_current_system(self) -> SystemConfig:
        """Detect which system we're running on"""
        import platform
        
        # Check if running on Mac
        if platform.system() == "Darwin":
            return next(s for s in self.systems if s.type == "mac")
        
        # Check for DGX Spark (would need actual detection logic)
        # For now, assume Linux with specific characteristics
        try:
            with open('/proc/version', 'r') as f:
                version_info = f.read().lower()
                if 'dgx' in version_info or 'spark' in version_info:
                    return next(s for s in self.systems if s.type == "dgx-spark")
        except:
            pass
        
        # Default to first HPC system if not Mac or Spark
        return next(s for s in self.systems if s.type == "hpc")
    
    def check_system_availability(self, system: SystemConfig) -> bool:
        """Check if a system is available"""
        if system.type == "mac":
            return True  # Always available locally
        
        try:
            # Ping test
            result = subprocess.run(['ping', '-c', '1', system.host], 
                                  capture_output=True, timeout=5)
            if result.returncode != 0:
                return False
            
            # SSH connectivity test
            result = subprocess.run(['ssh', '-o', 'ConnectTimeout=5', 
                                  system.host, 'echo "ok"'], 
                                  capture_output=True, timeout=10)
            return result.returncode == 0
            
        except Exception as e:
            logger.warning(f"Connectivity check failed for {system.name}: {e}")
            return False
    
    def get_system_resources(self, system: SystemConfig) -> Dict:
        """Get current resource utilization of a system"""
        if system.type == "mac":
            return {"cpu_percent": 0, "memory_percent": 0, "gpu_utilization": 0}
        
        try:
            # SSH and get GPU stats
            cmd = f"ssh {system.host} 'nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                gpu_data = []
                for line in lines:
                    if line.strip():
                        util, mem_used, mem_total = map(int, line.split(', '))
                        gpu_data.append({
                            "utilization": util,
                            "memory_used": mem_used,
                            "memory_total": mem_total,
                            "memory_percent": (mem_used / mem_total) * 100
                        })
                
                return {
                    "available": True,
                    "gpu_count": len(gpu_data),
                    "gpus": gpu_data,
                    "avg_utilization": sum(gpu["utilization"] for gpu in gpu_data) / len(gpu_data),
                    "avg_memory_percent": sum(gpu["memory_percent"] for gpu in gpu_data) / len(gpu_data)
                }
        except Exception as e:
            logger.warning(f"Failed to get resources for {system.name}: {e}")
        
        return {"available": False}
    
    def select_optimal_system(self, workload_type: str, model_size: str = "medium") -> SystemConfig:
        """Select the optimal system for a given workload"""
        
        # Define workload routing logic
        routing_rules = {
            "development": ["dgx-spark", "hpc-3"],
            "testing": ["dgx-spark", "hpc-1"], 
            "small_inference": ["dgx-spark", "hpc-3"],
            "medium_inference": ["dgx-spark", "hpc-1"],
            "large_inference": ["hpc-1", "dgx-spark"],
            "batch_processing": ["hpc-1", "hpc-2"],
            "multi_user": ["hpc-2", "dgx-spark"],
            "interactive": ["dgx-spark", "hpc-3"]
        }
        
        # Model size considerations
        if model_size == "large":
            preferred_systems = ["hpc-1"]  # Need maximum VRAM
        elif model_size == "medium":
            preferred_systems = ["dgx-spark", "hpc-1"]
        else:
            preferred_systems = ["dgx-spark", "hpc-3"]
        
        # Combine workload and model size preferences
        candidates = routing_rules.get(workload_type, ["dgx-spark"])
        
        # Filter by availability and resources
        available_systems = []
        for system_name in candidates:
            system = next(s for s in self.systems if s.name == system_name)
            if self.check_system_availability(system):
                resources = self.get_system_resources(system)
                if resources.get("available", False):
                    # Prefer systems with lower utilization
                    utilization_score = resources.get("avg_utilization", 100)
                    system.current_score = 100 - utilization_score
                    available_systems.append(system)
        
        if not available_systems:
            logger.warning("No systems available, falling back to DGX Spark")
            return next(s for s in self.systems if s.name == "dgx-spark")
        
        # Select best available system
        best_system = max(available_systems, key=lambda s: getattr(s, 'current_score', 0))
        logger.info(f"Selected {best_system.name} for {workload_type} workload")
        return best_system
    
    def deploy_to_system(self, system: SystemConfig, deployment_config: Dict) -> bool:
        """Deploy Qwen service to a specific system"""
        logger.info(f"Deploying to {system.name} ({system.role})")
        
        if system.type == "mac":
            return self.deploy_mac_control(deployment_config)
        elif system.type == "dgx-spark":
            return self.deploy_dgx_spark(deployment_config)
        else:  # HPC systems
            return self.deploy_hpc_system(system, deployment_config)
    
    def deploy_mac_control(self, config: Dict) -> bool:
        """Set up Mac as control interface"""
        logger.info("Setting up Mac Studio as control interface")
        
        # Setup AI Workbench project
        commands = [
            "ai-workbench create-project qwen-image-edit",
            "ai-workbench connect dgx-spark", 
            "ai-workbench setup-monitoring"
        ]
        
        for cmd in commands:
            try:
                result = subprocess.run(cmd.split(), capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning(f"Mac setup command failed: {cmd}")
            except Exception as e:
                logger.warning(f"Mac setup error: {e}")
        
        return True
    
    def deploy_dgx_spark(self, config: Dict) -> bool:
        """Deploy to DGX Spark system"""
        logger.info("Deploying to DGX Spark (orchestration hub)")
        
        # Use AI Workbench for deployment
        try:
            # Copy project files
            subprocess.run([
                "rsync", "-avz", "./", f"dgx-spark.lab:/data/qwen-project/"
            ], check=True)
            
            # Deploy via SSH
            deploy_cmd = """
            cd /data/qwen-project && \
            python code/scripts/deploy.py --env dgx-spark && \
            systemctl --user enable qwen-api && \
            systemctl --user start qwen-api
            """
            
            result = subprocess.run([
                "ssh", "dgx-spark.lab", deploy_cmd
            ], capture_output=True, text=True)
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"DGX Spark deployment failed: {e}")
            return False
    
    def deploy_hpc_system(self, system: SystemConfig, config: Dict) -> bool:
        """Deploy to HPC system"""
        logger.info(f"Deploying to {system.name}")
        
        try:
            # Copy project files
            subprocess.run([
                "rsync", "-avz", "./", f"{system.host}:/data/qwen-project/"
            ], check=True)
            
            # Deploy with system-specific config
            deploy_cmd = f"""
            cd /data/qwen-project && \
            python code/scripts/deploy.py --env {system.name} && \
            docker-compose -f docker-compose.{system.name}.yml up -d
            """
            
            result = subprocess.run([
                "ssh", system.host, deploy_cmd  
            ], capture_output=True, text=True)
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"HPC deployment to {system.name} failed: {e}")
            return False
    
    def create_unified_dashboard(self):
        """Create unified monitoring dashboard"""
        logger.info("Creating unified monitoring dashboard")
        
        dashboard_config = {
            "systems": [
                {
                    "name": system.name,
                    "host": system.host,
                    "type": system.type,
                    "api_endpoint": f"http://{system.host}:800{i}",
                    "ui_endpoint": f"http://{system.host}:300{i}"
                }
                for i, system in enumerate(self.systems[1:], 1)  # Skip Mac
            ]
        }
        
        # Save dashboard config
        with open("dashboard-config.json", "w") as f:
            json.dump(dashboard_config, f, indent=2)
        
        return dashboard_config
    
    def orchestrate_full_deployment(self, workload_types: List[str]) -> Dict:
        """Orchestrate deployment across all systems"""
        logger.info("Starting unified deployment across all systems")
        
        deployment_results = {}
        
        # 1. Setup Mac as control center
        mac_system = next(s for s in self.systems if s.type == "mac")
        deployment_results["mac"] = self.deploy_to_system(mac_system, {})
        
        # 2. Deploy to optimal systems for each workload type
        for workload in workload_types:
            optimal_system = self.select_optimal_system(workload)
            
            config = {
                "workload_type": workload,
                "system_role": optimal_system.role
            }
            
            result = self.deploy_to_system(optimal_system, config)
            deployment_results[f"{workload}_{optimal_system.name}"] = result
        
        # 3. Setup unified monitoring
        dashboard_config = self.create_unified_dashboard()
        deployment_results["dashboard"] = dashboard_config
        
        return deployment_results

def main():
    parser = argparse.ArgumentParser(description="Unified AI Lab Deployment")
    parser.add_argument("--workloads", nargs="+", 
                       default=["development", "testing", "production"],
                       help="Workload types to deploy")
    parser.add_argument("--target-system", 
                       choices=["mac", "dgx-spark", "hpc-1", "hpc-2", "hpc-3", "auto"],
                       default="auto",
                       help="Target system for deployment")
    parser.add_argument("--monitor-only", action="store_true",
                       help="Only setup monitoring, don't deploy")
    
    args = parser.parse_args()
    
    orchestrator = UnifiedOrchestrator()
    
    if args.monitor_only:
        dashboard = orchestrator.create_unified_dashboard()
        logger.info("Monitoring dashboard created")
        print(json.dumps(dashboard, indent=2))
        return
    
    if args.target_system == "auto":
        # Full orchestrated deployment
        results = orchestrator.orchestrate_full_deployment(args.workloads)
    else:
        # Deploy to specific system
        target = next(s for s in orchestrator.systems if s.name == args.target_system)
        results = orchestrator.deploy_to_system(target, {"workloads": args.workloads})
    
    # Print results
    logger.info("Deployment completed!")
    print(json.dumps(results, indent=2, default=str))

if __name__ == "__main__":
    main()