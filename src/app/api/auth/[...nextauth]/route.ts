import NextAuth from 'next-auth';

import { getAuthOptions } from '@features';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const handler = NextAuth(await getAuthOptions());

export { handler as GET, handler as POST };
