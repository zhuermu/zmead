#!/usr/bin/env python3
"""
Script to apply CORS configuration to GCS buckets using Python SDK
Usage: python apply_gcs_cors.py
"""

from google.cloud import storage
import json
import os
import sys

# Add parent directory to path to import app config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.config import get_settings

# Load settings from config
settings = get_settings()
TEMP_BUCKET = settings.gcs_bucket_uploads_temp
PERMANENT_BUCKET = settings.gcs_bucket_uploads

# CORS configuration
CORS_CONFIG = [
    {
        "origin": ["http://localhost:3000", "http://localhost:3001"],
        "method": ["GET", "PUT", "POST", "HEAD"],
        "responseHeader": [
            "Content-Type",
            "Content-Length",
            "Content-Range",
            "Content-Encoding",
            "x-goog-resumable",
        ],
        "maxAgeSeconds": 3600,
    }
]


def apply_cors_to_bucket(bucket_name: str, cors_config: list):
    """Apply CORS configuration to a GCS bucket"""
    try:
        # Initialize storage client
        storage_client = storage.Client()

        # Get bucket
        bucket = storage_client.bucket(bucket_name)

        # Set CORS configuration
        bucket.cors = cors_config
        bucket.patch()

        print(f"✓ CORS configured for bucket: {bucket_name}")
        return True
    except Exception as e:
        print(f"✗ Error configuring CORS for {bucket_name}: {e}")
        return False


def main():
    print("Applying CORS configuration to GCS buckets...")
    print(f"CORS config: {json.dumps(CORS_CONFIG, indent=2)}")
    print("")

    # Check for GCS credentials
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and not os.getenv("GCS_CREDENTIALS_PATH"):
        print("Warning: No GCS credentials environment variable found.")
        print("Make sure GOOGLE_APPLICATION_CREDENTIALS or GCS_CREDENTIALS_PATH is set.")
        print("")

    # Apply CORS to both buckets
    success_temp = apply_cors_to_bucket(TEMP_BUCKET, CORS_CONFIG)
    print("")

    success_perm = apply_cors_to_bucket(PERMANENT_BUCKET, CORS_CONFIG)
    print("")

    if success_temp and success_perm:
        print("✓ All done! CORS configuration applied successfully.")
    else:
        print("✗ Some buckets failed to configure. Please check the errors above.")
        exit(1)


if __name__ == "__main__":
    main()
