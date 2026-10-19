export const APP_VERSION = process.env.APP_VERSION ?? '1.0.0';
export const APP_COMMIT_SHA = process.env.APP_COMMIT_SHA ?? 'unknown';
export const APP_DEPLOYED_AT =
  process.env.APP_DEPLOYED_AT ?? new Date().toISOString();

export const ENVIRONMENT = process.env.NEXT_PUBLIC_ENVIRONMENT ?? 'local';
export const IS_PRODUCTION = ENVIRONMENT === 'production';
export const IS_DEVELOPMENT = ENVIRONMENT === 'development';
export const IS_LOCAL = !IS_PRODUCTION && !IS_DEVELOPMENT;

export const SENTRY_DSN = process.env.SENTRY_DSN ?? '';
export const SENTRY_AUTH_TOKEN = process.env.SENTRY_AUTH_TOKEN ?? '';

export const NEXTAUTH_SECRET = process.env.NEXTAUTH_SECRET ?? '';
