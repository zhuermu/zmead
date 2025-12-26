# Beta Access Control Implementation

## 概述

本文档说明了在 AAE 平台中实施的内测阶段用户白名单和超级管理员功能。

## 功能特性

### 1. 用户审批机制
- 新注册用户默认处于"待审核"状态 (`is_approved=False`)
- 未经审核的用户无法登录使用系统
- 用户在待审核期间会看到友好的等待提示页面

### 2. 超级管理员
- 通过配置文件设置管理员邮箱列表
- 超级管理员登录时自动批准 (`is_approved=True`)
- 拥有用户管理权限，可以批准/拒绝其他用户

### 3. 用户管理面板
- `/admin/users` - 超级管理员专用用户管理界面
- 功能包括：
  - 查看所有用户列表
  - 按审核状态筛选（全部/待审核/已批准）
  - 搜索用户（按邮箱或名称）
  - 批准/撤销用户访问权限
  - 查看平台统计数据

## 技术实现

### Backend Changes

#### 1. 数据库变更
- **文件**: `backend/app/models/user.py`
- **变更**: 添加 `is_approved` 字段
  ```python
  is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
  ```
- **迁移**: `backend/alembic/versions/5f92bfba0ec7_add_is_approved_field_to_users_table.py`

#### 2. 配置文件更新
- **文件**: `backend/app/core/config.py`
- **变更**: 添加超级管理员邮箱配置
  ```python
  super_admin_emails: str = Field(default="")

  @computed_field
  @property
  def super_admin_list(self) -> list[str]:
      """Parse comma-separated super admin emails."""
      if not self.super_admin_emails:
          return []
      return [email.strip() for email in self.super_admin_emails.split(",") if email.strip()]
  ```

#### 3. Schema 更新
- **文件**: `backend/app/schemas/user.py` 和 `backend/app/schemas/auth.py`
- **变更**: 添加用户管理相关 schemas
  - `AdminUserListItem` - 管理员用户列表项
  - `AdminUserListResponse` - 分页用户列表响应
  - `UserApprovalRequest` - 用户审批请求
  - `UserResponse` 添加 `is_approved` 和 `is_super_admin` 字段

#### 4. 认证流程更新
- **文件**: `backend/app/services/auth.py`
- **变更**:
  - `get_or_create_user` 方法：超级管理员自动批准
  - `authenticate_with_google` 方法：检查用户审批状态，未批准用户返回 403 错误

#### 5. 新增 API 端点
- **文件**: `backend/app/api/v1/admin.py`
- **端点**:
  - `GET /api/v1/admin/users` - 获取用户列表（分页、筛选、搜索）
  - `PUT /api/v1/admin/users/{user_id}/approval` - 批准/拒绝用户
  - `GET /api/v1/admin/users/{user_id}` - 获取用户详情
  - `GET /api/v1/admin/stats` - 获取平台统计

#### 6. 权限控制
- **文件**: `backend/app/api/deps.py`
- **变更**: 添加超级管理员验证依赖
  ```python
  def is_super_admin(email: str) -> bool
  async def get_current_super_admin(current_user: CurrentUser) -> User
  CurrentSuperAdmin = Annotated[User, Depends(get_current_super_admin)]
  ```

### Frontend Changes

#### 1. 类型定义更新
- **文件**: `frontend/src/types/index.ts`
- **变更**: User 接口添加字段
  ```typescript
  isApproved: boolean;
  isSuperAdmin: boolean;
  ```

#### 2. Auth Hook
- **文件**: `frontend/src/hooks/useAuth.ts`
- **新增**: 创建 useAuth hook 用于获取当前用户信息

#### 3. 用户管理面板
- **文件**: `frontend/src/app/admin/users/page.tsx`
- **功能**:
  - 用户列表展示
  - 审批状态筛选
  - 搜索功能
  - 批准/撤销操作
  - 统计数据展示

#### 4. 待审核页面
- **文件**: `frontend/src/app/auth/pending/page.tsx`
- **功能**: 显示友好的待审核提示信息

#### 5. 登录回调更新
- **文件**: `frontend/src/app/auth/callback/page.tsx`
- **变更**: 处理 `PENDING_APPROVAL` 错误，重定向到待审核页面

## 配置指南

### 1. 设置超级管理员

编辑 `backend/.env` 文件，添加：

```env
# Beta Access Control
# Super Admin Emails - Comma-separated list of admin emails
SUPER_ADMIN_EMAILS=admin@company.com,admin2@company.com
```

### 2. 应用数据库迁移

```bash
cd backend
source venv/bin/activate
alembic upgrade head
```

### 3. 重启服务

```bash
# 重启 backend
cd backend && uvicorn app.main:app --reload --port 8000

# 重启 frontend
cd frontend && npm run dev
```

## 使用流程

### 超级管理员首次登录
1. 配置超级管理员邮箱在 `.env` 文件中
2. 使用配置的邮箱通过 Google OAuth 登录
3. 系统自动将该用户标记为已批准
4. 登录成功后可访问 `/admin/users` 管理页面

### 普通用户注册流程
1. 用户通过 Google OAuth 登录
2. 系统创建用户账号，状态为"待审核"
3. 显示"账号等待审核中"页面
4. 超级管理员在管理面板批准该用户
5. 用户再次登录后可正常使用系统

### 管理员批准用户
1. 登录后访问 `/admin/users`
2. 在待审核列表中找到目标用户
3. 点击"Approve"按钮批准用户
4. 用户立即获得访问权限

## API 错误码

### PENDING_APPROVAL (HTTP 403)
```json
{
  "detail": {
    "code": "PENDING_APPROVAL",
    "message": "Your account is pending approval. Please wait for an administrator to approve your access.",
    "user_email": "user@example.com"
  }
}
```

## 安全注意事项

1. **超级管理员配置**
   - 超级管理员邮箱列表存储在环境变量中
   - 建议在生产环境使用密钥管理服务（如 AWS Secrets Manager）

2. **权限验证**
   - 所有管理员 API 端点都通过 `CurrentSuperAdmin` 依赖进行验证
   - 不允许修改超级管理员的审批状态

3. **认证流程**
   - 未批准用户不会获得 JWT token
   - 前端无法绕过审批检查

## 测试建议

### 1. 超级管理员功能测试
```bash
# 设置测试管理员邮箱
SUPER_ADMIN_EMAILS=test-admin@example.com

# 测试登录
# 验证自动批准
# 访问管理面板
```

### 2. 普通用户审批流程测试
```bash
# 使用非管理员邮箱登录
# 验证显示待审核页面
# 管理员批准后再次登录
# 验证正常访问
```

### 3. API 端点测试
```bash
# 获取用户列表
curl -H "Authorization: Bearer {admin_token}" \
  http://localhost:8000/api/v1/admin/users

# 批准用户
curl -X PUT \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{"approved": true}' \
  http://localhost:8000/api/v1/admin/users/{user_id}/approval

# 获取统计
curl -H "Authorization: Bearer {admin_token}" \
  http://localhost:8000/api/v1/admin/stats
```

## 已知限制

1. 超级管理员邮箱列表只能通过修改环境变量更新（需要重启服务）
2. 当前没有审批通知机制（可在后续迭代中添加邮件通知）
3. 审批操作没有审计日志（建议在生产环境添加）

## 后续优化建议

1. **邮件通知**
   - 用户注册时通知管理员
   - 审批通过后通知用户

2. **审计日志**
   - 记录所有审批操作
   - 包括操作人、时间、IP 地址

3. **批量操作**
   - 支持批量批准用户
   - 支持批量导入白名单

4. **自助申请**
   - 添加申请理由字段
   - 管理员可查看申请理由

## 相关文件清单

### Backend
- `backend/app/models/user.py` - 用户模型
- `backend/app/core/config.py` - 配置文件
- `backend/app/schemas/user.py` - 用户 schemas
- `backend/app/schemas/auth.py` - 认证 schemas
- `backend/app/services/auth.py` - 认证服务
- `backend/app/api/deps.py` - API 依赖
- `backend/app/api/v1/admin.py` - 管理员 API
- `backend/app/api/v1/auth.py` - 认证 API
- `backend/app/api/v1/router.py` - 路由配置
- `backend/alembic/versions/5f92bfba0ec7_*.py` - 数据库迁移
- `backend/.env.example` - 环境变量示例

### Frontend
- `frontend/src/types/index.ts` - 类型定义
- `frontend/src/hooks/useAuth.ts` - Auth hook
- `frontend/src/app/admin/users/page.tsx` - 用户管理面板
- `frontend/src/app/auth/pending/page.tsx` - 待审核页面
- `frontend/src/app/auth/callback/page.tsx` - 登录回调

## 总结

本次实现完整地建立了内测阶段的访问控制机制，包括：
- ✅ 用户白名单审批流程
- ✅ 超级管理员配置和自动批准
- ✅ 完整的用户管理界面
- ✅ 友好的用户体验（待审核提示页面）
- ✅ 安全的权限验证机制

系统现在可以安全地部署到内测环境，只允许经过审批的用户访问平台。
