import { NextRequest } from 'next/server';
import NextAuth from 'next-auth';

import { getAuthOptions } from '@features';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const handler = async (
  req: NextRequest,
  // @ts-ignore - NextAuth App Router compatibility
  { params }: { params: { nextauth: string[] } },
) => {
  const authOptions = await getAuthOptions();
  return NextAuth(authOptions)(req, { params });
};

export { handler as GET, handler as POST };
