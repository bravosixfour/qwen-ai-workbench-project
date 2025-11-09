#!/usr/bin/env python3
"""
Health check script for monitoring API and dependencies
"""
import sys
import requests
import redis
import json
from datetime import datetime

def check_api_health(host="localhost", port=8000):
    """Check if API is responding"""
    try:
        response = requests.get(f"http://{host}:{port}/health", timeout=5)
        return response.status_code == 200, response.json()
    except Exception as e:
        return False, str(e)

def check_redis_health(host="redis", port=6379):
    """Check if Redis is accessible"""
    try:
        r = redis.Redis(host, port)
        r.ping()
        info = r.info()
        return True, {
            "connected_clients": info.get("connected_clients"),
            "used_memory_human": info.get("used_memory_human"),
            "uptime_in_seconds": info.get("uptime_in_seconds")
        }
    except Exception as e:
        return False, str(e)

def check_queue_health(host="redis", port=6379):
    """Check Celery queue status"""
    try:
        r = redis.Redis(host, port)
        # Check queue lengths
        queues = {
            "qwen_image_queue": r.llen("qwen_image_queue"),
            "priority_queue": r.llen("priority_queue")
        }
        return True, queues
    except Exception as e:
        return False, str(e)

def main():
    health_status = {
        "timestamp": datetime.utcnow().isoformat(),
        "status": "healthy",
        "checks": {}
    }
    
    # Check API
    api_ok, api_info = check_api_health()
    health_status["checks"]["api"] = {
        "status": "up" if api_ok else "down",
        "info": api_info
    }
    
    # Check Redis
    redis_ok, redis_info = check_redis_health()
    health_status["checks"]["redis"] = {
        "status": "up" if redis_ok else "down",
        "info": redis_info
    }
    
    # Check queues
    queue_ok, queue_info = check_queue_health()
    health_status["checks"]["queues"] = {
        "status": "up" if queue_ok else "down",
        "info": queue_info
    }
    
    # Overall status
    if not all([api_ok, redis_ok, queue_ok]):
        health_status["status"] = "unhealthy"
        print(json.dumps(health_status, indent=2))
        sys.exit(1)
    
    print(json.dumps(health_status, indent=2))
    sys.exit(0)

if __name__ == "__main__":
    main()
