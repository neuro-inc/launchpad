export const ENVIRONMENT = process.env.ENVIRONMENT ?? 'local';
export const IS_PRODUCTION = ENVIRONMENT === 'production';
export const IS_DEVELOPMENT = ENVIRONMENT === 'development';
export const IS_LOCAL = !IS_PRODUCTION && !IS_DEVELOPMENT;

export const SENTRY_DSN = process.env.SENTRY_DSN ?? '';
export const SENTRY_AUTH_TOKEN = process.env.SENTRY_AUTH_TOKEN ?? '';

export const NEXTAUTH_SECRET = process.env.NEXTAUTH_SECRET ?? '';
