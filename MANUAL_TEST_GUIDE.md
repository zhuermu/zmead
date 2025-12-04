# 手动测试指南 - 多模态文件上传功能
**日期**: 2025-12-04
**状态**: 准备测试

## 前置条件 ✅

### 服务状态
所有服务已启动并健康：
```bash
✅ Frontend:          http://localhost:3000 (健康)
✅ Backend:           http://localhost:8000 (健康)
✅ AI Orchestrator:   http://localhost:8001 (健康)
   - Redis:           健康
   - MCP连接:         健康
   - Gemini API:      健康
```

### 已修复的Bug
1. ✅ Backend缺失函数导入
2. ✅ CDN配置错误
3. ✅ 前端使用错误的上传实现
4. ✅ SessionId未定义错误

---

## 测试场景 1: 图片上传和AI理解 🖼️

### 目标
验证图片能够：
1. 成功上传到GCS
2. 在对话框中显示
3. 被AI理解和分析

### 测试步骤

#### 1. 打开Dashboard
```
打开浏览器访问: http://localhost:3000/dashboard
```

#### 2. 创建新对话
- 点击侧边栏的 "新建对话" 按钮
- 或使用已有对话

#### 3. 上传测试图片
**方式A - 点击上传**:
- 点击输入框左侧的 📎 按钮
- 选择图片文件（推荐：`/tmp/test-image.svg`）

**方式B - 拖拽上传**:
- 将图片文件拖拽到对话区域
- 看到虚线边框时释放

#### 4. 验证上传预览
**预期结果**:
- ✅ 输入框上方显示图片预览卡片
- ✅ 显示图片缩略图
- ✅ 显示文件名和大小
- ✅ 显示绿色✓成功图标
- ✅ 有移除按钮（悬停时显示）

**失败标志**:
- ❌ 显示上传失败错误
- ❌ 显示旋转加载图标一直不停
- ❌ 控制台有错误信息

#### 5. 发送消息询问图片
输入以下任一问题：
```
这张图片是什么？
```
```
图片里有什么颜色？
```
```
请描述这张图片的内容
```

#### 6. 验证消息发送
**预期结果**:
- ✅ 用户消息立即显示在对话框
- ✅ 用户消息下方显示图片
- ✅ AI助手消息开始流式输出
- ✅ AI能准确描述图片内容

**对于 `/tmp/test-image.svg`，AI应该能识别**:
- 蓝色背景 (#4F46E5)
- 中文文字 "测试图片"
- 英文文字 "Test Image for Upload"
- 黄色圆圈 (#FCD34D)

#### 7. 检查后端日志
```bash
# 查看最近的backend日志
cd /Users/xiaowely/ws/git/zmead
# 后端应该显示:
# - 收到文件上传请求
# - GCS上传成功
# - Gemini File API上传成功
```

---

## 测试场景 2: 多文件上传 📂

### 目标
验证可以同时上传多个文件

### 测试步骤

#### 1. 创建多个测试文件
```bash
# 如果还没有测试图片
echo '<svg width="200" height="200"><rect width="200" height="200" fill="red"/><text x="50%" y="50%" text-anchor="middle" fill="white" font-size="20">Image 1</text></svg>' > /tmp/test-img-1.svg

echo '<svg width="200" height="200"><rect width="200" height="200" fill="green"/><text x="50%" y="50%" text-anchor="middle" fill="white" font-size="20">Image 2</text></svg>' > /tmp/test-img-2.svg

echo "This is a test document for multimodal upload testing." > /tmp/test-doc.txt
```

#### 2. 上传多个文件
- 点击 📎 按钮
- 按住 Cmd (Mac) 或 Ctrl (Windows) 选择多个文件
- 或拖拽多个文件到对话区域

#### 3. 验证预览
**预期结果**:
- ✅ 所有文件都显示预览卡片
- ✅ 每个文件独立显示，排列整齐
- ✅ 可以单独移除某个文件

#### 4. 发送消息
```
请分别描述这些文件的内容
```

#### 5. 验证AI响应
**预期结果**:
- ✅ AI能识别并描述所有文件
- ✅ 对每个文件都有独立分析

---

## 测试场景 3: 视频上传（如果有视频文件）🎥

### 测试步骤

#### 1. 准备视频文件
- 使用任何小于200MB的视频文件
- 支持格式: mp4, mov, webm, avi

#### 2. 上传视频
- 拖拽或点击上传视频文件

#### 3. 验证预览
**预期结果**:
- ✅ 显示视频文件图标（紫色）
- ✅ 显示文件名和大小
- ✅ 成功图标显示

#### 4. 发送消息
```
这个视频里有什么内容？
```

#### 5. 验证AI响应
**预期结果**:
- ✅ AI能分析视频内容
- ✅ AI能描述视频中的场景和动作

---

## 测试场景 4: 错误处理 ⚠️

### 4.1 文件过大
**测试**:
- 尝试上传超过20MB的图片
- 或超过200MB的视频

**预期结果**:
- ❌ 显示错误提示
- ✅ 错误信息清晰（"文件过大，图片最大20MB"）
- ✅ 其他文件不受影响

### 4.2 不支持的文件类型
**测试**:
- 尝试上传 .exe 或其他不支持的文件

**预期结果**:
- ❌ 显示错误提示
- ✅ 错误信息说明不支持的类型

### 4.3 网络中断
**测试**:
- 在上传过程中断开网络
- 或关闭backend服务

**预期结果**:
- ❌ 显示上传失败
- ✅ 用户可以重试

---

## 测试场景 5: UI/UX功能 ✨

### 5.1 拖拽区域高亮
**测试**:
- 拖拽文件到对话区域但不释放

**预期结果**:
- ✅ 对话区域显示虚线边框
- ✅ 背景色变化提示可拖放

### 5.2 移除文件
**测试**:
- 上传文件后，悬停在预览卡片上
- 点击移除按钮

**预期结果**:
- ✅ 文件从预览中移除
- ✅ 其他文件不受影响

### 5.3 上传进度
**测试**:
- 上传大文件时观察进度

**预期结果**:
- ✅ 显示上传百分比（如果是大文件）
- ✅ 成功后显示✓图标

### 5.4 消息历史显示
**测试**:
- 发送带图片的消息后
- 刷新页面或切换会话后回来

**预期结果**:
- ✅ 图片依然显示在历史消息中
- ✅ 图片可以正常查看

---

## 验收标准 ✅

### 必须通过（P0）
- [ ] 图片能成功上传
- [ ] 图片在对话中显示
- [ ] AI能理解图片内容
- [ ] 多文件上传正常工作
- [ ] 文件大小限制生效
- [ ] 不支持的文件类型被拒绝

### 应该通过（P1）
- [ ] 视频上传和分析
- [ ] 文档上传和分析
- [ ] 上传进度显示
- [ ] 拖拽上传体验流畅
- [ ] 错误提示清晰友好

### 最好通过（P2）
- [ ] 刷新后图片依然显示
- [ ] 移除文件功能正常
- [ ] UI动画流畅
- [ ] 手机端响应式适配

---

## 调试技巧 🔍

### 检查前端控制台
```
打开浏览器开发者工具 (F12)
查看 Console 标签页
```

**关键日志**:
```
[useFileUpload] Uploading file: xxx.png
[useFileUpload] Upload success
[useChat] Sending message with attachments
```

### 检查网络请求
```
开发者工具 → Network 标签页
```

**关键请求**:
```
POST /api/v1/uploads/presigned/chat-attachment  (获取上传URL)
PUT https://storage.googleapis.com/...          (上传到GCS)
POST /api/chat                                   (发送消息)
```

### 检查后端日志
```bash
# Backend日志
cd /Users/xiaowely/ws/git/zmead/backend
# 在运行uvicorn的终端查看输出

# AI Orchestrator日志
cd /Users/xiaowely/ws/git/zmead/ai-orchestrator
# 在运行uvicorn的终端查看输出
```

**正常日志应包含**:
```
INFO: Presigned URL generated for file: xxx.png
INFO: File uploaded to GCS: 2/chat-attachments/session-xxx/xxx.png
INFO: Gemini file uploaded: files/xxx
INFO: Chat message received with 1 attachments
```

---

## 常见问题 ❓

### Q1: 图片上传后不显示
**排查**:
1. 检查前端控制台是否有错误
2. 检查Network标签，上传请求是否成功
3. 检查 `attachments` 数组是否包含图片信息
4. 验证 `preview_url` 是否有效

### Q2: AI说看不到图片
**排查**:
1. 检查后端日志，Gemini File API是否上传成功
2. 检查请求格式，应该是 `attachments` 而不是 `tempAttachments`
3. 检查附件格式，应该包含 `gcs_path` 字段

### Q3: 上传一直显示加载中
**排查**:
1. 检查Network请求是否失败
2. 检查GCS credentials是否配置正确
3. 检查文件大小是否超限
4. 查看后端日志具体错误

### Q4: 刷新后图片消失
**检查**:
1. 数据库是否保存了 `download_url`
2. Signed URL是否过期
3. 前端是否正确重新获取 signed URL

---

## 测试报告模板

```markdown
## 测试执行记录
**日期**: 2025-12-04
**测试人员**: [您的名字]
**浏览器**: Chrome/Safari/Firefox [版本号]

### 场景1: 图片上传
- [ ] 上传成功: ✅/❌
- [ ] 预览显示: ✅/❌
- [ ] AI理解: ✅/❌
- 备注: _______________________

### 场景2: 多文件上传
- [ ] 上传成功: ✅/❌
- [ ] 全部预览: ✅/❌
- [ ] AI分析: ✅/❌
- 备注: _______________________

### 场景3: 视频上传
- [ ] 上传成功: ✅/❌
- [ ] 预览显示: ✅/❌
- [ ] AI分析: ✅/❌
- 备注: _______________________

### 场景4: 错误处理
- [ ] 文件过大拒绝: ✅/❌
- [ ] 类型不支持拒绝: ✅/❌
- [ ] 错误提示清晰: ✅/❌
- 备注: _______________________

### 场景5: UI/UX
- [ ] 拖拽高亮: ✅/❌
- [ ] 移除文件: ✅/❌
- [ ] 上传进度: ✅/❌
- [ ] 历史显示: ✅/❌
- 备注: _______________________

### 整体评价
- 通过测试: ✅/❌
- 发现bug数: ___
- 严重程度: P0/P1/P2
- 建议: _______________________
```

---

## 快速测试命令

### 验证测试图片存在
```bash
ls -lh /tmp/test-image.svg
# 如果不存在，重新创建
cat > /tmp/test-image.svg << 'EOF'
<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
  <rect width="400" height="300" fill="#4F46E5"/>
  <text x="50%" y="40%" text-anchor="middle" fill="white" font-size="32" font-family="Arial">
    测试图片
  </text>
  <text x="50%" y="55%" text-anchor="middle" fill="white" font-size="20" font-family="Arial">
    Test Image for Upload
  </text>
  <circle cx="200" cy="200" r="40" fill="#FCD34D"/>
</svg>
EOF
```

### 验证服务健康
```bash
curl http://localhost:3000/dashboard | head -5
curl http://localhost:8000/health
curl http://localhost:8001/health
```

### 监控实时日志
```bash
# 在不同终端窗口运行
# Terminal 1: Backend logs
cd /Users/xiaowely/ws/git/zmead/backend && tail -f nohup.out

# Terminal 2: AI Orchestrator logs
cd /Users/xiaowely/ws/git/zmead/ai-orchestrator && tail -f nohup.out

# Terminal 3: Frontend logs
cd /Users/xiaowely/ws/git/zmead/frontend && tail -f nohup.out
```

---

**准备就绪！现在可以开始测试了。** 🚀

打开浏览器访问: http://localhost:3000/dashboard
