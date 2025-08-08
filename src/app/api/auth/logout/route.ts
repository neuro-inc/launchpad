import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';

import { NEXTAUTH_URL } from '@constants';
import { getAuthConfig, getAuthOptions } from '@features';
import { getKeycloakIssuer } from '@utils/helpers';

export async function GET() {
  const config = await getAuthConfig();
  const authOptions = await getAuthOptions();
  const session = await getServerSession(authOptions);

  const idToken = session?.idToken;

  const logoutUrl = new URL(
    `${getKeycloakIssuer(config)}/protocol/openid-connect/logout`,
  );

  if (idToken) {
    logoutUrl.searchParams.set('id_token_hint', idToken);
  }

  logoutUrl.searchParams.set('post_logout_redirect_uri', NEXTAUTH_URL);

  return NextResponse.redirect(logoutUrl.toString());
}
