#!/bin/bash
# Build moonfish worker Docker image
set -e

# Configuration
PROJECT_ID="moonfish-451215"
REGION="us-east4"
REPO_NAME="cloud-run-source-deploy"
IMAGE_NAME="moonfish/worker"
TAG="${1:-latest}"

# Full image path
FULL_IMAGE_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:${TAG}"

# Navigate to project root
cd "$(dirname "$0")/.."

# Enable BuildKit for faster builds
export DOCKER_BUILDKIT=1

# Build the image
docker build --platform linux/amd64 -f worker.Dockerfile -t "${FULL_IMAGE_PATH}" .

# Show image info
echo ""
echo "Build complete!"
echo ""
