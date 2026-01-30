import { AuthOptions } from 'next-auth';
import KeycloakProvider from 'next-auth/providers/keycloak';

import { KeycloakConfig } from '@typings';
import { NEXTAUTH_SECRET } from '@constants';
import { getKeycloakIssuer, getServerApiUrl, getSiteUrl } from '@utils/helpers';

type AuthConfig = KeycloakConfig;

export async function getAuthConfig(): Promise<AuthConfig> {
  try {
    const serverApiUrl = await getServerApiUrl();

    const response = await fetch(`${serverApiUrl}/config?t=${Date.now()}`, {
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        Pragma: 'no-cache',
        Expires: '0',
      },
      cache: 'no-store',
    });

    if (!response.ok) {
      const errorText = await response.text();

      console.error('Server response error:', response.status, errorText);

      throw new Error(
        `Failed to fetch auth config: ${response.status} ${response.statusText}`,
      );
    }

    /**
     * Check if response is actually JSON
     */
    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
      const responseText = await response.text();
      console.error('Non-JSON response received:', responseText);
      throw new Error('Server did not return JSON response');
    }

    const responseText = await response.text();

    if (!responseText.trim()) {
      throw new Error('Empty response from server');
    }

    const responseJson = JSON.parse(responseText) as {
      keycloak: KeycloakConfig;
    };

    if (!responseJson.keycloak) {
      throw new Error('Invalid response structure: keycloak config not found');
    }

    return responseJson.keycloak;
  } catch (error) {
    console.error('Error fetching auth config:', error);

    throw error;
  }
}

export const refreshAccessToken = async (token: any) => {
  try {
    const config = await getAuthConfig();

    const url = `${getKeycloakIssuer(config)}/protocol/openid-connect/token`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        client_id: 'frontend',
        grant_type: 'refresh_token',
        refresh_token: token.refreshToken,
      }),
    });

    const refreshed = await response.json();

    if (!response.ok) {
      throw refreshed;
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
    // eslint-disable-next-line no-console
    console.error('Error refreshing access token:', error);
    return {
      ...token,
      error: 'RefreshAccessTokenError',
    };
  }
};

export async function getAuthOptions(): Promise<AuthOptions> {
  const config = await getAuthConfig();
  // const siteUrl = await getSiteUrl();

  return {
    providers: [
      KeycloakProvider({
        clientId: 'frontend',
        /**
         * For public clients, use undefined instead of empty string
         * This prevents NextAuth from trying to use client secret authentication
         */
        clientSecret: '',
        issuer: getKeycloakIssuer(config),
        /**
         * Only PKCE for public clients
         */
        checks: ['pkce'],
        // httpOptions: {
        //   headers: {
        //     origin: siteUrl,
        //   },
        // },
        authorization: {
          params: {
            // prompt: 'login',
            scope: 'openid profile email offline_access',
            response_type: 'code',
            // redirect_uri: `${siteUrl}/api/auth/callback/keycloak`,
          },
        },
      }),
    ],
    secret: NEXTAUTH_SECRET,
    debug: true,
    jwt: {
      /**
       * Reduce JWT size by using compact encoding
       */
      maxAge: 24 * 60 * 60, // 24 hours
    },
    session: {
      /**
       * Using JWT for public clients
       */
      strategy: 'jwt',
      /**
       * Reduce session cookie size by setting maxAge
       * This matches the access token expiry (24 hours based on logs)
       */
      maxAge: 24 * 60 * 60, // 24 hours
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
          // Store tokens for API calls (these won't be in session cookie)
          token.accessToken = account.access_token;
          token.refreshToken = account.refresh_token;
          token.idToken = account.id_token;
          token.accessTokenExpires = account.expires_at;

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
        // Only include essential data in session (which goes to cookie)
        // Tokens are stored in JWT but not exposed in session to reduce cookie size
        session.error = token.error;
        session.groups = token.groups;
        session.realm_roles = token.realm_roles;
        session.client_roles = token.client_roles;

        // Tokens are available in JWT for server-side API calls via getServerSession
        // but not included in client-side session to keep cookie small
        if (token.accessToken) {
          session.accessToken = token.accessToken;
        }

        return session;
      },
    },
  };
}
