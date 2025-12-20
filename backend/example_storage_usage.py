"""Example usage of the storage backend factory.

This demonstrates how to use both GCS and S3 storage backends
with the same interface.
"""

from app.core.storage import get_storage_backend


def example_upload_to_gcs():
    """Example: Upload a file to Google Cloud Storage."""
    # Get GCS storage for creatives
    storage = get_storage_backend("creatives", "gcs")
    
    # Upload a file
    file_data = b"Hello, GCS!"
    file_key = "examples/test.txt"
    
    result = storage.upload_file(
        key=file_key,
        data=file_data,
        content_type="text/plain",
    )
    print(f"Uploaded to GCS: {result}")
    
    # Get CDN URL
    cdn_url = storage.get_cdn_url(file_key)
    print(f"CDN URL: {cdn_url}")
    
    # Generate presigned download URL
    download_url = storage.generate_presigned_download_url(file_key, expires_in=3600)
    print(f"Download URL: {download_url}")


def example_upload_to_s3():
    """Example: Upload a file to Amazon S3."""
    # Get S3 storage for creatives
    storage = get_storage_backend("creatives", "s3")
    
    # Upload a file
    file_data = b"Hello, S3!"
    file_key = "examples/test.txt"
    
    result = storage.upload_file(
        key=file_key,
        data=file_data,
        content_type="text/plain",
    )
    print(f"Uploaded to S3: {result}")
    
    # Get CDN URL (CloudFront if configured)
    cdn_url = storage.get_cdn_url(file_key)
    print(f"CDN URL: {cdn_url}")
    
    # Generate presigned download URL
    download_url = storage.generate_presigned_download_url(file_key, expires_in=3600)
    print(f"Download URL: {download_url}")


def example_switch_providers():
    """Example: Switch between providers dynamically."""
    # Configuration-driven provider selection
    use_aws = True  # This could come from environment or user preference
    
    provider = "s3" if use_aws else "gcs"
    storage = get_storage_backend("uploads", provider)
    
    print(f"Using {provider.upper()} storage")
    
    # Same interface works for both providers
    file_key = "user-uploads/document.pdf"
    
    # Generate presigned upload URL
    upload_info = storage.generate_presigned_upload_url(
        key=file_key,
        content_type="application/pdf",
        expires_in=3600,
    )
    print(f"Upload URL: {upload_info['url']}")
    
    # Check if file exists
    exists = storage.file_exists(file_key)
    print(f"File exists: {exists}")


def example_list_files():
    """Example: List files with prefix filter."""
    # Works with both GCS and S3
    for provider in ["gcs", "s3"]:
        storage = get_storage_backend("creatives", provider)
        
        print(f"\nListing files in {provider.upper()}:")
        files = storage.list_files(prefix="examples/", max_results=10)
        
        for file_info in files:
            print(f"  - {file_info['name']} ({file_info['size']} bytes)")


if __name__ == "__main__":
    print("=" * 60)
    print("Storage Backend Usage Examples")
    print("=" * 60)
    
    print("\n1. Upload to GCS:")
    print("-" * 60)
    example_upload_to_gcs()
    
    print("\n2. Upload to S3:")
    print("-" * 60)
    example_upload_to_s3()
    
    print("\n3. Dynamic provider switching:")
    print("-" * 60)
    example_switch_providers()
    
    print("\n4. List files:")
    print("-" * 60)
    example_list_files()
    
    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)
