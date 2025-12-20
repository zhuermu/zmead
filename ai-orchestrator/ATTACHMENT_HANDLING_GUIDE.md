# Attachment Handling & Media Generation Guide

**Last Updated**: 2025-12-20
**Status**: ✅ Production Ready

## Overview

This document provides a comprehensive guide to attachment handling and media generation in the AI Orchestrator, covering the complete flow from tool execution to frontend display.

## Architecture

### Unified Attachment Flow

```
Tool Execution (generate_image_tool / generate_video_tool)
    ↓
Upload to S3 (us-west-2region)
    ↓
Yield observation event with attachments field
    ↓
Strands Agent captures via tool_stream_event
    ↓
SSE handler forwards attachments to frontend
    ↓
Frontend receives observation event + attachments
    ↓
AttachmentDisplay component fetches presigned URLs
    ↓
Display images/videos in chat interface
```

### Key Components

1. **Tool Layer** (`app/tools/creative_tools.py`)
   - `GenerateImageTool`: Bedrock Stable Diffusion / SageMaker Qwen-Image
   - `GenerateVideoTool`: SageMaker Wan2.2 / Bedrock Nova Reel

2. **Storage Layer** (`app/services/s3_client.py`)
   - Uploads to S3 bucket `aae-user-uploads`
   - Region: `us-west-2`
   - Organized by: `chat-images/{user_id}/{session_id}/` or `chat-videos/`

3. **Streaming Layer** (`app/api/chat.py`)
   - SSE event handler forwards observation events
   - Includes `attachments` field in unified format

4. **Backend API** (`backend/app/api/v1/media.py`)
   - Generates presigned URLs for S3 objects
   - 1-hour expiration for secure access

5. **Frontend Display** (`frontend/src/components/chat/AttachmentDisplay.tsx`)
   - Renders images, videos, and documents
   - Handles presigned URL fetching
   - Skips Next.js optimization for presigned URLs

## Unified Attachment Format

All tools return attachments in the same structure:

```python
{
    "success": True,
    "message": "Successfully generated 1 images",
    "attachments": [
        {
            "id": "image_0_generated_image_modern_1",
            "filename": "generated_image_modern_1.png",
            "contentType": "image/png",
            "size": 1152573,
            "s3Url": "chat-images/2/session-123/image.png",  # S3 object key
            "type": "image"  # or "video", "document"
        }
    ]
}
```

### Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier for the attachment |
| `filename` | string | Display filename |
| `contentType` | string | MIME type (image/png, video/mp4, etc.) |
| `size` | number | File size in bytes |
| `s3Url` | string | S3 object key (NOT full URL) |
| `type` | string | Category: "image", "video", "document" |

## Implementation Details

### 1. Tool Implementation

**Image Generation** (`creative_tools.py:100-300`):

```python
# Upload to S3
upload_result = await s3_client.upload_for_chat_display(
    image_bytes=image_bytes,
    filename=filename,
    user_id=user_id,
    session_id=session_id,
    style=style,
)

# Return with attachments
return {
    "success": True,
    "creative_ids": creative_ids,
    "count": 1,
    "message": f"Successfully generated {len(images)} images",
    "attachments": [{
        "id": f"image_{idx}_{filename_base}",
        "filename": filename,
        "contentType": "image/png",
        "size": upload_result["size"],
        "s3Url": upload_result["object_name"],  # S3 key for presigned URL
        "type": "image",
    }]
}
```

**Video Generation** (`creative_tools.py:700-850`):

```python
# Upload to S3
upload_result = await s3_client.upload_video(
    video_bytes=video_bytes,
    filename=filename,
    user_id=user_id or "anonymous",
    content_type="video/mp4",
    prefix="chat-videos",
)

# Return with attachments
result["attachments"] = [{
    "id": f"video_{operation_id[-8:]}",
    "filename": filename,
    "contentType": "video/mp4",
    "size": upload_result["size"],
    "s3Url": upload_result["object_name"],
    "type": "video",
}]
```

### 2. SSE Event Forwarding

**Critical Fix** (ai-orchestrator/app/api/chat.py:448-450):

```python
elif event_type == "observation":
    # Tool execution result
    observation_data = {
        'type': 'observation',
        'tool': event.get("tool", "unknown"),
        'success': event.get("success", False),
        'result': event.get("result", ""),
    }

    # ✅ Include attachments if present (unified format)
    if event.get("attachments"):
        observation_data["attachments"] = event["attachments"]

    # Legacy support for backwards compatibility
    if event.get("images"):
        observation_data["images"] = event["images"]

    yield f"data: {json.dumps(observation_data, ensure_ascii=False)}\n\n"
```

**Why This Matters**:
- Before fix: Attachments were stripped from observation events
- After fix: Attachments properly forwarded to frontend
- Result: Images and videos now display in chat interface

### 3. Backend Presigned URL Generation

**API Endpoint** (`backend/app/api/v1/media.py:31-103`):

```python
@router.get("/signed-url/{object_name:path}", response_model=SignedUrlResponse)
async def get_signed_url(object_name: str) -> SignedUrlResponse:
    """Generate presigned URL for S3 object.

    Args:
        object_name: S3 object key (e.g., "chat-images/2/session-123/image.png")

    Returns:
        SignedUrlResponse with presigned URL (1-hour expiration)
    """
    # Determine bucket based on path
    storage = s3_uploads_storage  # Default: aae-user-uploads

    if object_name.startswith("creatives/"):
        storage = s3_creatives_storage

    # Generate presigned URL
    signed_url = storage.generate_presigned_download_url(
        key=object_name,
        expires_in=3600,  # 1 hour
    )

    return SignedUrlResponse(
        signed_url=signed_url,
        object_name=object_name,
        expires_in_minutes=60,
    )
```

**S3 Configuration Requirements**:
- **Region**: Must match bucket region (us-west-2 for aae-user-uploads)
- **Credentials**: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY required
- **CORS**: Configured to allow frontend origins

### 4. Frontend Display

**Fetching Presigned URLs** (`AttachmentDisplay.tsx:54-107`):

```typescript
useEffect(() => {
  const fetchPresignedUrl = async (attachment: Attachment, idx: number) => {
    // Skip if already has direct URL
    if (attachment.download_url || attachment.cdnUrl) {
      return;
    }

    // Fetch presigned URL from backend
    const token = localStorage.getItem('access_token');
    const response = await fetch(
      `/api/v1/media/signed-url/${encodeURIComponent(attachment.s3Url)}`,
      {
        headers: {
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
      }
    );

    if (response.ok) {
      const data = await response.json();
      setPresignedUrls(prev => ({ ...prev, [idx]: data.signed_url }));
    }
  };

  attachments.forEach((attachment, idx) => {
    fetchPresignedUrl(attachment, idx);
  });
}, [attachments]);
```

**Rendering Images** (`AttachmentDisplay.tsx:166-209`):

```typescript
if (contentType.startsWith('image/')) {
  // Check if URL is a presigned URL
  const isPresignedUrl = url && (
    url.includes('X-Amz-Signature') ||
    url.includes('X-Amz-Algorithm')
  );

  return (
    <Image
      src={url}
      alt={attachment.filename}
      width={300}
      height={200}
      unoptimized={isPresignedUrl}  // ✅ Skip Next.js optimization
    />
  );
}
```

**Rendering Videos** (`AttachmentDisplay.tsx:212-231`):

```typescript
if (contentType.startsWith('video/')) {
  return (
    <video
      src={url}
      controls
      className="rounded-lg shadow-md"
      style={{ maxWidth: '400px', maxHeight: '300px' }}
    >
      您的浏览器不支持视频播放
    </video>
  );
}
```

### 5. Next.js Configuration

**Image Domain Configuration** (`frontend/next.config.mjs:3-21`):

```javascript
const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'storage.googleapis.com',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: '**.s3.amazonaws.com',  // ✅ Added for S3 support
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: '**.s3.*.amazonaws.com',  // ✅ Regional S3 URLs
        pathname: '/**',
      },
    ],
  },
};
```

## Fix History

### Fix 1: Tool Streaming Observation Events (2025-12-20)

**Problem**: Generated images didn't display in chat interface despite successful generation.

**Root Cause**: SSE handler in `chat.py` was not forwarding the `attachments` field from observation events.

**Solution**: Added 3 lines to forward attachments:
```python
if event.get("attachments"):
    observation_data["attachments"] = event["attachments"]
```

**Impact**: ✅ Images now properly display in chat interface

**Details**: See `TOOL_STREAMING_ATTACHMENT_FIX.md` (archived)

### Fix 2: Next.js Image Optimization (2025-12-20)

**Problem**: Next.js Image component failed with 400 error when loading S3 presigned URLs.

**Root Cause**: Next.js image optimizer tried to process presigned URLs, breaking the AWS signature.

**Solution**:
1. Added S3 domains to `next.config.mjs` remotePatterns
2. Added `unoptimized={true}` for presigned URLs

**Impact**: ✅ Presigned URLs load correctly without optimization errors

### Fix 3: S3 Region Mismatch (2025-12-20)

**Problem**: Presigned URLs returned 403 Forbidden with region error.

**Root Cause**: Backend generated presigned URLs with `us-east-1` region, but bucket is in `us-west-2`.

**Solution**: Restarted backend with explicit `AWS_REGION=us-west-2` environment variable.

**Impact**: ✅ Presigned URLs now use correct region and work properly

## Configuration Checklist

### AI Orchestrator

```bash
# .env
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET_UPLOADS=aae-user-uploads
```

### Backend

```bash
# .env
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET_UPLOADS=aae-user-uploads
S3_BUCKET_CREATIVES=aae-creatives
```

### Frontend

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

```javascript
// next.config.mjs
images: {
  remotePatterns: [
    { hostname: '**.s3.amazonaws.com' },
    { hostname: '**.s3.*.amazonaws.com' },
  ]
}
```

### S3 Bucket Configuration

**CORS Configuration**:
```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
    "AllowedOrigins": [
      "http://localhost:3000",
      "https://*.zmead.com"
    ],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

**Public Access Block**:
```json
{
  "BlockPublicAcls": true,
  "IgnorePublicAcls": true,
  "BlockPublicPolicy": true,
  "RestrictPublicBuckets": true
}
```

**Note**: Presigned URLs work even with public access blocked because they use temporary credentials.

## Testing

### Test Image Generation

```bash
curl -X POST http://localhost:8001/api/v1/chat \
  -H "Authorization: Bearer test-token-user-2" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "生成一张产品图片"}],
    "session_id": "test-image",
    "user_id": "2",
    "model_preferences": {
      "image_generation_provider": "bedrock",
      "image_generation_model": "stability.sd3-5-large-v1:0"
    }
  }'
```

**Expected SSE Events**:
```
data: {"type": "thinking", "message": "正在思考..."}
data: {"type": "action", "tool": "generate_image_tool"}
data: {"type": "observation", "tool": "generate_image_tool", "success": true, "attachments": [...]}
data: {"type": "text", "content": "已生成图片"}
data: {"type": "done"}
```

### Test Video Generation

```bash
curl -X POST http://localhost:8001/api/v1/chat \
  -H "Authorization: Bearer test-token-user-2" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "生成一段产品视频"}],
    "session_id": "test-video",
    "user_id": "2",
    "model_preferences": {
      "video_generation_provider": "bedrock",
      "video_generation_model": "amazon.nova-reel-v1:0"
    }
  }'
```

### Verify Attachment Display

1. Open frontend: `http://localhost:3000`
2. Send message: "生成一张图片"
3. Verify:
   - ✅ Image appears in chat
   - ✅ Click to open lightbox
   - ✅ Browser DevTools shows no 400/403 errors

## Troubleshooting

### Issue: Attachments Missing in Frontend

**Symptoms**:
```javascript
// Console log
observation event: { type: "observation", success: true, attachments: undefined }
```

**Solution**: Check SSE handler in `chat.py` includes:
```python
if event.get("attachments"):
    observation_data["attachments"] = event["attachments"]
```

### Issue: Image 400 Bad Request

**Symptoms**:
```
GET /_next/image?url=https://...X-Amz-Signature... 400 (Bad Request)
```

**Solution**: Add `unoptimized={true}` to Image component for presigned URLs:
```typescript
const isPresignedUrl = url.includes('X-Amz-Signature');
<Image src={url} unoptimized={isPresignedUrl} />
```

### Issue: Presigned URL 403 Forbidden

**Symptoms**:
```xml
<Error>
  <Code>AuthorizationQueryParametersError</Code>
  <Message>the region 'us-east-1' is wrong; expecting 'us-west-2'</Message>
</Error>
```

**Solution**:
1. Check `AWS_REGION` in backend .env: `AWS_REGION=us-west-2`
2. Restart backend service
3. Verify S3 client uses correct region

### Issue: Next.js Image Domain Not Configured

**Symptoms**:
```
Error: Invalid src prop ... hostname "...s3.amazonaws.com" is not configured
```

**Solution**: Add to `next.config.mjs`:
```javascript
images: {
  remotePatterns: [
    { protocol: 'https', hostname: '**.s3.amazonaws.com' }
  ]
}
```

## Best Practices

### 1. Always Use Unified Attachment Format

```python
# ✅ Good
return {
    "attachments": [{
        "id": "...",
        "filename": "...",
        "contentType": "...",
        "size": 123,
        "s3Url": "...",
        "type": "image"
    }]
}

# ❌ Bad - Mixed formats
return {
    "image_url": "...",
    "video_data_b64": "...",
}
```

### 2. Use S3 Object Keys, Not Full URLs

```python
# ✅ Good
"s3Url": "chat-images/2/session-123/image.png"

# ❌ Bad
"s3Url": "https://bucket.s3.amazonaws.com/chat-images/..."
```

### 3. Handle Presigned URLs in Frontend

```typescript
// ✅ Good - Detect and skip optimization
const isPresignedUrl = url.includes('X-Amz-Signature');
<Image src={url} unoptimized={isPresignedUrl} />

// ❌ Bad - Always optimize
<Image src={url} />
```

### 4. Organize S3 Objects by Session

```
chat-images/
  {user_id}/
    {session_id}/
      image_1.png
      image_2.png

chat-videos/
  {user_id}/
    {session_id}/
      video_1.mp4
```

### 5. Always Set ContentType on Upload

```python
# ✅ Good
s3_client.put_object(
    ContentType="image/png"  # Required for browser display
)

# ❌ Bad - Missing ContentType
s3_client.put_object()  # Defaults to binary/octet-stream
```

## Supported File Types

### Images
- ✅ PNG (image/png)
- ✅ JPEG (image/jpeg)
- ✅ WebP (image/webp)
- ✅ GIF (image/gif)

### Videos
- ✅ MP4 (video/mp4)
- ✅ WebM (video/webm)
- ✅ MOV (video/quicktime)

### Documents
- ✅ PDF (application/pdf)
- ✅ Text (text/plain)
- ✅ Other files (download link)

## Performance Considerations

### Presigned URL Expiration
- **Duration**: 1 hour (3600 seconds)
- **Caching**: Frontend fetches once per attachment
- **Refresh**: Auto-refetch if expired (future enhancement)

### S3 Upload Performance
- **Small files** (<1MB): ~200-500ms
- **Medium files** (1-10MB): ~500ms-2s
- **Large files** (>10MB): ~2-5s

### Frontend Display Performance
- **Image loading**: Progressive with Next.js Image
- **Video loading**: Native browser streaming
- **Lightbox**: Instant with cached presigned URL

## Future Enhancements

### 1. CloudFront CDN
- Add CloudFront distribution for S3 bucket
- Use CDN URLs instead of presigned URLs
- Longer cache duration (24 hours)

### 2. Thumbnail Generation
- Generate thumbnails on upload
- Display thumbnails in chat
- Full image in lightbox

### 3. Progressive Upload
- Stream upload progress to frontend
- Show upload percentage
- Cancel upload support

### 4. Attachment Expiration Management
- Auto-cleanup old attachments (>7 days)
- Archive to Glacier for cost savings
- User download before expiration

## Related Documentation

- [AWS Setup Guide](../AWS_SETUP_GUIDE.md) - AWS configuration
- [S3 Client Implementation](../MODEL_PROVIDER_README.md) - S3 client details
- [Next.js Image Configuration](https://nextjs.org/docs/api-reference/next/image) - Official docs

## Changelog

### 2025-12-20
- ✅ Fixed observation event attachment forwarding
- ✅ Fixed Next.js Image optimization for presigned URLs
- ✅ Fixed S3 region mismatch issue
- ✅ Added comprehensive documentation
- ✅ Verified image and video generation working end-to-end

---

**Status**: All attachment types (images, videos, documents) now work correctly end-to-end from tool execution to frontend display.
