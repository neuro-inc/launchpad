import { getServerSession } from 'next-auth';
import { getSession } from 'next-auth/react';

import { IS_PRODUCTION, SERVER_API_URL } from '@constants';
import { getAuthOptions } from '@features';

async function makeRequest<T>(
  url: string,
  options: RequestInit = {},
  token?: string,
): Promise<T> {
  const headers = new Headers(options.headers);

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(`${SERVER_API_URL}${url}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);

    if (!IS_PRODUCTION) {
      // eslint-disable-next-line no-console
      console.log(`Error in request ${url}:`, { error });
      // eslint-disable-next-line no-console
      console.log('Request failed with status: ', response.status);
    }

    throw new Error(error);
  }

  return response.json() as Promise<T>;
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
