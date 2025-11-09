import multiprocessing
import os

# Server Socket
bind = f"0.0.0.0:{os.getenv('API_PORT', '8000')}"
backlog = 2048

# Worker Processes
# For CPU-intensive tasks, use 2-4 workers per core
# For I/O-intensive tasks (like our image API), we can use more
workers = int(os.getenv('GUNICORN_WORKERS', min(multiprocessing.cpu_count() * 2 + 1, 16)))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000  # Restart workers after this many requests to prevent memory leaks
max_requests_jitter = 50  # Randomize the restart to avoid all workers restarting simultaneously
timeout = 300  # 5 minutes for long-running image processing
graceful_timeout = 30
keepalive = 5

# Thread pooling for sync workers (not used with uvicorn worker)
threads = int(os.getenv('GUNICORN_THREADS', 4))

# Process Naming
proc_name = 'qwen-image-api'

# Logging
accesslog = '-'
errorlog = '-'
loglevel = os.getenv('LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Stats
statsd_host = os.getenv('STATSD_HOST', None)
if statsd_host:
    statsd_prefix = 'qwen_api'

# Server Mechanics
daemon = False
pidfile = None
user = None
group = None
tmp_upload_dir = None

# SSL (optional, configure if needed)
# keyfile = '/path/to/keyfile'
# certfile = '/path/to/certfile'

# Worker lifecycle hooks
def on_starting(server):
    server.log.info("Starting Qwen Image API Server")
    server.log.info(f"Master process PID: {os.getpid()}")

def on_reload(server):
    server.log.info("Reloading Qwen Image API Server")

def when_ready(server):
    server.log.info("Qwen Image API Server is ready. Listening on: %s", server.address)

def worker_int(worker):
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def pre_exec(server):
    server.log.info("Forked child, re-executing.")

def on_exit(server):
    server.log.info("Shutting down Qwen Image API Server")
