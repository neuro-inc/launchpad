import { NextRequest, NextResponse } from 'next/server';
import { getToken } from 'next-auth/jwt';

import { NEXTAUTH_SECRET, PATH } from '@constants';

export const middleware = async (request: NextRequest) => {
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

  /**
   * Skip authentication checks for logout endpoint
   */
  if (pathname === '/api/auth/logout') {
    return NextResponse.next({
      request: {
        headers: requestHeaders,
      },
    });
  }

  const isProtected = pathname !== PATH.AUTH;

  console.log('pathname', pathname);

  const token = await getToken({
    req: request,
    secret: NEXTAUTH_SECRET,
    raw: true,
    cookieName: 'next-auth.session-token',
  });

  console.log('token', token);

  if (!token) {
    const url = new URL(PATH.AUTH, request.url);

    return NextResponse.redirect(url);
  }

  if (token && !isProtected) {
    const url = new URL(PATH.APPS, request.url);

    return NextResponse.redirect(url);
  }

  return NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  });
};

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes);
     * - _next/static (static files);
     * - _next/image (image optimization files);
     * - favicon.ico, sitemap.xml, robots.txt (metadata files);
     */
    '/((?!api|_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)',
  ],
};
