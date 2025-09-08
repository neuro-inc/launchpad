import { NextRequest, NextResponse } from 'next/server';
import { getToken } from 'next-auth/jwt';

import { NEXTAUTH_SECRET } from '@constants';
import { getAuthConfig } from '@features';
import {
  getKeycloakIssuer,
  getSiteUrl,
  getTokenCookieName,
} from '@utils/helpers';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  const config = await getAuthConfig();

  const token = await getToken({
    req: request,
    secret: NEXTAUTH_SECRET,
    cookieName: getTokenCookieName(),
  });

  const siteUrl = await getSiteUrl();

  // eslint-disable-next-line no-console
  console.log('Logout endpoint called:', {
    hasToken: !!token,
    hasIdToken: !!token?.idToken,
    siteUrl,
    token,
  });

  const logoutUrl = new URL(
    `${getKeycloakIssuer(config)}/protocol/openid-connect/logout`,
  );

  // eslint-disable-next-line no-console
  console.log('logoutUrl', logoutUrl.toString());

  if (token?.idToken) {
    logoutUrl.searchParams.set('id_token_hint', token.idToken);
    // eslint-disable-next-line no-console
    console.log('Added id_token_hint to logout URL');
  } else {
    // eslint-disable-next-line no-console
    console.log('No id_token available - proceeding without hint');
  }

  /**
   * Set the redirect URL after logout
   */
  logoutUrl.searchParams.set('post_logout_redirect_uri', siteUrl);

  return NextResponse.redirect(logoutUrl.toString());
}
