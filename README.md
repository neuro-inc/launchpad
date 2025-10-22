# Apolo Launchpad Web UI

A Next.js 15 web application for cloud-native application management. Provides a web interface for deploying, monitoring, and managing applications in a Kubernetes environment.

## Tech Stack

- **Next.js 15** with App Router
- **React 19**
- **TypeScript** (strict mode)
- **Tailwind CSS** with custom design system
- **NextAuth.js** with Keycloak authentication
- **Sentry** for error tracking
- **FontAwesome Pro** for icons

## Prerequisites

- **Node.js** 20 or higher
- **Yarn** package manager (required - npm is not supported)
- **Apolo Platform** access with Launchpad installed

## Local Development Setup

### 1. Deploy Launchpad Backend

Before running the frontend locally, you need to deploy a Launchpad instance:

1. Go to **Apolo Console**
2. Install the **Launchpad** app
3. After installation, go to the app's **Outputs** tab
4. Copy the **App URL** - you'll use this as `NEXT_PUBLIC_SERVER_API_URL`

### 2. Configure Keycloak for Local Development

Add the local development callback URL to your Keycloak configuration:

1. Access your **Keycloak admin console**
2. Navigate to **Launchpad realm** → **Clients** → **frontend**
3. Add the following to **Valid Redirect URIs**:
   ```
   http://localhost:3000/api/auth/callback/keycloak
   ```
4. Save the configuration

**Note:** This step is only needed for local development. Production deployments use different redirect URIs.

### 3. Install Dependencies

**Important:** This project uses Yarn. Do not use npm.

```bash
yarn install
```

### 4. Environment Variables

Create a `.env.local` file in the root directory with the following variables:

```bash
# NextAuth Configuration
NEXTAUTH_SECRET=your-secret-here
NEXTAUTH_URL=http://localhost:3000

# Backend API URL (from Launchpad app outputs)
NEXT_PUBLIC_SERVER_API_URL=https://your-launchpad-instance.jobs.neu.ro

# Site URL (use http://localhost:3000 for local development)
NEXT_PUBLIC_SITE_URL=http://localhost:3000

# Sentry (optional)
SENTRY_DSN=your-sentry-dsn
SENTRY_AUTH_TOKEN=your-sentry-token

# Environment
NEXT_PUBLIC_ENVIRONMENT=local
```

**Important Notes:**
- `NEXT_PUBLIC_SERVER_API_URL` is the App URL from your Launchpad instance outputs
- `NEXT_PUBLIC_SITE_URL` is used for OAuth redirects - use the public URL where this app is deployed
- For local development, `NEXT_PUBLIC_SITE_URL` should be `http://localhost:3000`

### 5. Run Development Server

```bash
yarn dev
```

The application will be available at [http://localhost:3000](http://localhost:3000).

The development server uses Turbopack for faster builds and hot module replacement.

## Available Commands

```bash
# Development
yarn dev              # Start dev server with Turbopack

# Building
yarn build            # Build production bundle

# Production
yarn start            # Start production server

# Linting
yarn lint             # Run both TypeScript and ESLint checks
yarn lint:ts          # TypeScript type checking only
yarn lint:eslint      # ESLint checks only
```

## Project Structure

```
├── src/
│   ├── app/                 # Next.js App Router pages
│   │   ├── api/auth/       # NextAuth.js routes
│   │   ├── apps/           # Main app pages (protected)
│   │   ├── auth/           # Login page (public)
│   │   └── admin/          # Admin panel (protected)
│   ├── components/         # React components
│   │   ├── Shared/        # Reusable UI primitives
│   │   └── Ui/            # App-specific components
│   ├── features/          # Feature modules
│   ├── utils/             # Utility functions
│   ├── types/             # TypeScript types
│   └── constants/         # App constants
├── public/                # Static assets
└── .claude/              # Claude Code configuration
```

## Authentication

This application uses **NextAuth.js with Keycloak** for authentication:

- Dynamic configuration fetched from backend API
- PKCE flow for public clients (no client secret)
- Automatic JWT token refresh
- Role-based access control (admin/user)

All routes except `/auth` are protected by default.

## Development

### Code Style

The project enforces strict linting rules:

- **Airbnb** style guide with TypeScript extensions
- **Prettier** for code formatting
- **Import sorting** with specific grouping order
- **Tailwind CSS** class validation

Run `yarn lint` before committing to ensure code quality.

### Path Aliases

Use TypeScript path aliases instead of relative imports:

```typescript
import { Button } from '@components/Shared';
import { getAuthOptions } from '@features';
import { PATH } from '@constants';
```

See [tsconfig.json](tsconfig.json) for all available aliases.

## Learn More

- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev)
- [NextAuth.js Documentation](https://next-auth.js.org)
- [Tailwind CSS Documentation](https://tailwindcss.com)
