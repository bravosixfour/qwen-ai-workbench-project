import os
from celery import Celery
from kombu import Queue, Exchange
import redis
from redis import ConnectionPool

# Redis configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)

# Create Redis connection pool
redis_pool = ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    max_connections=100,
    socket_keepalive=True,
    socket_keepalive_options={
        1: 1,  # TCP_KEEPIDLE
        2: 1,  # TCP_KEEPINTVL
        3: 5,  # TCP_KEEPCNT
    }
)

# Redis client
redis_client = redis.Redis(connection_pool=redis_pool)

# Celery configuration
app = Celery('qwen_api')

# Configure Celery
app.conf.update(
    broker_url=f'redis://{":" + REDIS_PASSWORD + "@" if REDIS_PASSWORD else ""}{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}',
    result_backend=f'redis://{":" + REDIS_PASSWORD + "@" if REDIS_PASSWORD else ""}{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=600,  # 10 minutes hard limit
    task_soft_time_limit=540,  # 9 minutes soft limit
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks to prevent memory leaks
    worker_disable_rate_limits=False,
    
    # Connection pool settings
    broker_pool_limit=50,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_compression='gzip',
    
    # Queue configuration
    task_default_queue='qwen_image_queue',
    task_default_exchange='qwen_image',
    task_default_exchange_type='direct',
    task_default_routing_key='qwen_image',
    
    task_queues=(
        Queue('qwen_image_queue', Exchange('qwen_image'), routing_key='qwen_image'),
        Queue('priority_queue', Exchange('priority'), routing_key='priority', priority=10),
    ),
    
    # Route specific tasks to specific queues
    task_routes={
        'qwen_api.tasks.process_image': {'queue': 'qwen_image_queue'},
        'qwen_api.tasks.priority_process': {'queue': 'priority_queue'},
    }
)

# Import tasks
from . import tasks
