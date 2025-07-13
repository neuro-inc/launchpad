import { NextRequest, NextResponse } from 'next/server';

import { IS_LOCAL, IS_PRODUCTION, PATH } from '@constants';

export const middleware = (request: NextRequest) => {
  const { pathname } = request.nextUrl;

  /**
   * Temporary partners slug
   */
  if (IS_PRODUCTION && pathname !== PATH.HOME) {
    return NextResponse.redirect(new URL(PATH.HOME, request.url));
  }

  const setCookieHeader = request.headers.get('X-Set-Cookie');

  const response = NextResponse.next();

  if (setCookieHeader) {
    try {
      setCookieHeader.split(',').forEach((cookieString) => {
        const [name, value] = cookieString.split(';')[0].split('=');
        response.cookies.set({
          name: name.trim(),
          value: value.trim(),
          secure: !IS_LOCAL,
          path: '/',
          sameSite: 'lax',
        });
      });
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Failed to set cookies in middleware:', error);
    }
  }

  request.headers.append('x-pathname', pathname);

  return response;
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
