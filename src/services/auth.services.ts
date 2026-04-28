import { getSiteUrl } from '@utils/helpers';

const SET_COOKIE_PATH = '/callback';

let lastToken: string | null = null;
let pending: Promise<void> | null = null;

export async function setLaunchpadCookie(token?: string) {
  if (!token || token === lastToken) return;

  if (pending) {
    await pending;
    if (token === lastToken) return;
  }

  const MAX_ATTEMPTS = 3;

  pending = (async () => {
    try {
      const siteUrl = await getSiteUrl();
      const url = `${siteUrl}${SET_COOKIE_PATH}`;

      let attempt = 0;
      let lastError: any = null;

      while (attempt < MAX_ATTEMPTS) {
        attempt += 1;
        try {
          // eslint-disable-next-line no-console
          console.debug('setLaunchpadCookie attempt %d -> %s', attempt, url);

          const res = await fetch(url, {
            method: 'POST',
            headers: {
              Authorization: `Bearer ${token}`,
            },
            credentials: 'include',
          });

          if (res.ok) {
            // eslint-disable-next-line no-console
            console.info('launchpad cookie set');
            lastToken = token;
            return;
          }

          // If the response is 401/403, do not retry
          if (res.status === 401 || res.status === 403) {
            const text = await res.text().catch(() => '');
            // Keep line short for prettier
            throw new Error(
              `Unauthorized setting cookie: ${res.status} ${text}`,
            );
          }

          lastError = new Error(`Failed to set cookie: ${res.status}`);
        } catch (err) {
          lastError = err;
          // exponential backoff with jitter
          const backoff =
            Math.pow(2, attempt) * 100 + Math.floor(Math.random() * 100);
          // eslint-disable-next-line no-console
          console.warn(
            'setLaunchpadCookie failed (attempt %d):',
            attempt,
            err,
            'backoff:',
            backoff,
          );
          // wait before next attempt
          // eslint-disable-next-line no-await-in-loop
          await new Promise((r) => setTimeout(r, backoff));
        }
      }

      throw lastError;
    } finally {
      pending = null;
    }
  })();

  await pending;
}

export default setLaunchpadCookie;
