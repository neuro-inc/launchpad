import { AuthOptions } from 'next-auth';
import KeycloakProvider from 'next-auth/providers/keycloak';

import { KeycloakConfig } from '@typings';
import { NEXTAUTH_SECRET, SERVER_API_URL } from '@constants';
import { getKeycloakIssuer } from '@utils/helpers';

type AuthConfig = KeycloakConfig;

let cachedAuthConfig: AuthConfig | null = null;

export async function getAuthConfig(): Promise<AuthConfig> {
  if (cachedAuthConfig) {
    return cachedAuthConfig;
  }

  try {
    const response = await fetch(`${SERVER_API_URL}/config`);

    if (!response.ok) {
      const errorText = await response.text();

      console.error('Server response error:', response.status, errorText);

      throw new Error(
        `Failed to fetch auth config: ${response.status} ${response.statusText}`,
      );
    }

    // Check if response is actually JSON
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

    cachedAuthConfig = responseJson.keycloak;

    return cachedAuthConfig;
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

    return {
      ...token,
      accessToken: refreshed.access_token,
      accessTokenExpires: Date.now() + refreshed.expires_in * 1000,
      refreshToken: refreshed.refresh_token ?? token.refreshToken, // fallback to old refresh token
      idToken: refreshed.id_token ?? token.idToken,
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

  return {
    providers: [
      KeycloakProvider({
        clientId: 'frontend',
        /**
         * There is public client authentication enabled in Keycloak,
         */
        // @ts-ignore
        clientSecret: '',
        issuer: getKeycloakIssuer(config),
        checks: ['pkce'],
        authorization: {
          params: {
            scope: 'openid profile email offline_access',
          },
        },
      }),
    ],
    secret: NEXTAUTH_SECRET,
    callbacks: {
      async jwt({ token, account, profile }) {
        const now = Date.now();

        if (account) {
          token.accessToken = account.access_token;
          token.refreshToken = account.refresh_token;
          token.idToken = account.id_token;
          token.accessTokenExpires = account.expires_at;

          token.name = profile?.name ?? undefined;
          token.email = profile?.email ?? undefined;
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

        return session;
      },
    },
  };
}
