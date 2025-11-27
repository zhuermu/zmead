# Admin Pages

This directory contains admin-only pages for managing the AAE platform.

## Pages

### Credit Configuration (`/admin/config`)

Manage credit rates and pricing for AI operations.

**Features:**
- View and edit all credit configuration parameters
- AI model rates (Gemini Flash, Gemini Pro)
- Operation rates (image generation, video generation, landing pages, etc.)
- Registration bonus credits
- View change history with timestamps and admin user tracking
- Confirmation dialog before saving changes
- Non-retroactive changes (only affect new operations)

**Access:**
- This page is currently accessible to all authenticated users
- In production, add admin role verification to the backend endpoints
- See TODO comments in `backend/app/api/v1/credits.py`

**API Endpoints:**
- `GET /api/v1/credits/config` - Get current configuration
- `PUT /api/v1/credits/config` - Update configuration
- `GET /api/v1/credits/config/history` - Get change history

## Security Notes

⚠️ **Important**: The admin endpoints currently do not have role-based access control. Before deploying to production:

1. Add an `is_admin` field to the User model
2. Implement admin role verification in the API endpoints
3. Add middleware to protect admin routes in the frontend
4. Consider adding audit logging for all admin actions

See the TODO comments in the codebase for specific locations that need updates.
