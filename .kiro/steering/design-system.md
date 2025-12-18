---
inclusion: always
---

# AAE Design System Rules for Figma Integration

## Design System Structure

### 1. Token Definitions

**Location**: `frontend/tailwind.config.ts`
**Format**: Tailwind CSS configuration with custom tokens

```typescript
// Color tokens
colors: {
  primary: {
    50: '#eff6ff',
    500: '#3b82f6',
    900: '#1e3a8a'
  },
  secondary: {...},
  accent: {...}
}

// Typography tokens
fontFamily: {
  sans: ['Inter', 'system-ui', 'sans-serif'],
  mono: ['JetBrains Mono', 'monospace']
}

// Spacing tokens (default Tailwind scale)
spacing: {
  '0': '0px',
  '1': '0.25rem',
  '4': '1rem',
  // ... standard Tailwind spacing
}
```

**Usage Pattern**: Use Tailwind utility classes throughout components
- Colors: `bg-primary-500`, `text-secondary-600`
- Spacing: `p-4`, `m-2`, `gap-6`
- Typography: `font-sans`, `text-lg`, `font-medium`

### 2. Component Library

**Location**: `frontend/src/components/`
**Architecture**: Domain-driven component organization

```
components/
├── ui/                    # Shadcn/ui primitives
│   ├── button.tsx
│   ├── card.tsx
│   ├── input.tsx
│   └── select.tsx
├── chat/                  # Chat domain components
├── dashboard/             # Dashboard domain components
├── creatives/             # Creative management components
└── auth/                  # Authentication components
```

**Component Patterns**:
- Use `cn()` utility from `lib/utils.ts` for conditional classes
- Prefer composition over prop drilling
- Server Components by default, `'use client'` only when needed

```typescript
// Example component structure
interface ComponentProps {
  variant?: 'default' | 'secondary';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function Component({ variant = 'default', size = 'md', className, ...props }: ComponentProps) {
  return (
    <div className={cn(
      'base-styles',
      variants[variant],
      sizes[size],
      className
    )} {...props} />
  );
}
```

### 3. Frameworks & Libraries

**UI Framework**: Next.js 14 (App Router) + React 18
**Styling**: Tailwind CSS 3.4 + Shadcn/ui components
**Build System**: Next.js built-in bundler (Turbopack in dev)
**Type System**: TypeScript 5 with strict mode

**Key Dependencies**:
- `@radix-ui/*` - Accessible primitives
- `class-variance-authority` - Component variants
- `clsx` + `tailwind-merge` - Conditional styling

### 4. Asset Management

**Storage**: Google Cloud Storage (GCS) with direct upload
**Configuration**: `backend/app/core/storage.py`

```python
# Asset upload patterns
ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
```

**Frontend Usage**:
```typescript
// Image optimization with Next.js
import Image from 'next/image';

<Image
  src={assetUrl}
  alt="Description"
  width={400}
  height={300}
  className="rounded-lg"
/>
```

**CDN**: GCS serves as CDN with proper CORS configuration

### 5. Icon System

**Library**: Lucide React icons
**Location**: Imported directly in components
**Usage Pattern**:

```typescript
import { Plus, Edit, Trash2 } from 'lucide-react';

// Standard icon sizing
<Plus className="h-4 w-4" />        // Small (16px)
<Edit className="h-5 w-5" />        // Medium (20px)  
<Trash2 className="h-6 w-6" />      // Large (24px)
```

**Naming Convention**: Use semantic names from Lucide library
- Prefer: `Plus`, `Edit`, `Trash2`, `ChevronDown`
- Avoid: Custom icon components unless absolutely necessary

### 6. Styling Approach

**Methodology**: Utility-first with Tailwind CSS
**Responsive Design**: Mobile-first breakpoints

```typescript
// Responsive patterns
className="text-sm md:text-base lg:text-lg"
className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3"
className="p-4 md:p-6 lg:p-8"
```

**Global Styles**: Minimal, defined in `frontend/src/app/globals.css`
- CSS reset via Tailwind
- Custom CSS properties for theme colors
- Focus ring utilities

**Component Styling Rules**:
1. Use Tailwind utilities exclusively
2. Avoid inline styles unless absolutely necessary
3. Use `cn()` for conditional classes
4. Group related utilities logically

### 7. Project Structure

**Frontend Organization**:
```
frontend/src/
├── app/                   # Next.js App Router pages
│   ├── (auth)/           # Route groups
│   ├── dashboard/        # Dashboard pages
│   └── api/              # API routes
├── components/           # React components (domain-organized)
├── hooks/                # Custom React hooks
├── lib/                  # Utilities (api, auth, store)
└── types/                # TypeScript definitions
```

**Feature Organization**: Domain-driven, not by component type
- Group by business domain (chat, dashboard, creatives)
- Each domain has its own components, hooks, and utilities
- Shared primitives in `components/ui/`

## Figma Integration Guidelines

### Design-to-Code Conversion Rules

1. **Component Mapping**:
   - Map Figma components to existing Shadcn/ui components when possible
   - Use `Button`, `Card`, `Input`, `Select` from `components/ui/`
   - Create new components only for domain-specific patterns

2. **Styling Translation**:
   - Convert Figma colors to Tailwind color tokens
   - Use semantic color names (`primary`, `secondary`, `accent`)
   - Maintain spacing consistency with Tailwind scale

3. **Responsive Behavior**:
   - Implement mobile-first responsive design
   - Use Tailwind breakpoints: `sm:`, `md:`, `lg:`, `xl:`
   - Ensure touch-friendly interactions on mobile

4. **Accessibility Requirements**:
   - Maintain proper heading hierarchy (`h1`, `h2`, `h3`)
   - Include `alt` text for images
   - Ensure keyboard navigation works
   - Use semantic HTML elements

### Code Connect Mapping

**Target Components for Mapping**:
- `components/ui/*` - Base UI primitives
- `components/chat/*` - Chat interface components  
- `components/dashboard/*` - Dashboard widgets
- `components/creatives/*` - Creative management UI

**Mapping Strategy**:
1. Start with most reused components (Button, Card, Input)
2. Map domain-specific components (ChatWindow, MetricCard)
3. Establish consistent naming between Figma and code

### Asset Integration

**Image Handling**:
- Export images as WebP when possible
- Use appropriate sizing (1x, 2x for retina)
- Implement lazy loading with Next.js Image component

**Icon Integration**:
- Prefer Lucide icons over custom SVGs
- Maintain consistent sizing (16px, 20px, 24px)
- Use semantic color classes

## Quality Checklist

When integrating Figma designs:

- [ ] Components use existing Shadcn/ui primitives
- [ ] Styling uses Tailwind utility classes
- [ ] Colors match defined token system
- [ ] Responsive behavior implemented
- [ ] Accessibility requirements met
- [ ] TypeScript types properly defined
- [ ] Server/Client components correctly designated
- [ ] Assets optimized and properly referenced

## Common Patterns

### Chat Interface Components
```typescript
// Chat message bubble pattern
<div className={cn(
  "max-w-[80%] rounded-lg p-3",
  isUser ? "ml-auto bg-primary-500 text-white" : "bg-gray-100"
)}>
  {content}
</div>
```

### Dashboard Metric Cards
```typescript
// Metric card pattern
<Card className="p-6">
  <div className="flex items-center justify-between">
    <div>
      <p className="text-sm font-medium text-gray-600">{label}</p>
      <p className="text-2xl font-bold">{value}</p>
    </div>
    <Icon className="h-8 w-8 text-gray-400" />
  </div>
</Card>
```

### Form Components
```typescript
// Form field pattern
<div className="space-y-2">
  <Label htmlFor={id}>{label}</Label>
  <Input
    id={id}
    type={type}
    placeholder={placeholder}
    className="w-full"
  />
</div>
```