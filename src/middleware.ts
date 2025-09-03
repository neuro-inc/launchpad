import { NextRequest, NextResponse } from 'next/server';
import { getToken } from 'next-auth/jwt';

import { PATH } from '@constants';

export const middleware = async (request: NextRequest) => {
  const { pathname } = request.nextUrl;

  /**
   * Skip authentication checks for logout endpoint
   */
  if (pathname === '/api/auth/logout') {
    return NextResponse.next();
  }

  const isProtected = pathname !== PATH.AUTH;

  const token = await getToken({
    req: request,
    raw: true,
  });

  if (!token && isProtected) {
    const url = new URL(PATH.AUTH, request.url);

    /**
     * Add the original URL as callbackUrl parameter
     */
    url.searchParams.set('callbackUrl', request.url);

    return NextResponse.redirect(url);
  }

  if (token && !isProtected) {
    const url = new URL(PATH.APPS, request.url);

    return NextResponse.redirect(url);
  }

  return NextResponse.next();
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
