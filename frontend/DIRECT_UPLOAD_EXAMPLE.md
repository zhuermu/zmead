# Direct Upload to GCS - Implementation Guide

## Overview

这是一个优化的文件上传方案，使用**预签名 URL** 直接上传到 GCS，而不经过 backend 服务器。

## 架构流程

```
1. 用户选择文件
   ↓
2. 前端请求预签名 URL (POST /api/v1/uploads/presigned/generate)
   ↓
3. 前端使用预签名 URL 直接上传到 GCS (临时存储，36小时)
   ↓
4. 用户发送对话
   ↓
5. 前端确认上传 (POST /api/v1/uploads/presigned/confirm)
   ↓
6. Backend:
   - 从临时存储移动到永久存储
   - 上传到 Gemini Files API
   - 返回永久 URL 和 Gemini File URI
```

## Backend API

### 1. 生成预签名 URL

```http
POST /api/v1/uploads/presigned/generate
Authorization: Bearer {token}
Content-Type: application/json

{
  "filename": "photo.jpg",
  "contentType": "image/jpeg",
  "size": 1024000
}
```

**Response:**
```json
{
  "uploadUrl": "https://storage.googleapis.com/...",
  "fileKey": "temp/user-id/file-uuid.jpg",
  "fileId": "uuid",
  "expiresAt": "2025-12-05T14:00:00Z",
  "cdnUrl": "https://storage.googleapis.com/..."
}
```

### 2. 确认上传

```http
POST /api/v1/uploads/presigned/confirm
Authorization: Bearer {token}
Content-Type: application/json

{
  "fileKey": "temp/user-id/file-uuid.jpg",
  "fileId": "uuid"
}
```

**Response:**
```json
{
  "fileKey": "chat-attachments/user-id/file-uuid.jpg",
  "fileId": "uuid",
  "permanentUrl": "gs://aae-user-uploads/...",
  "cdnUrl": "https://storage.googleapis.com/...",
  "geminiFileUri": "https://generativelanguage.googleapis.com/v1beta/files/xxx",
  "geminiFileName": "files/xxx"
}
```

## Frontend Usage

### 使用 Hook

```tsx
import { useDirectUpload } from '@/hooks/useDirectUpload'

function ChatInput() {
  const {
    uploadFiles,
    uploadedFiles,
    confirmUploads,
    removeFile,
    clearFiles,
    isUploading,
    hasUploadedFiles
  } = useDirectUpload()

  // 1. 用户选择文件时
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files) {
      await uploadFiles(Array.from(files))
    }
  }

  // 2. 用户发送消息时
  const handleSendMessage = async (content: string) => {
    // 确认上传，获取永久 URL 和 Gemini URI
    const confirmedFiles = await confirmUploads()

    // 发送消息，包含文件信息
    await sendMessage({
      content,
      attachments: confirmedFiles.map(f => ({
        fileId: f.fileId,
        geminiFileUri: f.geminiFileUri,
        cdnUrl: f.cdnUrl,
      }))
    })

    clearFiles()
  }

  return (
    <div>
      {/* 文件选择 */}
      <input
        type="file"
        multiple
        onChange={handleFileSelect}
        disabled={isUploading}
      />

      {/* 显示已上传的文件 */}
      {uploadedFiles.map(file => (
        <FilePreview
          key={file.presigned.fileId}
          file={file}
          onRemove={() => removeFile(file.presigned.fileId)}
        />
      ))}

      {/* 发送按钮 */}
      <button
        onClick={() => handleSendMessage(messageContent)}
        disabled={isUploading}
      >
        发送
      </button>
    </div>
  )
}
```

### 使用底层 API

```tsx
import {
  uploadFileDirect,
  confirmUpload
} from '@/lib/upload-direct'

// 1. 上传文件
const uploadedFile = await uploadFileDirect(
  file,
  token,
  (progress) => console.log(`${progress}%`)
)

// 2. 发送消息时确认
const confirmed = await confirmUpload(
  uploadedFile.presigned.fileKey,
  uploadedFile.presigned.fileId,
  token
)

// 3. 使用确认后的文件信息
console.log('Gemini URI:', confirmed.geminiFileUri)
console.log('CDN URL:', confirmed.cdnUrl)
```

## 文件状态

```typescript
type FileStatus =
  | 'pending'    // 等待上传
  | 'uploading'  // 上传中
  | 'uploaded'   // 已上传到临时存储
  | 'confirmed'  // 已确认并移至永久存储
  | 'error'      // 上传失败
```

## 优势

1. **减少 Backend 负载** - 文件不经过 backend 服务器
2. **更快的上传速度** - 直连 GCS
3. **更好的用户体验** - 上传和对话分离
4. **节省带宽** - Backend 只处理元数据
5. **自动清理** - 临时文件 36 小时后自动过期

## GCS Bucket 配置

需要两个 bucket：

1. **aae-user-uploads-temp** - 临时存储
   - Lifecycle: 36 小时后自动删除
   - CORS: 允许前端域名

2. **aae-user-uploads** - 永久存储
   - 按用户组织: `chat-attachments/{user_id}/`
   - 可配置 CDN

## 部署配置

### 1. 创建 GCS Buckets

访问 [GCS Console](https://console.cloud.google.com/storage/browser?project=custom-unison-453604-k7)

**Bucket 1: aae-user-uploads-temp (临时存储)**
```bash
# 配置
Name: aae-user-uploads-temp
Location: asia-east1 (台湾)
Storage class: Standard

# Lifecycle Rule (自动删除)
Action: Delete object
Condition: Age = 2 days (48小时)

# CORS 配置 (可选，如果需要前端直接上传)
[
  {
    "origin": ["http://localhost:3000", "https://your-domain.com"],
    "method": ["GET", "PUT", "POST"],
    "responseHeader": ["Content-Type"],
    "maxAgeSeconds": 3600
  }
]
```

**Bucket 2: aae-user-uploads (永久存储)**
```bash
# 配置
Name: aae-user-uploads
Location: asia-east1
Storage class: Standard
# 不需要 Lifecycle rule
```

### 2. 创建 Service Account

1. 访问 [IAM Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts?project=custom-unison-453604-k7)
2. 创建服务账号:
   - 名称: `aae-backend-storage`
   - 描述: `Backend service for GCS access`
3. 授予角色: `Storage Object Admin`
4. 创建密钥（JSON 格式）并下载

### 3. 配置环境变量

```env
# Backend .env
GCS_PROJECT_ID=custom-unison-453604-k7
GCS_CREDENTIALS_PATH=/absolute/path/to/service-account.json
GEMINI_API_KEY=your-api-key

# Bucket names (可选，使用默认值)
GCS_BUCKET_TEMP=aae-user-uploads-temp
GCS_BUCKET_UPLOADS=aae-user-uploads
```

### 4. 验证配置

```bash
cd backend

# 测试 Service Account 认证
python -c "from app.core.storage import is_gcs_available; print('GCS Available:', is_gcs_available())"

# 启动服务
uvicorn app.main:app --reload --port 8000
```

## 安全考虑

1. ✅ **认证** - 需要 Bearer token
2. ✅ **文件大小限制** - 最大 50MB
3. ✅ **用户隔离** - 文件按用户 ID 存储
4. ✅ **临时存储** - 未确认的文件自动过期
5. ✅ **验证归属** - 确认时验证文件所有权

## 实施状态

### ✅ 已完成功能

| 功能 | 状态 | 说明 |
|------|------|------|
| Backend API | ✅ | 两个端点均已实现并测试 |
| GCS 集成 | ✅ | Service Account 认证成功 |
| Gemini Files API | ✅ | 文件自动上传到 Gemini |
| 临时存储 | ✅ | 48小时自动过期 |
| 永久存储 | ✅ | 按用户 ID 组织 |
| Frontend Hook | ✅ | useDirectUpload 已实现 |
| Frontend Utils | ✅ | upload-direct.ts 已实现 |
| 前端测试 | ✅ | 已在 UI 中验证通过 |

### 📝 测试记录

**测试时间**: 2025-12-04
**测试环境**: 本地开发环境

**测试结果**:
- ✅ 直接上传流程: 预签名URL → GCS临时存储 → 确认 → 永久存储
- ✅ 传统上传流程: 向后兼容，正常工作
- ✅ Gemini Files API: 文件成功上传并获得 URI
- ✅ 文件组织: 按用户 ID 正确隔离
- ✅ 性能优化: 大文件不经过 backend

### 🔄 迁移建议

可以同时保留两种上传方式：

- **旧方式**: `/api/v1/uploads` - 小文件、简单场景、向后兼容
- **新方式**: `/api/v1/uploads/presigned/*` - 大文件、优化性能、推荐使用

**迁移步骤**:
1. 保持现有上传功能正常工作
2. 在新功能中使用 `useDirectUpload` hook
3. 逐步替换旧的上传逻辑
4. 监控两种方式的使用情况
5. 最终可以废弃旧方式（可选）

## 技术实现

### Backend 核心文件

| 文件 | 说明 |
|------|------|
| `backend/app/core/storage.py` | GCS 客户端封装 |
| `backend/app/core/gemini_files.py` | Gemini Files API 客户端 |
| `backend/app/api/v1/upload_presigned.py` | 预签名URL端点 |
| `backend/app/api/v1/uploads.py` | 传统上传端点（已集成Gemini） |

### Frontend 核心文件

| 文件 | 说明 |
|------|------|
| `frontend/src/hooks/useDirectUpload.ts` | React Hook |
| `frontend/src/lib/upload-direct.ts` | 底层 API |
| `frontend/DIRECT_UPLOAD_EXAMPLE.md` | 文档（本文件） |
