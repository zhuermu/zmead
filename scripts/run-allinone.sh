#!/bin/bash
# Build and run AAE all-in-one container

set -e

IMAGE_NAME="aae-allinone"
CONTAINER_NAME="aae-app"

echo "Building AAE all-in-one image..."
docker build -f Dockerfile.allinone -t $IMAGE_NAME .

echo "Stopping existing container..."
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

echo "Starting container..."
docker run -d \
  --name $CONTAINER_NAME \
  --restart unless-stopped \
  -p 3000:3000 \
  -p 8000:8000 \
  -p 8001:8001 \
  --env-file backend/.env \
  --env-file ai-orchestrator/.env \
  --env-file frontend/.env.local \
  $IMAGE_NAME

echo "Container started. Checking health..."
sleep 10
docker logs $CONTAINER_NAME --tail 20

echo ""
echo "Services:"
echo "  Frontend:       http://localhost:3000"
echo "  Backend:        http://localhost:8000"
echo "  AI Orchestrator: http://localhost:8001"
