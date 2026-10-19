import { COOKIE, COOKIE_EXPIRE_HEADER } from '@constants';

const COOKIE_ATTRIBUTES = 'path=/; SameSite=Lax';
let lastToken: string | null = null;
let sharedDomain: string | null | undefined = undefined;

// "launchpad-xxx.launchpad.apps.dev.apolo.us" → ".apps.dev.apolo.us"
const getSharedCookieDomain = (hostname: string): string | null => {
  const parts = hostname.split('.');
  const appsIdx = parts.indexOf('apps');
  if (appsIdx !== -1) {
    return '.' + parts.slice(appsIdx).join('.');
  }
  return null;
};

const resolveSharedDomain = (): string | null => {
  if (sharedDomain === undefined) {
    sharedDomain = getSharedCookieDomain(window.location.hostname);
  }
  return sharedDomain;
};

const getCookieAttributes = () => {
  let attrs = COOKIE_ATTRIBUTES;
  const domain = resolveSharedDomain();
  if (domain) attrs += `; domain=${domain}`;
  if (window.location.protocol === 'https:') attrs += '; Secure';
  return attrs;
};

export const setLaunchpadCookie = (token: string): void => {
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

  const expiredCookie = `${COOKIE.LAUNCHPAD_TOKEN}=; ${COOKIE_EXPIRE_HEADER}`;
  const domain = resolveSharedDomain();
  document.cookie = expiredCookie;
  if (domain) document.cookie = `${expiredCookie}; domain=${domain}`;
};
