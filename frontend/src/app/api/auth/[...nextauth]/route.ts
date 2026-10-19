import NextAuth from 'next-auth';

import { getAuthOptions } from '@features';
import { logLaunchpadNet, safeError, safeUrlParts } from '@utils/helpers';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

type AuthRouteContext = {
  params: Promise<{
    nextauth?: string[];
  }>;
};

const handler = async (req: any, context: AuthRouteContext) => {
  const startedAt = Date.now();
  const urlInfo = safeUrlParts(req.url ?? '');
  const params = await context.params;
  const route = Array.isArray(params.nextauth)
    ? params.nextauth.join('/')
    : 'unknown';

  try {
    const authOptions = await getAuthOptions();
    const response = await NextAuth(authOptions)(req, { ...context, params });
    return response;
  } catch (error) {
    logLaunchpadNet('nextauth-handler-error', {
      ...urlInfo,
      route,
      durationMs: Date.now() - startedAt,
      error: safeError(error),
    });
    throw error;
  }
};

export { handler as GET, handler as POST };
