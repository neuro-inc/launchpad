import { AuthOptions } from 'next-auth';
import KeycloakProvider from 'next-auth/providers/keycloak';

import { KeycloakConfig } from '@typings';
import { NEXTAUTH_SECRET } from '@constants';
import { getKeycloakIssuer, getServerApiUrl, getSiteUrl } from '@utils/helpers';

type AuthConfig = KeycloakConfig;

export async function getAuthConfig(): Promise<AuthConfig> {
  try {
    const serverApiUrl = await getServerApiUrl();
    // eslint-disable-next-line no-console
    console.log('serverApiUrl', serverApiUrl);
    const response = await fetch(`${serverApiUrl}/config`, {
      headers: { 'Cache-Control': 'no-cache' },
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

    return {
      ...token,
      accessToken: refreshed.access_token,
      accessTokenExpires: Date.now() + refreshed.expires_in * 1000,
      /**
       * Fallback to old refresh token
       */
      refreshToken: refreshed.refresh_token ?? token.refreshToken,
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

  /**
   * Dynamically set NEXTAUTH_URL from x-origin header or getSiteUrl
   */
  try {
    const siteUrl = await getSiteUrl();
    process.env.NEXTAUTH_URL = siteUrl;
    // eslint-disable-next-line no-console
    console.log('Dynamically set NEXTAUTH_URL to:', siteUrl);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Failed to set dynamic NEXTAUTH_URL:', error);
  }

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
        authorization: {
          params: {
            scope: 'openid profile email offline_access',
            response_type: 'code',
          },
        },
      }),
    ],
    secret: NEXTAUTH_SECRET,
    debug: true,
    session: {
      /**
       * Using JWT for public clients
       */
      strategy: 'jwt',
    },
    callbacks: {
      async redirect({ url }) {
        const siteUrl = await getSiteUrl();

        /**
         * Log redirect parameters for debugging
         */
        // eslint-disable-next-line no-console
        console.log('Redirect callback:', { url, siteUrl });

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
      async signIn({ user, account, profile }) {
        /**
         * Add debugging for sign-in attempts
         */
        // eslint-disable-next-line no-console
        console.log('SignIn attempt:', {
          user: user?.email,
          account: account?.provider,
          profile: profile?.email,
          error: account?.error,
        });

        if (account?.error) {
          // eslint-disable-next-line no-console
          console.error('Account error during sign in:', account.error);

          /**
           * Reject sign in if there's an account error
           */
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
