import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';

import { getAuthConfig } from '@features';
import { getKeycloakIssuer, getSiteUrl } from '@utils/helpers';

export async function GET() {
  const config = await getAuthConfig();

  const token = await getServerSession();

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
