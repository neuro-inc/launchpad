import { getServerSession } from 'next-auth';
import { getSession } from 'next-auth/react';

import { getAuthOptions } from '@features';

import { fetchWithRetry } from './fetchWithRetry';
import { getServerApiUrl } from './getSiteUrl';

const logRequest = (event: string, data: Record<string, unknown>) => {
  if (process.env.LAUNCHPAD_DEBUG_LOGS !== 'true') {
    return;
  }

  console.error(
    JSON.stringify({
      scope: 'launchpad-net',
      event,
      ts: new Date().toISOString(),
      ...data,
    }),
  );
};

const serializeError = (error: unknown) =>
  error instanceof Error
    ? { name: error.name, message: error.message }
    : { message: String(error) };

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

  const fullUrl = `${serverApiUrl}${url}`;
  const requestContext = {
    route: url,
    fullPathname: new URL(fullUrl).pathname,
    isServer: typeof window === 'undefined',
    hasCallerSignal: Boolean(options.signal),
  };

  // Server-side without a caller-managed signal: use serverFetch so Lambda
  // post-freeze network hangs are retried with exponential backoff.
  // Client-side and caller-managed AbortSignal: use standard fetch.
  let response: Response;
  try {
    if (typeof window === 'undefined' && !options.signal) {
      response = await fetchWithRetry(fullUrl, { ...options, headers });
    } else {
      response = await fetch(fullUrl, { ...options, headers });
    }
  } catch (error) {
    logRequest('request-transport-error', {
      ...requestContext,
      error: serializeError(error),
    });
    throw error;
  }

  if (!response.ok) {
    const error = await response.json().catch(() => null);

    logRequest('request-error-response', {
      ...requestContext,
      status: response.status,
    });

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
  const authOptions = await getAuthOptions();
  const session = await getServerSession(authOptions);

  return makeRequest<T>(url, options, session?.accessToken);
}

export async function clientRequest<T>(
  url: string,
  options: RequestInit = {},
): Promise<T> {
  const session = await getSession();

  return makeRequest<T>(url, options, session?.accessToken);
}

export async function request<T>(
  url: string,
  options: RequestInit = {},
): Promise<T> {
  return typeof window === 'undefined'
    ? serverRequest<T>(url, options)
    : clientRequest<T>(url, options);
}
