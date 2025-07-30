#!/bin/bash

# Build and push moonfish worker to Artifact Registry
set -e  # Exit on any error

# Configuration
PROJECT_ID="moonfish-451215"
REGION="us-east4"
REPO_NAME="cloud-run-source-deploy"
IMAGE_NAME="moonfish/worker"
TAG="${1:-latest}"  # Use first argument as tag, default to 'latest'

# Full image path
FULL_IMAGE_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:${TAG}"

echo "🔨 Building worker image..."
# Build from project root, regardless of where script is run from
cd "$(dirname "$0")/.."
docker build -f worker.Dockerfile -t "${FULL_IMAGE_PATH}" .

echo "Pushing to Artifact Registry..."
docker push "${FULL_IMAGE_PATH}"

echo "Successfully pushed: ${FULL_IMAGE_PATH}"
echo ""
echo "To deploy this image:"
echo "  gcloud run deploy moonfish-worker --image=${FULL_IMAGE_PATH}"
