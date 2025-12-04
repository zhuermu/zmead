# Multimodal File Upload Testing Guide

## Prerequisites

### 1. Install Dependencies

```bash
cd frontend
npm install lucide-react  # Icon library (if not already installed)
```

### 2. Environment Setup

Ensure all services have proper environment variables:

**Backend** (`.env`):
```bash
GCS_BUCKET_UPLOADS=aae-user-uploads
GCS_PROJECT_ID=your-project-id
GCS_CREDENTIALS_PATH=/path/to/credentials.json
GEMINI_API_KEY=your-gemini-api-key
```

**AI Orchestrator** (`.env`):
```bash
GCS_BUCKET_UPLOADS=aae-user-uploads
GEMINI_API_KEY=your-gemini-api-key
WEB_PLATFORM_SERVICE_TOKEN=your-service-token
```

**Frontend** (`.env.local`):
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Create GCS Bucket

```bash
# Create the bucket
gsutil mb gs://aae-user-uploads

# Set CORS configuration (for direct uploads)
gsutil cors set backend/scripts/cors.json gs://aae-user-uploads

# Set lifecycle (optional - auto-delete files older than 90 days)
gsutil lifecycle set backend/scripts/lifecycle.json gs://aae-user-uploads
```

## Starting Services

### Terminal 1: Backend
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### Terminal 2: AI Orchestrator
```bash
cd ai-orchestrator
source venv/bin/activate
uvicorn app.main:app --reload --port 8001
```

### Terminal 3: Frontend
```bash
cd frontend
npm run dev
```

## Testing Scenarios

### Test 1: Image Upload and Understanding ✅

**Steps:**
1. Open chat interface: http://localhost:3000
2. Click the paperclip (📎) button
3. Select an image file (PNG, JPG, etc.)
4. Wait for upload to complete (progress bar)
5. See thumbnail preview below input
6. Type message: "这张图片里有什么？描述一下"
7. Press Enter or click Send

**Expected Results:**
- ✅ File uploads successfully (progress indicator)
- ✅ Thumbnail appears in AttachmentPreview
- ✅ Message sent with attachment
- ✅ User message bubble shows image thumbnail
- ✅ AI analyzes the image and responds with description
- ✅ Click image to open full-screen lightbox
- ✅ Lightbox features work: zoom, download, close (ESC)

**Test Images:**
- Product photo
- Screenshot with text
- Infographic
- Landscape/scene photo

### Test 2: Video Upload and Analysis ✅

**Steps:**
1. Click paperclip button
2. Select a video file (MP4, MOV, etc., max 200MB)
3. Wait for upload (may take longer for large files)
4. See video preview with play icon
5. Type: "总结这个视频的内容"
6. Send message

**Expected Results:**
- ✅ Large file uploads with progress tracking
- ✅ Video preview shows thumbnail
- ✅ Video plays in message bubble with controls
- ✅ AI summarizes video content

**Test Videos:**
- Short product demo (10-30 seconds)
- Tutorial video
- Marketing video

### Test 3: Document Upload and Processing ✅

**Steps:**
1. Click paperclip button
2. Select a document (PDF, TXT, etc.)
3. Wait for upload
4. See file icon with name and size
5. Type: "提取这个文档的关键信息"
6. Send message

**Expected Results:**
- ✅ Document uploads successfully
- ✅ Shows file icon, name, size
- ✅ Download button works
- ✅ AI extracts and summarizes document content

**Test Documents:**
- PDF report
- Text file
- Markdown file
- CSV data file

### Test 4: Multiple File Upload ✅

**Steps:**
1. Click paperclip button
2. Select multiple files (Ctrl/Cmd + Click)
   - 1 image
   - 1 PDF
   - 1 video
3. Wait for all uploads to complete
4. See all files in preview
5. Type: "分析这些文件的内容"
6. Send message

**Expected Results:**
- ✅ All files upload in parallel
- ✅ Progress shown for each file
- ✅ All files displayed in preview
- ✅ Can remove individual files before sending
- ✅ AI receives and processes all files
- ✅ Response references content from multiple files

### Test 5: Error Handling 🔴

#### Test 5.1: File Too Large
**Steps:**
1. Try uploading image > 20MB
2. Or video > 200MB
3. Or document > 50MB

**Expected Results:**
- ❌ Upload blocked with clear error message
- ❌ "File too large. Maximum size for [type] is [X]MB"
- ✅ Can still upload other valid files

#### Test 5.2: Unsupported File Type
**Steps:**
1. Try uploading .exe, .zip, or other unsupported format

**Expected Results:**
- ❌ Upload blocked with error
- ❌ "Unsupported file type. Please upload images, videos, or documents."

#### Test 5.3: Network Error
**Steps:**
1. Start upload
2. Disconnect internet
3. Reconnect and retry

**Expected Results:**
- ❌ Upload fails with error message
- ✅ Can retry upload
- ✅ Other features still work

### Test 6: UI/UX Features ✅

#### Attachment Preview (Before Send)
- ✅ Image thumbnails display correctly
- ✅ Video previews show frame
- ✅ Document shows icon + filename
- ✅ File size displayed
- ✅ Remove button (X) works
- ✅ Progress bars animate smoothly

#### Message Bubble (After Send)
- ✅ User messages show attachments
- ✅ Images clickable (opens lightbox)
- ✅ Videos have playback controls
- ✅ Documents have download button
- ✅ Responsive layout (mobile/desktop)

#### Image Lightbox
- ✅ Opens on image click
- ✅ Full-screen display
- ✅ Zoom in/out (+ / - keys)
- ✅ Reset zoom (0 key)
- ✅ Download button works
- ✅ Fullscreen toggle
- ✅ ESC key closes
- ✅ Click outside closes
- ✅ Keyboard shortcuts help text

### Test 7: Cross-Browser Compatibility 🔄

Test in:
- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari (macOS/iOS)
- [ ] Mobile browsers (iOS Safari, Chrome Android)

### Test 8: Performance ⚡

**Metrics to Check:**
- [ ] Upload starts within 1 second
- [ ] Progress updates smoothly
- [ ] UI remains responsive during upload
- [ ] Large files (100MB+) don't freeze browser
- [ ] Multiple concurrent uploads work
- [ ] Lightbox opens instantly (<100ms)

## Debugging

### Check Backend Logs
```bash
# Terminal with backend running
# Look for:
# - "File uploaded to GCS"
# - "Uploaded to Gemini"
# - Error messages
```

### Check AI Orchestrator Logs
```bash
# Terminal with ai-orchestrator running
# Look for:
# - "Processing attachments"
# - "Uploaded attachment to Gemini"
# - Gemini API responses
```

### Check Browser Console
```bash
# F12 > Console tab
# Look for:
# - Upload progress logs
# - API request/response
# - React errors
```

### Check Network Tab
```bash
# F12 > Network tab
# Look for:
# - POST /api/v1/uploads/presigned/chat-attachment (should return 200)
# - PUT to GCS (storage.googleapis.com) (should return 200)
# - POST /api/chat (should start SSE stream)
```

## Common Issues & Solutions

### Issue: "Failed to get upload URL"
**Solution:** Check backend is running and env vars are set

### Issue: "Upload failed with status 403"
**Solution:** Check GCS credentials and bucket permissions

### Issue: "File not found in GCS"
**Solution:** Verify upload completed before sending message

### Issue: "AI doesn't mention the file"
**Solution:** Check Gemini API key and file upload logs in ai-orchestrator

### Issue: Images don't display
**Solution:** Check signed URLs are being generated (check download_url field)

### Issue: Lightbox doesn't open
**Solution:** Check browser console for React errors

## Success Criteria

All features working:
- ✅ File upload (images, videos, documents)
- ✅ Progress tracking
- ✅ Attachment preview
- ✅ Message with attachments
- ✅ AI multimodal understanding
- ✅ Image lightbox
- ✅ Video playback
- ✅ Document download
- ✅ Error handling
- ✅ Mobile responsive

## Next Steps After Testing

1. **Fix any bugs found**
2. **Add unit tests** (Jest/React Testing Library)
3. **Add E2E tests** (Playwright/Cypress)
4. **Performance optimization** (if needed)
5. **Accessibility audit** (screen readers, keyboard nav)
6. **User documentation** (help text, tooltips)
7. **Deploy to staging** for QA testing
8. **Monitor usage** and gather feedback

## Reporting Issues

When reporting bugs, include:
- Browser & OS version
- Steps to reproduce
- Expected vs actual behavior
- Screenshots/screen recording
- Console logs
- Network tab (if upload related)

---

**Happy Testing! 🚀**

For questions, see:
- Implementation docs: `MULTIMODAL_FILE_UPLOAD_PROGRESS.md`
- Frontend status: `FRONTEND_IMPLEMENTATION_STATUS.md`
- Spec: `.kiro/specs/MULTIMODAL_FILE_UPLOAD.md`
