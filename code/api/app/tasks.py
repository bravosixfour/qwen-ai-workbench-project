from celery import Task
from celery_app import app, redis_client
import json
import time
import logging

logger = logging.getLogger(__name__)

class ImageProcessingTask(Task):
    """Base task with connection pooling and retry logic"""
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3}
    retry_backoff = True
    retry_jitter = True

@app.task(base=ImageProcessingTask, bind=True, name='qwen_api.tasks.process_image')
def process_image(self, request_id, image_data, prompt, **kwargs):
    """
    Async task to process image editing requests
    """
    try:
        # Store task status in Redis
        redis_client.hset(f"task:{request_id}", mapping={
            "status": "processing",
            "started_at": time.time(),
            "worker": self.request.hostname
        })
        
        # Import here to avoid circular dependencies
        from api_server import process_image_edit
        
        # Process the image
        result = process_image_edit(image_data, prompt, **kwargs)
        
        # Store result in Redis with expiration
        redis_client.hset(f"task:{request_id}", mapping={
            "status": "completed",
            "completed_at": time.time(),
            "result": json.dumps(result)
        })
        redis_client.expire(f"task:{request_id}", 3600)  # Expire after 1 hour
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing image {request_id}: {str(e)}")
        redis_client.hset(f"task:{request_id}", mapping={
            "status": "failed",
            "error": str(e),
            "failed_at": time.time()
        })
        raise

@app.task(bind=True, name='qwen_api.tasks.priority_process')
def priority_process_image(self, request_id, image_data, prompt, **kwargs):
    """
    High-priority image processing task
    """
    return process_image(request_id, image_data, prompt, **kwargs)

@app.task(name='qwen_api.tasks.get_task_status')
def get_task_status(request_id):
    """
    Get the status of a processing task
    """
    task_data = redis_client.hgetall(f"task:{request_id}")
    if not task_data:
        return {"status": "not_found"}
    
    return {k.decode('utf-8'): v.decode('utf-8') for k, v in task_data.items()}

@app.task(name='qwen_api.tasks.cleanup_old_tasks')
def cleanup_old_tasks():
    """
    Periodic task to cleanup old task data
    """
    pattern = "task:*"
    current_time = time.time()
    cleaned = 0
    
    for key in redis_client.scan_iter(match=pattern):
        task_data = redis_client.hgetall(key)
        if task_data:
            created_at = float(task_data.get(b'started_at', 0))
            # Delete tasks older than 24 hours
            if current_time - created_at > 86400:
                redis_client.delete(key)
                cleaned += 1
    
    logger.info(f"Cleaned up {cleaned} old tasks")
    return cleaned
