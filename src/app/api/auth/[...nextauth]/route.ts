import NextAuth from 'next-auth';

import { getAuthOptions } from '@features';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const handler = NextAuth({
  ...(await getAuthOptions()),
  debug: true,
  logger: {
    error(code, metadata) {
      console.error('NextAuth Error:', code, metadata);
    },
    warn(code) {
      console.warn('NextAuth Warning:', code);
    },
    debug(code, metadata) {
      // eslint-disable-next-line no-console
      console.debug('NextAuth Debug:', code, metadata);
    },
  },
});

export { handler as GET, handler as POST };
