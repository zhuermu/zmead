# File Upload Fix Summary

**Date**: 2025-12-04
**Issue**: Agent unable to understand uploaded images - attachment data not reaching AI Orchestrator

## Root Cause Analysis

The attachment data (`tempAttachments`) was being stripped during message forwarding through the request pipeline:

```
Frontend → Next.js API Route → AI Orchestrator → Agent
           ❌ Lost here
```

## Fixes Applied

### 1. Frontend Next.js API Route (`frontend/src/app/api/chat/route.ts`)

**Problem**: Message normalization was stripping `tempAttachments` and `attachments` fields

**Before**:
```typescript
const normalizedMessages = (body.messages || [])
  .map((msg: any) => ({
    role: msg.role,
    content: getMessageContent(msg),
  }))
  .filter((msg: any) => msg.content);
```

**After** (Lines 42-53):
```typescript
const normalizedMessages = (body.messages || [])
  .map((msg: any) => ({
    role: msg.role,
    content: getMessageContent(msg),
    // Preserve temp attachments (for files uploaded to GCS temp bucket)
    ...(msg.tempAttachments ? { tempAttachments: msg.tempAttachments } : {}),
    // Preserve permanent attachments (for already processed files)
    ...(msg.attachments ? { attachments: msg.attachments } : {}),
  }))
  .filter((msg: any) => msg.content);
```

### 2. AI Orchestrator API (`ai-orchestrator/app/api/chat.py`)

**Problem 1**: AI Orchestrator didn't accept `tempAttachments` field

**Solution**: Added support for temp attachments

**Changes**:
- Added `TempAttachment` Pydantic model (Lines 98-104)
- Modified `ChatMessage` to accept `tempAttachments` (Line 112)
- Added processing logic to convert temp attachments to agent format (Lines 163-185)

**Problem 2**: Calling `.model_dump()` on dict objects (Line 206)

**Before**:
```python
attachments=[att.model_dump() for att in attachments] if attachments else None,
```

**After**:
```python
attachments=attachments,  # Already dict format, no need for model_dump()
```

## Testing Results

### Test 1: File Upload
✅ **Success** - File uploaded to frontend (test_image.png, 70 B)

### Test 2: Message Sending with Attachment
✅ **Success** - Message sent: "请描述这个图片 [文件: test_image.png (70 B)]"

### Test 3: Attachment Data Flow
✅ **Success** - Attachment data now reaches AI Orchestrator

### Test 4: Services Health
✅ **Backend**: Healthy (http://localhost:8000/health)
✅ **AI Orchestrator**: Healthy (http://localhost:8001/health)
✅ **Frontend**: Running (http://localhost:3000)

## Current Data Flow

```
┌─────────────┐
│   Frontend  │
│  (Next.js)  │
└──────┬──────┘
       │ tempAttachments: [{fileKey, fileId, filename, ...}]
       ▼
┌─────────────────────────┐
│  Next.js API Route      │
│  /api/chat/route.ts     │
│  ✅ NOW PRESERVES       │
│     tempAttachments     │
└──────┬──────────────────┘
       │ Forward with tempAttachments
       ▼
┌──────────────────────────┐
│   AI Orchestrator        │
│   /api/v1/chat           │
│  ✅ NOW ACCEPTS          │
│     TempAttachment model │
└──────┬───────────────────┘
       │ Convert to agent format:
       │ {fileId, filename, contentType, permanentUrl, ...}
       ▼
┌─────────────┐
│ ReAct Agent │
│  ✅ RECEIVES│
│  attachments│
└─────────────┘
```

## Files Modified

1. `frontend/src/app/api/chat/route.ts` (Lines 42-53)
2. `ai-orchestrator/app/api/chat.py` (Lines 98-112, 163-185, 206)

## Gemini Files API Integration (COMPLETED)

### Phase 3: Gemini Files API Integration

**Date**: 2025-12-04 (Continued)

**Problem**: Agent could receive attachment metadata but couldn't analyze image content because files weren't uploaded to Gemini Files API.

**Solution**: Implemented complete Gemini Files API integration in AI Orchestrator

#### New Files Created:

1. **`ai-orchestrator/app/services/gemini_files.py`** - Gemini Files API service
   - `GeminiFilesService` class with methods:
     - `upload_file(data, mime_type, display_name)` - Upload bytes to Gemini
     - `download_from_gcs(gcs_uri)` - Download file from GCS bucket
     - `upload_from_gcs(gcs_uri, mime_type, display_name)` - Convenience method combining download + upload
     - `delete_file(file_name)` - Delete from Gemini
     - `get_file(file_name)` - Get file metadata
   - Uses `google.generativeai` library
   - Handles temp file creation (Gemini requires file path)
   - Returns file URI for use in prompts

#### Configuration Updates:

2. **`ai-orchestrator/app/core/config.py`** (Lines 72-95)
   - Added GCS configuration fields:
     - `gcs_project_id` - GCS project ID
     - `gcs_bucket_uploads_temp` - Temp uploads bucket (default: "aae-user-uploads-temp")
     - `gcs_bucket_uploads` - Permanent uploads bucket (default: "aae-user-uploads")
   - Matches backend GCS config structure

#### Integration Logic:

3. **`ai-orchestrator/app/api/chat.py`** (Lines 168-211)
   - Added import: `from app.services.gemini_files import gemini_files_service`
   - Replaced TODO with actual Gemini upload logic:
     ```python
     # For each temp attachment:
     gcs_uri = f"gs://aae-user-uploads-temp/{temp_att.fileKey}"
     gemini_result = gemini_files_service.upload_from_gcs(
         gcs_uri=gcs_uri,
         mime_type=temp_att.contentType,
         display_name=temp_att.filename,
     )

     if gemini_result:
         attachment_info["geminiFileUri"] = gemini_result["uri"]
         attachment_info["geminiFileName"] = gemini_result["name"]
     ```

#### Architecture:

**Correct Service Responsibilities**:
- **Backend**: GCS storage, file persistence, user data
- **AI Orchestrator**: Gemini Files API, AI model input preparation
- **Agent**: Consumes prepared multimodal inputs

This follows proper separation of concerns where AI-specific integrations stay in the AI Orchestrator layer.

## Critical Fix: Enable Multimodal Support in Streaming

### Phase 4: Fix Gemini Client Streaming Method

**Date**: 2025-12-04 (Continued)

**Problem**: Agent tried to call non-existent `upload_to_s3` tool and couldn't see images, even though attachments were uploaded to Gemini Files API.

**Root Cause**: The `chat_completion_stream` method in `gemini_client.py` used LangChain's wrapper (`ChatGoogleGenerativeAI`) which doesn't support Gemini Files API attachments. The attachment files were being ignored in the API request.

**Evidence**:
- SSE logs showed: `"type": "observation", "tool": "upload_to_s3", "success": false, "result": "Tool execution failed: MCP tool failed: 工具不存在"`
- Agent couldn't see the image despite geminiFileUri being properly set

**Solution**: Updated `gemini_client.py:353-405` to use native Google GenerativeAI SDK

#### Before (Broken):
```python
async def chat_completion_stream(...):
    llm = self._get_fast_llm()  # LangChain wrapper
    langchain_messages = self._convert_messages(messages)  # Strips attachments
    async for chunk in llm.astream(langchain_messages):
        yield chunk.content
```

#### After (Fixed):
```python
async def chat_completion_stream(...):
    client = self._get_genai_client()  # Native google-genai SDK
    contents = self._convert_messages_to_genai(messages)  # Handles attachments!
    async for chunk in client.models.generate_content_stream(
        model=self.fast_model_name,
        contents=contents,
        config=types.GenerateContentConfig(temperature=...),
    ):
        if chunk.text:
            yield chunk.text
```

**Key Change**:
- Now uses `_convert_messages_to_genai()` which properly handles attachments (lines 407-460)
- This method converts `geminiFileUri` to `types.Part.from_uri()` format required by Gemini API
- Uses native SDK's `generate_content_stream()` instead of LangChain's `astream()`

## Phase 5: GCS Credentials Configuration (COMPLETED)

**Date**: 2025-12-04 (Continued)

**Problem**: GCS client initialization failed due to missing credentials in AI Orchestrator

**Root Cause**: AI Orchestrator's `.env` file did not have GCS configuration

**Evidence from logs**:
```
[warning] GCS client initialization failed: Your default credentials were not found
[error] GCS client not available
[warning] Failed to upload to Gemini
```

**Solution**: Added GCS configuration to `ai-orchestrator/.env`:
```env
# Google Cloud Storage Configuration
GCS_PROJECT_ID=custom-unison-453604-k7
GCS_CREDENTIALS_PATH=/Users/xiaowely/ws/git/zmead/backend/custom-unison-453604-k7-90ae21210330.json
GCS_BUCKET_UPLOADS_TEMP=aae-user-uploads-temp
GCS_BUCKET_UPLOADS=aae-user-uploads
```

**Result**: ✅ Services restarted successfully, all health checks passing

## Current Status

- ✅ Attachment metadata flows through the system
- ✅ File upload to GCS works
- ✅ Gemini Files API integration implemented
- ✅ **Streaming method fixed to support multimodal content**
- ✅ **GCS credentials configured in AI Orchestrator**
- ✅ **All services healthy and running**
- ✅ **READY FOR IMAGE ANALYSIS TESTING**: Agent should now be able to analyze uploaded images

## Next Steps

1. Test with browser: Upload image and ask agent to describe it
2. Verify agent can now see and analyze the image content
3. Check logs for successful multimodal API calls
4. Monitor for any Gemini API errors

## Notes

- Gemini Files API requires files to be uploaded before use in prompts
- Files are temporary and expire after 48 hours in Gemini's system
- The implementation gracefully handles cases where GEMINI_API_KEY is not configured
- Agent receives both GCS permanent URL and Gemini File URI for flexibility
- **Critical**: Always use native google-genai SDK for multimodal features, not LangChain wrappers

## Verification Commands

```bash
# Check backend health
curl http://localhost:8000/health

# Check AI Orchestrator health
curl http://localhost:8001/health

# View logs
# Backend: Check background process cfe91b
# AI Orchestrator: Check background process 7770fb
```
