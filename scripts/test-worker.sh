#!/bin/bash
# Test the worker image locally
set -e

# Configuration
PROJECT_ID="moonfish-451215"
REGION="us-east4"
REPO_NAME="cloud-run-source-deploy"
IMAGE_NAME="moonfish/worker"
TAG="${1:-latest}"

# Full image path
FULL_IMAGE_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:${TAG}"

# 1. Test: Check if ffmpeg is installed and working
echo "Testing ffmpeg installation..."
docker run --rm --platform linux/amd64 ${FULL_IMAGE_PATH} ffmpeg -version
echo "✓ ffmpeg installation test passed!"
echo ""

# 2. Test: Check Python and imports
echo "Testing Python environment..."
docker run --rm --platform linux/amd64 ${FULL_IMAGE_PATH} python -c "

import sys
print(f'Python version: {sys.version}')
print('Testing imports...')
try:
    import pydub
    print('✓ Pydub imported successfully')
except ImportError as e:
    print(f'✗ Pydub import error: {e}')
    sys.exit(1)
"
echo "Python environment test completed!"
echo ""

# 3. Test: Verify user permissions
echo "Testing user permissions..."
docker run --rm --platform linux/amd64 ${FULL_IMAGE_PATH} sh -c "
echo 'User info:' && whoami && id
echo 'Working directory permissions:' && ls -la /app/ | head -5
"
echo "User permissions verified!"
echo ""

# 4. Test: Verify environment variables
echo "Testing environment setup..."
docker run --rm --platform linux/amd64 ${FULL_IMAGE_PATH} env | grep -E "(PYTHONUNBUFFERED|PATH)" || true
echo "Environment variables checked!"
echo ""

echo "All tests completed! Your image is ready to push."
echo "Run: ./push.sh ${TAG}"
