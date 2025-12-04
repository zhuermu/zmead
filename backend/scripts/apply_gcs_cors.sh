#!/bin/bash

# Script to apply CORS configuration to GCS buckets
# Usage: ./apply_gcs_cors.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORS_CONFIG="$SCRIPT_DIR/configure_gcs_cors.json"

# Load .env file if it exists
if [ -f "$SCRIPT_DIR/../.env" ]; then
    echo "Loading environment variables from .env..."
    set -a
    source <(grep -v '^#' "$SCRIPT_DIR/../.env" | grep -v '^$')
    set +a
fi

# Bucket names from environment variables or defaults
TEMP_BUCKET="${GCS_BUCKET_UPLOADS_TEMP:-aae-user-uploads-temp}"
PERMANENT_BUCKET="${GCS_BUCKET_UPLOADS:-aae-user-uploads}"

echo "Applying CORS configuration to GCS buckets..."
echo "CORS config file: $CORS_CONFIG"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI is not installed."
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Apply CORS to temporary bucket
echo "Configuring CORS for bucket: $TEMP_BUCKET"
gcloud storage buckets update "gs://$TEMP_BUCKET" \
    --cors-file="$CORS_CONFIG"

echo "✓ CORS configured for $TEMP_BUCKET"
echo ""

# Apply CORS to permanent bucket
echo "Configuring CORS for bucket: $PERMANENT_BUCKET"
gcloud storage buckets update "gs://$PERMANENT_BUCKET" \
    --cors-file="$CORS_CONFIG"

echo "✓ CORS configured for $PERMANENT_BUCKET"
echo ""

echo "✓ All done! CORS configuration applied successfully."
echo ""
echo "To verify the configuration, run:"
echo "  gcloud storage buckets describe gs://$TEMP_BUCKET --format='json(cors_config)'"
echo "  gcloud storage buckets describe gs://$PERMANENT_BUCKET --format='json(cors_config)'"
