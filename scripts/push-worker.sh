# Push moonfish worker image to Artifact Registry
set -e

# Configuration
PROJECT_ID="moonfish-451215"
REGION="us-east4"
REPO_NAME="cloud-run-source-deploy"
IMAGE_NAME="moonfish/worker"
TAG="${1:-latest}"

# Full image path
FULL_IMAGE_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:${TAG}"

# Configure Docker for Artifact Registry
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet

# Check if image exists locally
if ! docker images ${FULL_IMAGE_PATH} --format "{{.Repository}}" | grep -q .; then
    echo "❌ Image not found: ${FULL_IMAGE_PATH}"
    echo "Run ./build.sh first"
    exit 1
fi

# Push the image
docker push "${FULL_IMAGE_PATH}"

echo ""
echo "Successfully pushed: ${FULL_IMAGE_PATH}"
echo ""
