import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';

import { getAuthConfig, getAuthOptions } from '@features';
import { getKeycloakIssuer, getSiteUrl } from '@utils/helpers';

export async function GET() {
  const config = await getAuthConfig();
  const authOptions = await getAuthOptions();
  // eslint-disable-next-line no-console
  console.log('authOptions', authOptions);
  const session = await getServerSession(authOptions);
  const siteUrl = await getSiteUrl();

  // eslint-disable-next-line no-console
  console.log('session', session);

  const idToken = session?.idToken;

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
