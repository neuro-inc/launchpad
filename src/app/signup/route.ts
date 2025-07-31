import { NextResponse } from 'next/server';

import { KEYCLOAK_CLIENT_ID } from '@constants';

export async function GET() {
  const redirectUri = encodeURIComponent(
    `${process.env.NEXTAUTH_URL}/api/auth/callback/keycloak`,
  );
  const keycloakUrl =
    `${process.env.KEYCLOAK_ISSUER}/protocol/openid-connect/auth?` +
    `client_id=${KEYCLOAK_CLIENT_ID}` +
    `&response_type=code` +
    `&scope=openid` +
    `&redirect_uri=${redirectUri}` +
    `&action=register`;

  return NextResponse.redirect(keycloakUrl);
}
