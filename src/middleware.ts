import { NextRequest, NextResponse } from 'next/server';

import { PATH } from '@constants';
import { getTokenCookieName } from '@utils/helpers/getTokenCookieName';

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

  const isProtected = pathname !== PATH.AUTH;

  // Fast auth check - just verify cookie exists without decoding JWT
  // This avoids slow getToken() calls that cause edge function timeouts
  const cookieName = getTokenCookieName();
  const sessionCookie = request.cookies.get(cookieName);
  const hasSession = !!sessionCookie?.value;

  if (!hasSession && isProtected) {
    const url = new URL(PATH.AUTH, request.url);

    return NextResponse.redirect(url);
  }

  if (hasSession && !isProtected) {
    const url = new URL(PATH.APPS, request.url);

    return NextResponse.redirect(url);
  }

  // For admin routes, we can't check roles here without decoding JWT (slow)
  // Admin access will be enforced server-side in the actual page/API route

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
