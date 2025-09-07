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

export async function GET(req: NextRequest) {
  const config = await getAuthConfig();

  const token = await getToken({
    req,
    secret: NEXTAUTH_SECRET,
    cookieName: getTokenCookieName(),
  });

  // eslint-disable-next-line no-console
  console.log('token from getToken:', token);

  const siteUrl = await getSiteUrl();

  const idToken = token?.idToken;

  // eslint-disable-next-line no-console
  console.log('idToken', idToken);

  const logoutUrl = new URL(
    `${getKeycloakIssuer(config)}/protocol/openid-connect/logout`,
  );

  if (idToken) {
    logoutUrl.searchParams.set('id_token_hint', idToken);
  }

  logoutUrl.searchParams.set('post_logout_redirect_uri', siteUrl);

  return NextResponse.redirect(logoutUrl.toString());
}
