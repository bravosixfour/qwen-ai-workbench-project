#!/bin/bash
set -e

echo "Starting Qwen Image API Server..."
echo "Configuration:"
echo "  - Workers: ${GUNICORN_WORKERS}"
echo "  - Threads: ${GUNICORN_THREADS}"
echo "  - Port: ${API_PORT}"
echo "  - Redis: ${REDIS_HOST}:${REDIS_PORT}"

# Wait for Redis to be ready
echo "Waiting for Redis..."
for i in {1..30}; do
    if python3 -c "import redis; r = redis.Redis('${REDIS_HOST}', ${REDIS_PORT}); r.ping()" 2>/dev/null; then
        echo "Redis is ready!"
        break
    fi
    echo "Waiting for Redis... ($i/30)"
    sleep 2
done

# Start Gunicorn with the API
exec gunicorn api_server:app \
    --config /app/config/gunicorn_config.py \
    --access-logfile - \
    --error-logfile - \
    --log-level ${LOG_LEVEL} \
    --bind 0.0.0.0:${API_PORT}
