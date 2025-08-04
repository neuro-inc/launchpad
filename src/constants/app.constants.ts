export const ENVIRONMENT = process.env.ENVIRONMENT ?? 'local';
export const IS_PRODUCTION = ENVIRONMENT === 'production';
export const IS_DEVELOPMENT = ENVIRONMENT === 'development';
export const IS_LOCAL = !IS_PRODUCTION && !IS_DEVELOPMENT;

export const SERVER_API_URL = process.env.NEXT_PUBLIC_SERVER_API_URL;

export const SENTRY_DSN = process.env.SENTRY_DSN ?? '';
export const SENTRY_AUTH_TOKEN = process.env.SENTRY_AUTH_TOKEN ?? '';

export const KEYCLOAK_CLIENT_ID = process.env.KEYCLOAK_CLIENT_ID ?? '';
export const KEYCLOAK_CLIENT_SECRET = process.env.KEYCLOAK_CLIENT_SECRET ?? '';
export const KEYCLOAK_ISSUER = process.env.KEYCLOAK_ISSUER ?? '';

export const NEXTAUTH_SECRET = process.env.NEXTAUTH_SECRET ?? '';
export const NEXTAUTH_URL = process.env.NEXTAUTH_URL ?? '';
