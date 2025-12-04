# 文件上传流程说明

## 新的优雅设计（当前实现）

### 流程概览

```
用户选择文件
    ↓
前端：上传到临时GCS桶（presigned URL）
    ↓
前端：发送消息（带临时文件引用）
    ↓
后端：接收消息
    ↓
后端：异步处理文件
    ├── 验证文件权限
    ├── 从临时桶移动到永久桶
    ├── 上传到 Gemini Files API
    └── 清理临时文件
    ↓
后端：将处理后的文件信息传给 AI Agent
    ↓
AI Agent：使用 Gemini File URI 分析文件
```

### 详细步骤

#### 1. 前端上传到临时存储（用户选择文件后立即执行）

**文件**: `frontend/src/hooks/useDirectUpload.ts`

```typescript
// 用户选择文件后立即上传到临时GCS桶
const uploadFilesToGCS = async (files: File[]) => {
  for (const file of files) {
    // 1. 请求 presigned URL
    const presigned = await requestPresignedUrl(file, token)

    // 2. 直接上传到 GCS 临时桶 (aae-user-uploads-temp)
    await uploadToGCS(file, presigned.uploadUrl, onProgress)

    // 保存上传结果（fileKey, fileId等）
    // 不调用 confirm - 这是关键改进！
  }
}
```

**临时文件存储位置**:
- 桶: `aae-user-uploads-temp`
- 路径: `temp/{user_id}/{file_id}.ext`
- 有效期: 48小时（lifecycle policy）

#### 2. 前端发送消息（带临时文件引用）

**文件**: `frontend/src/components/chat/ChatDrawer.tsx`

```typescript
const onSubmit = async (e) => {
  // 不再调用 confirmUploads()！

  // 直接发送临时文件引用
  const tempAttachments = uploadedFiles.map(uploaded => ({
    fileKey: uploaded.presigned.fileKey,  // temp/{user_id}/{file_id}.ext
    fileId: uploaded.presigned.fileId,
    filename: uploaded.file.name,
    contentType: uploaded.file.type,
    size: uploaded.file.size,
  }))

  // 发送消息
  await sendMessage(messageContent, tempAttachments)
}
```

#### 3. 后端接收并处理文件（自动异步）

**文件**: `backend/app/api/v1/chat.py`

```python
@router.post("/chat")
async def chat_stream(request: ChatRequest, current_user: CurrentUser):
    # 在开始流式响应前，处理所有临时文件
    processed_messages = []

    for msg in request.messages:
        if msg.tempAttachments:
            # 异步处理临时文件
            processed_attachments = await process_temp_attachments(
                msg.tempAttachments,
                current_user.id
            )

            # 添加处理后的文件信息
            msg_dict["attachments"] = [att.to_dict() for att in processed_attachments]

    # 将处理后的消息传给 AI Orchestrator
    payload = {"messages": processed_messages, ...}
```

#### 4. 文件处理服务（核心逻辑）

**文件**: `backend/app/services/file_processor.py`

```python
async def process_temp_attachment(file_key, file_id, user_id):
    # 1. 权限验证
    if not file_key.startswith(f"temp/{user_id}/"):
        return None

    # 2. 从临时桶下载文件
    temp_blob = temp_uploads_storage.bucket.blob(file_key)
    file_data = temp_blob.download_as_bytes()

    # 3. 上传到永久桶
    perm_key = f"chat-attachments/{user_id}/{file_id}.ext"
    perm_url = perm_uploads_storage.upload_file(
        key=perm_key,
        data=file_data,
        content_type=content_type,
    )

    # 4. 上传到 Gemini Files API
    gemini_result = gemini_files_service.upload_file(
        data=file_data,
        mime_type=content_type,
        display_name=filename,
    )

    # 5. 清理临时文件
    temp_blob.delete()

    # 6. 返回处理结果
    return ProcessedAttachment(
        file_id=file_id,
        permanent_url=perm_url,
        cdn_url=cdn_url,
        gemini_file_uri=gemini_result["uri"],
        gemini_file_name=gemini_result["name"],
    )
```

## 优势对比

### ❌ 旧设计（前端主动confirm）

```
前端上传 → 临时桶
   ↓
前端调用 /api/v1/uploads/presigned/confirm  ← 阻塞用户体验
   ↓
后端移动文件 + 上传Gemini
   ↓
前端等待完成  ← 可能很慢
   ↓
前端发送消息
```

**问题**:
- ❌ 前端需要等待confirm完成（慢）
- ❌ 用户体验差，消息发送被阻塞
- ❌ 前端需要处理confirm失败的情况
- ❌ 责任分配不清晰（前端管理后端逻辑）

### ✅ 新设计（后端监听事件自动处理）

```
前端上传 → 临时桶
   ↓
前端发送消息（立即！）  ← 用户体验好
   ↓
后端接收到消息事件
   ↓
后端自动异步处理文件  ← 解耦
   ↓
AI Agent 使用 Gemini File URI
```

**优势**:
- ✅ 前端无需等待文件处理（快速响应）
- ✅ 用户体验好，消息立即发送
- ✅ 责任分离清晰（前端只管上传，后端管理文件生命周期）
- ✅ 错误处理集中在后端
- ✅ 可扩展（后端可添加重试、批处理等优化）

## API 接口变更

### 前端发送消息格式

```typescript
// POST /api/v1/chat
{
  "messages": [
    {
      "role": "user",
      "content": "这张图片是什么？\n\n[文件: photo.jpg (2.5 MB)]",
      "tempAttachments": [  // ← 新增字段
        {
          "fileKey": "temp/user-123/abc-def-456.jpg",
          "fileId": "abc-def-456",
          "filename": "photo.jpg",
          "contentType": "image/jpeg",
          "size": 2621440
        }
      ]
    }
  ]
}
```

### 后端传给 AI Orchestrator 格式

```python
{
  "messages": [
    {
      "role": "user",
      "content": "这张图片是什么？\n\n[文件: photo.jpg (2.5 MB)]",
      "attachments": [  // ← 已处理的文件
        {
          "fileId": "abc-def-456",
          "filename": "photo.jpg",
          "contentType": "image/jpeg",
          "size": 2621440,
          "permanentKey": "chat-attachments/user-123/abc-def-456.jpg",
          "permanentUrl": "gs://aae-user-uploads/chat-attachments/user-123/abc-def-456.jpg",
          "cdnUrl": "https://cdn.example.com/...",
          "geminiFileUri": "https://generativelanguage.googleapis.com/v1beta/files/abc123",
          "geminiFileName": "files/abc123"
        }
      ]
    }
  ]
}
```

## 存储桶配置

所有存储桶名称从配置文件读取，支持灵活配置：

**配置文件**: `backend/.env`

```env
# 临时文件存储桶（48小时自动清理）
GCS_BUCKET_UPLOADS_TEMP=aae-user-uploads-temp

# 永久文件存储桶
GCS_BUCKET_UPLOADS=aae-user-uploads
```

**代码自动读取配置**:
```python
# backend/app/services/file_processor.py
temp_uploads_storage = GCSStorage(settings.gcs_bucket_uploads_temp)
perm_uploads_storage = GCSStorage(settings.gcs_bucket_uploads)
```

## 错误处理

### 临时文件不存在

```python
if not temp_uploads_storage.file_exists(file_key):
    logger.error(f"Temp file not found: {file_key}")
    return None  # 跳过这个文件，继续处理其他文件
```

### 权限检查

```python
if not file_key.startswith(f"temp/{user_id}/"):
    logger.error(f"Permission denied: {file_key} does not belong to {user_id}")
    return None
```

### Gemini 上传失败

```python
gemini_result = gemini_files_service.upload_file(...)
if not gemini_result:
    logger.warning(f"Failed to upload to Gemini: {filename}")
    # 仍然返回GCS URL，AI可能无法处理文件但消息不会失败
```

## 监控和日志

关键日志点:

```python
logger.info(f"Processing {len(temp_attachments)} temp attachments")
logger.info(f"Successfully processed attachment: {filename} ({file_id})")
logger.info(f"File uploaded to Gemini: {filename} -> {gemini_file_name}")
logger.warning(f"Failed to process attachment: {filename} ({file_id})")
logger.error(f"Error processing temp attachment {file_key}: {e}")
```

## 性能考虑

1. **并行处理**: 可以将多个文件的处理并行化
2. **缓存**: Gemini File URI 可以缓存避免重复上传
3. **后台任务**: 如果文件很大，可以移到Celery后台任务
4. **重试机制**: 对于Gemini上传失败的情况，可以添加重试

## 迁移指南

### 前端改动

1. `ChatDrawer.tsx`: 移除 `confirmUploads()` 调用
2. `useChat.ts`: 支持发送 `tempAttachments` 字段
3. 无需修改上传逻辑（`useDirectUpload`）

### 后端改动

1. 添加 `TempFileAttachment` 模型到 `chat.py`
2. 创建 `file_processor.py` 服务
3. 修改 `chat_stream` 函数处理临时文件
4. 配置文件添加存储桶配置

### 测试清单

- [ ] 上传单个文件
- [ ] 上传多个文件
- [ ] 文件权限检查（不同用户）
- [ ] 临时文件不存在的情况
- [ ] Gemini上传失败的情况
- [ ] 大文件上传
- [ ] 并发上传
- [ ] 临时文件清理（48小时后）

## 相关文档

- [Direct Upload Example](./DIRECT_UPLOAD_EXAMPLE.md) - 原始的直接上传示例
- [GCS CORS Configuration](../backend/scripts/README_CORS.md) - 存储桶CORS配置
- [CLAUDE.md](../CLAUDE.md) - 项目架构文档
