import { cache } from 'react';
import { AuthOptions } from 'next-auth';
import KeycloakProvider from 'next-auth/providers/keycloak';

import { KeycloakConfig, LaunchpadConfigResponse } from '@typings';
import { NEXTAUTH_SECRET } from '@constants';
import {
  getKeycloakIssuer,
  getServerApiUrl,
  getSiteUrl,
  logLaunchpadNet,
  safeError,
  safeUrlParts,
} from '@utils/helpers';
import { fetchWithRetry } from '@utils/helpers/fetchWithRetry';

type AuthConfig = KeycloakConfig;

type RawConfig = {
  keycloak: KeycloakConfig;
  branding?: LaunchpadConfigResponse['branding'];
};

const SESSION_MAX_AGE_SECONDS = 10 * 24 * 60 * 60;

const getOAuthErrorInfo = (error: unknown) => {
  if (!error || typeof error !== 'object') {
    return undefined;
  }

  const data = error as Record<string, unknown>;

  return {
    error: typeof data.error === 'string' ? data.error : undefined,
    errorDescription:
      typeof data.error_description === 'string'
        ? data.error_description
        : undefined,
    status: typeof data.status === 'number' ? data.status : undefined,
    statusText:
      typeof data.statusText === 'string' ? data.statusText : undefined,
  };
};

// Module-level cache keyed by apiUrl — survives across React renders and generateMetadata()
const rawConfigCache = new Map<string, { data: RawConfig; expires: number }>();
const rawConfigInflight = new Map<string, Promise<RawConfig>>();

async function fetchRawConfigFromApi(apiUrl: string): Promise<RawConfig> {
  const safeApiUrl = safeUrlParts(apiUrl);
  const cached = rawConfigCache.get(apiUrl);
  if (cached && Date.now() < cached.expires) {
    return cached.data;
  }

  const inflight = rawConfigInflight.get(apiUrl);
  if (inflight) {
    return inflight;
  }

  const promise = (async () => {
    const startedAt = Date.now();

    try {
      const response = await fetchWithRetry(
        `${apiUrl}/config`,
        {
          headers: {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            Pragma: 'no-cache',
            Expires: '0',
          },
          cache: 'no-store',
        },
        1,
      );

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          `Failed to fetch config: ${response.status} ${response.statusText} — ${errorText}`,
        );
      }

      const contentType = response.headers.get('content-type');
      if (!contentType?.includes('application/json')) {
        throw new Error('Server did not return JSON response');
      }

      const data = (await response.json()) as RawConfig;

      if (!data.keycloak) {
        throw new Error(
          'Invalid response structure: keycloak config not found',
        );
      }

      rawConfigCache.set(apiUrl, { data, expires: Date.now() + 30_000 });
      return data;
    } catch (error) {
      logLaunchpadNet('raw-config-fetch-error', {
        ...safeApiUrl,
        durationMs: Date.now() - startedAt,
        error: safeError(error),
      });
      throw error;
    } finally {
      rawConfigInflight.delete(apiUrl);
    }
  })();

  rawConfigInflight.set(apiUrl, promise);
  return promise;
}

// Per-request deduplication on top of the module-level cache
export const getRawConfig = cache(async (): Promise<RawConfig> => {
  const apiUrl = await getServerApiUrl();
  return fetchRawConfigFromApi(apiUrl);
});

export const getAuthConfig = cache(async (): Promise<AuthConfig> => {
  const raw = await getRawConfig();
  return raw.keycloak;
});

export const refreshAccessToken = async (token: any) => {
  const startedAt = Date.now();
  let tokenUrlParts: ReturnType<typeof safeUrlParts> | undefined;

  try {
    const config = await getAuthConfig();
    const url = `${getKeycloakIssuer(config)}/protocol/openid-connect/token`;
    tokenUrlParts = safeUrlParts(url);

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      signal: AbortSignal.timeout(5_000),
      body: new URLSearchParams({
        client_id: 'frontend',
        grant_type: 'refresh_token',
        refresh_token: token.refreshToken,
      }),
    });

    const refreshed = await response.json();

    if (!response.ok) {
      throw {
        ...refreshed,
        status: response.status,
        statusText: response.statusText,
      };
    }

    // Decode the new access token to extract roles
    let realmRoles = token.realm_roles || [];
    let clientRoles = token.client_roles || [];
    let groups = token.groups || [];

    if (refreshed.access_token) {
      try {
        const base64Url = refreshed.access_token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(
          Buffer.from(base64, 'base64')
            .toString('ascii')
            .split('')
            .map((c) => `%${`00${c.charCodeAt(0).toString(16)}`.slice(-2)}`)
            .join(''),
        );
        const decodedToken = JSON.parse(jsonPayload);

        realmRoles = decodedToken.realm_access?.roles || [];

        // Extract client roles from resource_access.frontend.roles
        const resourceAccess = decodedToken.resource_access || {};
        const frontendAccess = resourceAccess.frontend || {};
        clientRoles = frontendAccess.roles || [];

        groups = decodedToken.groups || [];
      } catch (error) {
        console.error('Error decoding refreshed access token:', error);
      }
    }

    return {
      ...token,
      accessToken: refreshed.access_token,
      accessTokenExpires: Date.now() + refreshed.expires_in * 1000,
      /**
       * Fallback to old refresh token
       */
      refreshToken: refreshed.refresh_token ?? token.refreshToken,
      idToken: refreshed.id_token ?? token.idToken,
      realm_roles: realmRoles,
      client_roles: clientRoles,
      groups,
    };
  } catch (error) {
    console.error(
      JSON.stringify({
        scope: 'launchpad-net',
        event: 'auth-refresh-error',
        ts: new Date().toISOString(),
        durationMs: Date.now() - startedAt,
        tokenEndpoint: tokenUrlParts,
        oauth: getOAuthErrorInfo(error),
        error: safeError(error),
      }),
    );
    logLaunchpadNet('auth-refresh-error', {
      durationMs: Date.now() - startedAt,
      tokenEndpoint: tokenUrlParts,
      oauth: getOAuthErrorInfo(error),
      error: safeError(error),
    });
    return {
      ...token,
      error: 'RefreshAccessTokenError',
    };
  }
};

export async function getAuthOptions(): Promise<AuthOptions> {
  const config = await getAuthConfig();

  return {
    providers: [
      KeycloakProvider({
        clientId: 'frontend',
        /**
         * For public clients, use undefined instead of empty string
         * This prevents NextAuth from trying to use client secret authentication
         */
        clientSecret: process.env.KEYCLOAK_CLIENT_SECRET ?? '',
        issuer: getKeycloakIssuer(config),
        /**
         * Only PKCE for public clients
         */
        checks: ['pkce', 'state'],
        authorization: {
          params: {
            scope: 'openid profile email offline_access',
            response_type: 'code',
          },
        },
      }),
    ],
    secret: NEXTAUTH_SECRET,
    debug: false,
    session: {
      /**
       * Using JWT for public clients
       */
      strategy: 'jwt',
      maxAge: SESSION_MAX_AGE_SECONDS,
    },
    jwt: {
      maxAge: SESSION_MAX_AGE_SECONDS,
    },
    callbacks: {
      async redirect({ url }) {
        const siteUrl = await getSiteUrl();

        /**
         * If url starts with /, it's a relative path - make it absolute
         */
        if (url.startsWith('/')) {
          return `${siteUrl}${url}`;
        }

        /**
         * If url is from the same origin as our site, allow it
         */
        if (new URL(url).origin === siteUrl) {
          return url;
        }

        /**
         * Default fallback - return to the apps page instead of auth page
         */
        return `${siteUrl}/apps`;
      },
      async signIn({ account }) {
        if (account?.error) {
          console.error('Account error during sign in:', account.error);
          return false;
        }

        return true;
      },
      async jwt({ token, account, profile }) {
        const now = Date.now();

        if (account) {
          token.accessToken = account.access_token;
          token.refreshToken = account.refresh_token;
          token.idToken = account.id_token;
          // expires_at from OAuth providers is in seconds; Date.now() is ms.
          // Guard against providers that already return ms (value > 1e12).
          const expiresAt = account.expires_at ?? 0;
          token.accessTokenExpires =
            expiresAt > 1e12 ? expiresAt : expiresAt * 1000;

          token.name = profile?.name ?? undefined;
          token.email = profile?.email ?? undefined;

          // Decode the access token to get realm_access.roles
          // The profile object from userinfo endpoint doesn't contain roles
          // We need to decode the JWT access token directly
          if (account.access_token) {
            try {
              // Decode JWT (base64 decode the payload part)
              const base64Url = account.access_token.split('.')[1];
              const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
              const jsonPayload = decodeURIComponent(
                Buffer.from(base64, 'base64')
                  .toString('ascii')
                  .split('')
                  .map(
                    (c) => `%${`00${c.charCodeAt(0).toString(16)}`.slice(-2)}`,
                  )
                  .join(''),
              );
              const decodedToken = JSON.parse(jsonPayload);

              // Extract roles from realm_access.roles
              const realmAccessRoles = decodedToken.realm_access?.roles || [];
              token.realm_roles = Array.isArray(realmAccessRoles)
                ? realmAccessRoles
                : [];

              // Extract client roles from resource_access.frontend.roles
              // The backend expects roles in resource_access.frontend.roles
              const resourceAccess = decodedToken.resource_access || {};
              const frontendAccess = resourceAccess.frontend || {};
              const clientRoles = frontendAccess.roles || [];
              token.client_roles = Array.isArray(clientRoles)
                ? clientRoles
                : [];

              // Also try to get groups if they exist (backend uses this as roles)
              const groups = decodedToken.groups || [];
              token.groups = Array.isArray(groups) ? groups : [];
            } catch (error) {
              console.error('Error decoding access token:', error);
              token.realm_roles = [];
              token.client_roles = [];
              token.groups = [];
            }
          }
        }

        if (token.accessTokenExpires && now < token.accessTokenExpires) {
          return token;
        }

        return refreshAccessToken(token);
      },
      async session({ session, token }) {
        session.accessToken = token.accessToken;
        session.refreshToken = token.refreshToken;
        session.idToken = token.idToken;
        session.error = token.error;
        session.groups = token.groups;
        session.realm_roles = token.realm_roles;
        session.client_roles = token.client_roles;

        return session;
      },
    },
  };
}
