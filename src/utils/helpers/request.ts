import { getToken } from 'next-auth/jwt';

import { getAuthOptions } from '@features';

import { getServerApiUrl } from './getSiteUrl';

async function makeRequest<T>(
  url: string,
  options: RequestInit = {},
  token?: string,
): Promise<T> {
  const serverApiUrl = await getServerApiUrl();
  const headers = new Headers(options.headers);

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(`${serverApiUrl}${url}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);

    // eslint-disable-next-line no-console
    console.log(`Error in request ${url}:`, { error });
    // eslint-disable-next-line no-console
    console.log('Request failed with status: ', response.status);

    const errorMessage =
      error?.detail?.message ??
      error?.message ??
      `Request failed with status ${response.status}`;

    throw new Error(errorMessage);
  }

  return response.json().catch(() => null) as Promise<T>;
}

export async function serverRequest<T>(
  url: string,
  options: RequestInit = {},
): Promise<T> {
  // Note: getToken() in App Router requires the request object
  // Since we don't have access to it in this helper, we need to use getServerSession
  // For a better solution, consider using server actions instead of this helper
  const authOptions = await getAuthOptions();

  // In App Router, we need to import { cookies } from 'next/headers'
  // and create a mock request object
  const { cookies: getCookies } = await import('next/headers');
  const cookieStore = await getCookies();
  const token = await getToken({
    req: {
      cookies: Object.fromEntries(
        cookieStore.getAll().map((c) => [c.name, c.value]),
      ),
    } as any,
    secret: authOptions.secret as string,
  });

  return makeRequest<T>(url, options, token?.accessToken as string);
}

export async function clientRequest<T>(
  url: string,
  options: RequestInit = {},
): Promise<T> {
  // Client-side requests go through our API proxy
  // This avoids including tokens in the session cookie
  // The proxy will add the accessToken from the JWT on the server side
  const proxyUrl = `/api/proxy${url}`;

  const headers = new Headers(options.headers);
  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(proxyUrl, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);

    const errorMessage =
      error?.detail?.message ??
      error?.message ??
      error?.error ??
      `Request failed with status ${response.status}`;

    throw new Error(errorMessage);
  }

  return response.json().catch(() => null) as Promise<T>;
}

export async function request<T>(
  url: string,
  options: RequestInit = {},
): Promise<T> {
  return typeof window === 'undefined'
    ? serverRequest<T>(url, options)
    : clientRequest<T>(url, options);
}
