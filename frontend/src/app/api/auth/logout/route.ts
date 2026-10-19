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
  const siteUrl = await getSiteUrl();
  const token = await getToken({
    req: request,
    secret: NEXTAUTH_SECRET,
    cookieName: getTokenCookieName(),
  });

  const logoutUrl = new URL(
    `${getKeycloakIssuer(config)}/protocol/openid-connect/logout`,
  );

  if (token?.idToken) {
    logoutUrl.searchParams.set('id_token_hint', token.idToken);
  }

  logoutUrl.searchParams.set('post_logout_redirect_uri', siteUrl);

  return NextResponse.redirect(logoutUrl.toString());
}
