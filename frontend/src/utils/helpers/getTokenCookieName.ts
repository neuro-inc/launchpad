import { IS_LOCAL } from '@constants';

export const getTokenCookieName = () =>
  IS_LOCAL ? 'next-auth.session-token' : '__Secure-next-auth.session-token';
