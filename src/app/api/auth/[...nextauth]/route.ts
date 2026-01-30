import NextAuth from 'next-auth';

import { getAuthOptions } from '@features';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const handler = async (req: any, context: any) => {
  const authOptions = await getAuthOptions();
  return NextAuth(authOptions)(req, context);
};

export { handler as GET, handler as POST };
