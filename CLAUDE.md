# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **Apolo Launchpad**, a Next.js 15 application that serves as a web-based portal for managing cloud-native applications. It provides a user interface for browsing, accessing, and managing applications deployed on Kubernetes infrastructure. The app uses NextAuth for authentication via Keycloak and communicates with a backend API server.

## Key Development Commands

```bash
# Development
npm run dev          # Start development server with Turbopack (http://localhost:3000)

# Building
npm run build        # Production build

# Linting
npm run lint         # Run both TypeScript and ESLint checks
npm run lint:ts      # TypeScript type checking only (tsc --noEmit)
npm run lint:eslint  # ESLint only (checks ./src directory)

# Production
npm run start        # Start production server
```

## Architecture Overview

### Authentication Flow

The application uses a custom authentication system built on NextAuth with Keycloak:

1. **Dynamic Configuration**: Authentication config is fetched at runtime from the backend API (`/config` endpoint) rather than being hardcoded. This is cached in `src/features/auth.feature.ts:10`.

2. **Token Management**: JWT tokens are automatically refreshed before expiration via `refreshAccessToken()` in `src/features/auth.feature.ts:63`.

3. **Middleware Protection**: All routes except `/auth` require authentication (see `src/middleware.ts:9`). Unauthenticated users are redirected to `/auth`, authenticated users accessing `/auth` are redirected to `/apps`.

4. **Multi-Environment URLs**: The app dynamically determines its URLs at runtime:
   - In localhost development: API calls are proxied to `https://launchpad.apps.dev.apolo.us`
   - In production: API hostname is derived by prefixing `-api` to the web hostname (see `src/utils/helpers/getSiteUrl.ts:33`)

### API Request Pattern

All API requests use the unified `request()` function in `src/utils/helpers/request.ts:65`, which:
- Automatically detects client vs server context
- Injects the appropriate authentication token
- Handles errors consistently
- Prepends the correct API base URL

### Data Flow Architecture

1. **Server Components**: Pages like `src/app/apps/AppsPage.tsx:8` fetch data directly using `request()` at build/render time
2. **Formatting Layer**: API responses (typically snake_case) are converted to camelCase via `formatToCamelCase()` before being passed to components
3. **Type Safety**: All API responses and data structures have TypeScript types in `src/types/`

### Component Organization

- `src/components/Shared/`: Reusable UI primitives (Button, Modal, Table, Fields, etc.)
- `src/components/Ui/`: Application-specific composed components (Layout, LogoutButton, etc.)
- `src/components/Apps/`: App-specific components for the applications listing
- `src/components/Modals/`: Modal dialogs
- `src/components/Theme/`: Theming components (logo, container)

### Styling System

The project uses Tailwind CSS with extensive custom configuration:

- **Custom Typography Scale**: Uses semantic font sizes (h0-h7, headline, body, footnote, caption, button) defined in `tailwind.config.ts:4`
- **Color System**: Custom palette with neural grays, system colors (error/warning/success), and brand colors (primary/secondary/rebecca)
- **Responsive Breakpoints**: Custom breakpoints (sm: ≤600px, md: 601-1024px, lg: ≥1025px, plus hdp and hd variants)
- **Utilities**: `clsx` for conditional classes, `tailwind-merge` for class merging, `tailwind-variants` for variant-based styling

### Path Aliases (tsconfig.json)

The project uses extensive path aliases for cleaner imports:

```typescript
@actions/*      → src/actions/*
@components     → src/components (or @components/* for subpaths)
@constants      → src/constants
@features       → src/features
@typings        → src/types
@utils          → src/utils
@styles/*       → src/styles/*
```

Always use these aliases in imports rather than relative paths.

### State Management

- **nuqs**: URL-based state management (see `NuqsAdapter` in root layout)
- **use-immer**: Immutable state updates using Immer
- **React 19**: Uses the latest React features

### Error Monitoring

The application integrates Sentry for error tracking and performance monitoring. Configuration is in `next.config.ts:20` with automatic source map uploads and breadcrumb tracking.

## Important Patterns

### Environment-Aware URL Resolution

The app needs to work both in local development (proxying to dev.apolo.us) and in production (using hostname-based API discovery). Always use `getSiteUrl()` and `getServerApiUrl()` from `src/utils/helpers/getSiteUrl.ts` rather than hardcoding URLs.

### Server vs Client Components

Next.js 15 App Router defaults to Server Components. Be mindful of:
- Use `'use client'` directive only when needed (hooks, event handlers, browser APIs)
- Keep data fetching in Server Components when possible
- Use `request()` which automatically handles server vs client contexts

### Type Definitions in dev-types/

The `src/dev-types/` directory contains augmented type definitions for:
- NextAuth session types (`next-auth.d.ts`)
- React types (`react-types.d.ts`, `react-app-env.d.ts`)
- Day.js plugin types (`dayjs-types.d.ts`)

These extend library types to match the application's usage patterns.

## Common Development Workflows

### Adding a New Page

1. Create page in `src/app/[route]/page.tsx` (or `page.ts` if re-exporting)
2. If the page needs metadata, export `generateMetadata()` function
3. Create the actual component in a separate file (e.g., `[Route]Page.tsx`)
4. Add route constant to `src/constants/path.constants.ts`
5. Update middleware matcher if the route needs special auth handling

### Adding a New Component

1. Create component in appropriate directory under `src/components/`
2. Export from the directory's `index.ts` for cleaner imports
3. Use path aliases (@components) in imports
4. Apply Tailwind classes using the custom design system tokens
5. Consider using `tailwind-variants` for components with multiple visual variants

### Working with API Data

1. Define TypeScript types in `src/types/`
2. Use `request<YourType>()` for API calls
3. Apply `formatToCamelCase()` if the API returns snake_case
4. Handle errors gracefully (API calls can fail in development if backend is unavailable)

### Testing Considerations

Currently, the project doesn't have a test setup configured. When adding tests:
- Consider Jest with React Testing Library for component tests
- Use `@testing-library/react` for user-centric testing
- Mock the `request()` utility to avoid live API calls
- Test both authenticated and unauthenticated states

## Configuration Files

- `.env.example`: Required environment variables (ENVIRONMENT, SENTRY_AUTH_TOKEN, SENTRY_DSN, NEXTAUTH_SECRET)
- `next.config.ts`: Next.js configuration with Sentry integration
- `tailwind.config.ts`: Extensive Tailwind customization
- `tsconfig.json`: TypeScript configuration with path aliases

## Notes on Dependencies

- **FontAwesome Pro**: The project uses FontAwesome Pro icons (requires authentication/license)
- **Radix UI**: Uses Radix primitives for accessible components (Dialog, Popover, Select, Tooltip)
- **Sentry**: Error monitoring and performance tracking
- **Next.js 15**: Uses latest App Router patterns
- **React 19**: Latest React version with improved hooks and server components
