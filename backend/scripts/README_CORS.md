# GCS 存储桶 CORS 配置说明

## 问题背景

当前端尝试直接上传文件到 GCS 时，浏览器会因为 CORS（跨域资源共享）限制而阻止请求。错误信息类似：
```
Access to XMLHttpRequest at 'https://storage.googleapis.com/...' has been blocked by CORS policy
Referrer Policy: strict-origin-when-cross-origin
```

## 解决方案

需要为 GCS 存储桶配置 CORS 策略，允许前端域名直接上传文件。

## 配置文件

`configure_gcs_cors.json` 包含 CORS 配置：
- **允许的域名**：localhost:3000（开发环境）、生产域名
- **允许的方法**：GET, PUT, POST, HEAD
- **允许的响应头**：Content-Type, Content-Length 等
- **缓存时间**：3600 秒（1 小时）

## 配置存储桶名称

存储桶名称从配置文件读取，而不是硬编码。在 `backend/.env` 文件中配置：

```env
GCS_BUCKET_UPLOADS_TEMP=aae-user-uploads-temp  # 临时文件存储桶
GCS_BUCKET_UPLOADS=aae-user-uploads            # 永久文件存储桶
```

如果需要使用不同的存储桶名称，只需修改 `.env` 文件即可，无需修改代码。

## 使用方法

### 方法 1：使用 gcloud CLI（推荐）

```bash
# 进入脚本目录
cd backend/scripts

# 运行脚本（会自动从 .env 读取存储桶名称）
./apply_gcs_cors.sh
```

**前提条件**：
- 已安装 gcloud CLI：https://cloud.google.com/sdk/docs/install
- 已认证并设置默认项目：
  ```bash
  gcloud auth login
  gcloud config set project YOUR_PROJECT_ID
  ```
- 确保 `backend/.env` 文件中配置了存储桶名称

### 方法 2：使用 Python SDK

```bash
# 进入脚本目录
cd backend/scripts

# 确保已激活虚拟环境
source ../venv/bin/activate

# 运行 Python 脚本（会从配置文件读取存储桶名称）
python apply_gcs_cors.py
```

**前提条件**：
- 已设置 GCS 凭证环境变量：
  ```bash
  export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
  # 或
  export GCS_CREDENTIALS_PATH=/path/to/service-account-key.json
  ```
- 确保 `backend/.env` 文件中配置了存储桶名称

### 方法 3：手动配置（使用 gcloud 命令）

如果需要手动配置，替换 `YOUR-TEMP-BUCKET` 和 `YOUR-PERM-BUCKET` 为你的实际存储桶名称：

```bash
# 配置临时存储桶（从 .env 中的 GCS_BUCKET_UPLOADS_TEMP）
gcloud storage buckets update gs://YOUR-TEMP-BUCKET \
    --cors-file=backend/scripts/configure_gcs_cors.json

# 配置永久存储桶（从 .env 中的 GCS_BUCKET_UPLOADS）
gcloud storage buckets update gs://YOUR-PERM-BUCKET \
    --cors-file=backend/scripts/configure_gcs_cors.json
```

例如，如果使用默认配置：
```bash
gcloud storage buckets update gs://aae-user-uploads-temp \
    --cors-file=backend/scripts/configure_gcs_cors.json
gcloud storage buckets update gs://aae-user-uploads \
    --cors-file=backend/scripts/configure_gcs_cors.json
```

## 验证配置

配置完成后，可以验证 CORS 设置是否生效（使用你配置的实际存储桶名称）：

```bash
# 查看临时存储桶的 CORS 配置
gcloud storage buckets describe gs://YOUR-TEMP-BUCKET \
    --format='json(cors_config)'

# 查看永久存储桶的 CORS 配置
gcloud storage buckets describe gs://YOUR-PERM-BUCKET \
    --format='json(cors_config)'
```

例如，使用默认配置：
```bash
gcloud storage buckets describe gs://aae-user-uploads-temp \
    --format='json(cors_config)'
gcloud storage buckets describe gs://aae-user-uploads \
    --format='json(cors_config)'
```

## 测试直接上传

配置完成后，在前端：
1. 打开 http://localhost:3000
2. 点击聊天界面的附件按钮
3. 选择文件上传
4. 检查浏览器网络面板，应该看到：
   - `POST /api/v1/uploads/presigned/generate` - 获取签名 URL
   - `PUT https://storage.googleapis.com/...` - 直接上传到 GCS（不再报 CORS 错误）

## 生产环境注意事项

在 `configure_gcs_cors.json` 中添加你的生产域名：

```json
{
  "origin": [
    "http://localhost:3000",
    "https://yourdomain.com",
    "https://www.yourdomain.com"
  ],
  ...
}
```

然后重新运行配置脚本。

## 安全建议

1. **限制域名**：只添加你控制的域名到 `origin` 列表
2. **使用 HTTPS**：生产环境应该只允许 HTTPS 域名
3. **定期审查**：定期检查 CORS 配置，移除不再使用的域名
4. **监控上传**：启用 GCS 审计日志，监控异常上传行为

## 故障排查

### 错误 1：gcloud 命令未找到
```
Error: gcloud CLI is not installed
```
**解决**：安装 gcloud CLI - https://cloud.google.com/sdk/docs/install

### 错误 2：权限不足
```
Error: Permission denied
```
**解决**：确保你的 GCP 账号有 Storage Admin 权限

### 错误 3：存储桶不存在
```
Error: Bucket not found
```
**解决**：
1. 检查存储桶名称是否正确
2. 确保已创建存储桶：
   ```bash
   gcloud storage buckets create gs://aae-user-uploads-temp --location=us-central1
   gcloud storage buckets create gs://aae-user-uploads --location=us-central1
   ```

## 相关文档

- [GCS CORS Configuration](https://cloud.google.com/storage/docs/cross-origin)
- [Direct Upload Flow](../../frontend/DIRECT_UPLOAD_EXAMPLE.md)
- [Gemini Files API](https://ai.google.dev/gemini-api/docs/files)
