import { COOKIE, COOKIE_EXPIRE_HEADER } from '@constants';

const COOKIE_ATTRIBUTES = 'path=/; SameSite=Lax';
let lastToken: string | null = null;

const getCookieAttributes = () => {
  if (typeof window !== 'undefined' && window.location.protocol === 'https:') {
    return `${COOKIE_ATTRIBUTES}; Secure`;
  }

  return COOKIE_ATTRIBUTES;
};

export const setLaunchpadCookie = async (token: string): Promise<void> => {
  if (typeof document === 'undefined' || !token || token === lastToken) {
    return;
  }

  document.cookie = `${COOKIE.LAUNCHPAD_TOKEN}=${encodeURIComponent(token)}; ${getCookieAttributes()}`;
  lastToken = token;
};

export const clearLaunchpadCookie = (): void => {
  lastToken = null;

  if (typeof document === 'undefined') {
    return;
  }

  document.cookie = `${COOKIE.LAUNCHPAD_TOKEN}=; ${COOKIE_EXPIRE_HEADER}`;
};
