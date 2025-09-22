import { NextRequest } from 'next/server';
import NextAuth from 'next-auth';

import { getAuthOptions } from '@features';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

async function handler(req: NextRequest) {
  const authOptions = await getAuthOptions();

  return NextAuth(authOptions)(req);
}

export { handler as GET, handler as POST };
