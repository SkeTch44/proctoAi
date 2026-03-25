#!/bin/bash
# WSL Redis Startup Script
# Run this in WSL to start Redis on the correct port

echo "=========================================="
echo "Starting Redis for Smoke Test"
echo "=========================================="

# Check if Redis is already running on port 6380
if pgrep -f "redis-server.*6380" > /dev/null; then
    echo "✅ Redis is already running on port 6380"
    redis-cli -h 172.26.79.185 -p 6380 ping
    exit 0
fi

echo "Starting Redis server on 172.26.79.185:6380..."

# Start Redis
redis-server --port 6380 --bind 172.26.79.185 --daemonize yes

# Wait a moment for startup
sleep 1

# Verify it's running
if redis-cli -h 172.26.79.185 -p 6380 ping > /dev/null 2>&1; then
    echo "✅ Redis started successfully!"
    echo ""
    echo "Redis is now listening on: 172.26.79.185:6380"
    echo ""
    echo "To test connection:"
    echo "  redis-cli -h 172.26.79.185 -p 6380 ping"
    echo ""
    echo "To stop Redis:"
    echo "  redis-cli -h 172.26.79.185 -p 6380 shutdown"
else
    echo "❌ Failed to start Redis"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check if Redis is installed: redis-server --version"
    echo "2. Check if port 6380 is already in use: netstat -tuln | grep 6380"
    echo "3. Check Redis logs: tail -f /var/log/redis/redis-server.log"
    exit 1
fi
