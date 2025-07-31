import { NextRequest, NextResponse } from 'next/server';
import { getToken } from 'next-auth/jwt';

import { NEXTAUTH_SECRET, PATH } from '@constants';

const paths = Object.values(PATH);
const protectedPaths = paths.filter((path) => path !== PATH.AUTH) as string[];

export const middleware = async (request: NextRequest) => {
  const { pathname } = request.nextUrl;

  const isProtected = protectedPaths.includes(pathname);

  const token = await getToken({
    req: request,
    secret: NEXTAUTH_SECRET,
    raw: true,
  });

  if (!token && isProtected) {
    const url = new URL(PATH.AUTH, request.url);

    return NextResponse.redirect(url);
  }

  if (token && !isProtected) {
    const url = new URL(PATH.HOME, request.url);

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
