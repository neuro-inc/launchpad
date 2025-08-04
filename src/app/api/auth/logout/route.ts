import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';

import { KEYCLOAK_ISSUER, NEXTAUTH_URL } from '@constants';
import { authOptions } from '@features/auth.feature';

export async function GET() {
  const session = await getServerSession(authOptions);
  const idToken = session?.idToken;

  const logoutUrl = new URL(
    `${KEYCLOAK_ISSUER}/protocol/openid-connect/logout`,
  );

  if (idToken) {
    logoutUrl.searchParams.set('id_token_hint', idToken);
  }

  logoutUrl.searchParams.set('post_logout_redirect_uri', NEXTAUTH_URL);

  return NextResponse.redirect(logoutUrl.toString());
}
