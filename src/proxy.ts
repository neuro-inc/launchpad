import { NextRequest, NextResponse } from 'next/server';
import { getToken } from 'next-auth/jwt';

import { NEXTAUTH_SECRET, PATH } from '@constants';
import { getTokenCookieName } from '@utils/helpers/getTokenCookieName';

export const proxy = async (request: NextRequest) => {
  const { headers } = request;
  const { pathname } = request.nextUrl;

  const protocol =
    headers.get('x-forwarded-proto') ??
    request.nextUrl.protocol.replace(':', '') ??
    'https';
  const host =
    headers.get('x-forwarded-host') ??
    headers.get('host') ??
    request.nextUrl.host;

  const origin = `${protocol}://${host}`;
  const requestHeaders = new Headers(headers);

  requestHeaders.set('x-origin', origin);

  if (pathname === '/api/auth/logout') {
    return NextResponse.next({
      request: {
        headers: requestHeaders,
      },
    });
  }

  const isProtected = pathname !== PATH.AUTH;
  const isAdminRoute = pathname.startsWith(PATH.ADMIN);

  const token = await getToken({
    req: request,
    secret: NEXTAUTH_SECRET,
    cookieName: getTokenCookieName(),
  });

  if (!token && isProtected) {
    const url = new URL(PATH.AUTH, request.url);

    return NextResponse.redirect(url);
  }

  if (token && !isProtected) {
    const url = new URL(PATH.APPS, request.url);

    return NextResponse.redirect(url);
  }

  if (token && isAdminRoute) {
    const clientRoles = (token.client_roles as string[]) || [];
    const realmRoles = (token.realm_roles as string[]) || [];
    const roles = clientRoles.length > 0 ? clientRoles : realmRoles;
    const isAdmin = roles.includes('admin');

    if (!isAdmin) {
      const url = new URL(PATH.APPS, request.url);

      return NextResponse.redirect(url);
    }
  }

  return NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  });
};

export const config = {
  matcher: [
    '/((?!api|_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)',
  ],
};
