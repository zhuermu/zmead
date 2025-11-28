# 开发环境认证配置

## 概述

为了方便本地开发，系统提供了一个开关来跳过 Google OAuth 登录流程。

## 配置方法

### 1. 启用开发模式认证

在 `backend/.env` 文件中设置：

```bash
DISABLE_AUTH=true
```

### 2. 重启后端服务

修改环境变量后需要重启 FastAPI 服务。

## 功能说明

### 自动创建测试用户

当 `DISABLE_AUTH=true` 时：

- 所有需要认证的 API 端点会自动使用测试用户
- 测试用户信息：
  - Email: `dev@test.local`
  - Display Name: `Dev User`
  - OAuth Provider: `dev`
  - 初始积分: 10,000（用于测试）

### 开发登录端点

提供了专门的开发登录端点：

```bash
POST /api/v1/auth/dev/login
```

返回：
```json
{
  "tokens": {
    "access_token": "...",
    "refresh_token": "...",
    "expires_in": 1800
  },
  "user": {
    "id": 1,
    "email": "dev@test.local",
    "display_name": "Dev User",
    ...
  }
}
```

### 检查认证状态

```bash
GET /api/v1/auth/dev/status
```

返回：
```json
{
  "disable_auth": true
}
```

## 前端集成

在前端代码中，可以检查开发模式并使用简化的登录流程：

```typescript
// 检查是否启用开发模式
const response = await fetch('/api/v1/auth/dev/status');
const { disable_auth } = await response.json();

if (disable_auth) {
  // 使用开发登录
  const loginResponse = await fetch('/api/v1/auth/dev/login', {
    method: 'POST'
  });
  const { tokens, user } = await loginResponse.json();
  // 保存 tokens...
} else {
  // 使用正常的 Google OAuth 流程
  window.location.href = '/api/v1/auth/oauth/google';
}
```

## 安全注意事项

⚠️ **重要**: 

- 此功能仅用于本地开发环境
- 生产环境必须设置 `DISABLE_AUTH=false` 或不设置该变量
- 开发登录端点在生产环境会返回 403 错误
- 确保 `.env` 文件不会被提交到版本控制系统

## 使用场景

1. **本地开发**: 快速测试功能，无需每次都进行 OAuth 流程
2. **API 测试**: 使用 Postman/curl 等工具测试 API
3. **自动化测试**: 在测试环境中跳过复杂的认证流程
4. **前端开发**: 前端开发者可以独立工作，无需配置 OAuth

## 恢复正常认证

要恢复正常的 Google OAuth 认证：

1. 在 `.env` 中设置 `DISABLE_AUTH=false` 或删除该行
2. 重启后端服务
3. 确保 Google OAuth 配置正确（CLIENT_ID, CLIENT_SECRET, REDIRECT_URI）
