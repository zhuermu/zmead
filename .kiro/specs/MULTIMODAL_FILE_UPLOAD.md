# Multimodal File Upload Feature Specification

## Overview

Enable AI agent conversations to support file uploads (images, videos, documents) with multimodal understanding powered by Gemini API.

## Requirements

### 1. File Upload Support

**WHEN** user uploads a file in chat interface
**THEN** system should:
- Accept image formats: PNG, JPG, JPEG, WEBP, HEIC, HEIF
- Accept video formats: MP4, MPEG, MOV, AVI, FLV, MPG, WEBM, WMV, 3GPP
- Accept document formats: PDF, TXT, HTML, CSS, JS, TS, PY, MD, CSV, XML, RTF
- Maximum file size: 20MB for images, 200MB for videos, 50MB for documents
- Upload directly to GCS bucket: `aae-user-uploads`
- Store files with path: `{user_id}/chat-attachments/{session_id}/{filename}`

### 2. GCS Bucket Simplification

**WHEN** configuring file storage
**THEN** system should:
- Use single GCS bucket: `GCS_BUCKET_UPLOADS` (permanent storage)
- Remove `GCS_BUCKET_UPLOADS_TEMP` configuration
- Remove 48-hour expiration logic
- All uploaded files are permanently stored
- Update backend configuration to remove temporary bucket references

**Environment Variables** (backend and ai-orchestrator):
```bash
GCS_BUCKET_UPLOADS=aae-user-uploads  # Single permanent bucket
```

### 3. File Processing Flow

#### 3.1 Frontend Upload Flow

**WHEN** user attaches a file to chat message
**THEN** frontend should:
1. Call `POST /api/v1/uploads/presigned/chat-attachment` with file metadata
2. Receive presigned upload URL and final GCS path
3. Upload file directly to GCS using presigned URL
4. Include GCS file path in chat message payload
5. Display file thumbnail/preview in chat bubble

#### 3.2 Backend Upload API

**Endpoint**: `POST /api/v1/uploads/presigned/chat-attachment`

**Request**:
```json
{
  "filename": "example.png",
  "content_type": "image/png",
  "file_size": 1048576,
  "session_id": "session_123"
}
```

**Response**:
```json
{
  "upload_url": "https://storage.googleapis.com/...",
  "gcs_path": "user_123/chat-attachments/session_123/example.png",
  "download_url": "https://storage.googleapis.com/...",
  "expires_in": 3600
}
```

**Validation Rules**:
- Check user authentication
- Validate file size limits
- Validate file type against allowed extensions
- Verify user has sufficient credits (1 credit per file upload)

#### 3.3 AI Agent File Processing

**WHEN** AI agent receives chat message with file attachments
**THEN** ai-orchestrator should:
1. Receive GCS file paths in chat request
2. Generate signed download URLs (valid for 1 hour)
3. Download file content from GCS
4. Upload to Gemini File API using `genai.upload_file()`
5. Wait for file to be processed (status: ACTIVE)
6. Include file reference in Gemini API request with appropriate MIME type

#### 3.4 Gemini File API Integration

**Supported File Types**:

| Category | MIME Types | Gemini API Method |
|----------|------------|-------------------|
| Images | image/png, image/jpeg, image/webp | Direct inline content |
| Videos | video/mp4, video/mpeg, video/mov, etc. | File API upload required |
| Documents | application/pdf, text/plain, etc. | File API upload required |

**Image Understanding** (直接inline):
```python
response = model.generate_content([
    "Describe this image",
    {"mime_type": "image/jpeg", "data": base64_image_data}
])
```

**Video Understanding** (File API):
```python
video_file = genai.upload_file(path=downloaded_path, mime_type="video/mp4")
while video_file.state.name == "PROCESSING":
    time.sleep(2)
    video_file = genai.get_file(video_file.name)

response = model.generate_content([
    "Summarize this video",
    video_file
])
```

**Document Understanding** (File API):
```python
doc_file = genai.upload_file(path=downloaded_path, mime_type="application/pdf")
response = model.generate_content([
    "Extract key information from this document",
    doc_file
])
```

### 4. Frontend UI Enhancements

#### 4.1 File Attachment Input

**WHEN** user clicks attach file button
**THEN** UI should:
- Show file picker dialog
- Display selected file preview
- Show upload progress indicator
- Display file name, size, and type
- Allow removing attachment before sending

#### 4.2 Message Bubble File Display

**WHEN** message contains file attachments
**THEN** message bubble should:
- **Images**: Display thumbnail (max 300px width) with lightbox click to view full size
- **Videos**: Show video player with play/pause controls
- **Documents**: Show file icon, name, size with download button
- All files: Include download link with file name

**UI Components**:
```tsx
// Image preview
<img src={signedUrl} alt={filename} className="max-w-[300px] rounded cursor-pointer" onClick={openLightbox} />

// Video preview
<video controls src={signedUrl} className="max-w-[400px] rounded" />

// Document preview
<div className="flex items-center gap-2 p-3 bg-gray-100 rounded">
  <FileIcon type={fileType} />
  <div>
    <p className="font-medium">{filename}</p>
    <p className="text-sm text-gray-500">{fileSize}</p>
  </div>
  <DownloadButton url={signedUrl} filename={filename} />
</div>
```

### 5. Data Schema Updates

#### 5.1 Chat Message Schema

**Update**: `backend/app/schemas/chat.py` and `ai-orchestrator/app/schemas/chat.py`

```python
class FileAttachment(BaseModel):
    gcs_path: str
    filename: str
    content_type: str
    file_size: int
    download_url: Optional[str] = None  # Signed URL for viewing

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    attachments: Optional[List[FileAttachment]] = None
    timestamp: datetime
```

#### 5.2 Database Model

**Update**: `backend/app/models/chat.py`

```python
class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(255), nullable=False, index=True)
    role = Column(Enum("user", "assistant"), nullable=False)
    content = Column(Text, nullable=False)
    attachments = Column(JSON, nullable=True)  # List of FileAttachment dicts
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Migration**:
```bash
cd backend
alembic revision --autogenerate -m "add_attachments_to_messages"
alembic upgrade head
```

### 6. Credit Consumption

**WHEN** user uploads file for AI understanding
**THEN** system should:
- Deduct 1 credit for file upload
- Deduct additional credits based on Gemini API token usage
- Show credit cost in UI before upload confirmation (for large files)

**Cost Formula**:
- File upload: 1 credit (flat fee)
- Gemini processing: Variable based on input/output tokens
- Video processing: Higher cost due to frame extraction

### 7. Error Handling

**Error Codes**:
- `5001`: INVALID_FILE_TYPE
- `5002`: FILE_TOO_LARGE
- `5003`: UPLOAD_FAILED
- `5004`: GEMINI_UPLOAD_FAILED
- `5005`: FILE_PROCESSING_TIMEOUT

**Error Messages** (Chinese):
- "不支持的文件类型，请上传图片、视频或文档"
- "文件大小超过限制（图片20MB/视频200MB/文档50MB）"
- "文件上传失败，请重试"
- "AI 文件处理失败，请稍后重试"
- "文件处理超时，请尝试上传更小的文件"

### 8. Security Considerations

**WHEN** handling file uploads
**THEN** system must:
- Validate file MIME type both client-side and server-side
- Scan files for malware (future enhancement)
- Use signed URLs with expiration (1 hour for download, 15 min for upload)
- Verify user owns the session_id before generating presigned URLs
- Rate limit: Max 10 file uploads per minute per user
- Store files in user-specific directories to prevent unauthorized access

### 9. Performance Optimizations

**WHEN** processing large files
**THEN** system should:
- Stream file downloads instead of loading into memory
- Use temporary local storage for Gemini File API uploads
- Clean up temporary files after processing
- Implement file upload retry with exponential backoff
- Cache Gemini file upload results for 1 hour (avoid re-uploading same file)

**Caching Strategy**:
```python
cache_key = f"gemini_file:{sha256_hash}"
if cached_file_uri := redis.get(cache_key):
    return cached_file_uri
else:
    file_uri = genai.upload_file(...)
    redis.setex(cache_key, 3600, file_uri)
    return file_uri
```

### 10. Implementation Priority

**Phase 1** (MVP):
1. ✅ Simplify GCS bucket configuration
2. ✅ Implement presigned URL generation for chat attachments
3. ✅ Add Gemini File API client
4. ✅ Support image upload and understanding
5. ✅ Basic file preview in chat UI

**Phase 2** (Enhanced):
6. ✅ Video upload and understanding
7. ✅ Document upload and understanding
8. ✅ Advanced file preview (video player, PDF viewer)
9. ✅ File upload progress indicator

**Phase 3** (Polish):
10. File upload caching
11. Malware scanning
12. Batch file upload
13. File search and filter in chat history

## Testing Scenarios

### Test Case 1: Image Understanding
1. User uploads product photo
2. User asks "这张图片里的产品适合什么广告文案?"
3. AI analyzes image and generates ad copy suggestions

### Test Case 2: Video Analysis
1. User uploads 30-second product demo video
2. User asks "总结视频内容并推荐适合的投放平台"
3. AI summarizes video and recommends TikTok/Meta

### Test Case 3: Document Processing
1. User uploads competitor analysis PDF
2. User asks "提取关键竞争策略"
3. AI extracts and summarizes key insights

### Test Case 4: Multi-file Context
1. User uploads 3 product images
2. User asks "比较这些产品，哪个更适合年轻人市场?"
3. AI compares all images and provides analysis

## References

- [Gemini Image Understanding](https://ai.google.dev/gemini-api/docs/image-understanding?hl=zh-cn)
- [Gemini Video Understanding](https://ai.google.dev/gemini-api/docs/video-understanding?hl=zh-cn)
- [Gemini Document Processing](https://ai.google.dev/gemini-api/docs/document-processing?hl=zh-cn)
- [Gemini File API](https://ai.google.dev/gemini-api/docs/file-api?hl=zh-cn)
- [Google Cloud Storage Signed URLs](https://cloud.google.com/storage/docs/access-control/signed-urls)
