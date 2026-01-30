import { NextRequest, NextResponse } from 'next/server';
import { getToken } from 'next-auth/jwt';

import { getAuthOptions } from '@features';
import { getServerApiUrl } from '@utils/helpers/getSiteUrl';

export const runtime = 'nodejs';

/**
 * API Proxy endpoint to forward client requests to backend with authentication
 * This avoids including tokens in the session cookie (which causes size issues)
 */

async function handleRequest(
  request: NextRequest,
  path: string[],
  method: string,
) {
  try {
    const authOptions = await getAuthOptions();
    const token = await getToken({
      req: request,
      secret: authOptions.secret as string,
    });

    if (!token?.accessToken) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const serverApiUrl = await getServerApiUrl();
    const apiPath = path.join('/');
    const searchParams = request.nextUrl.searchParams.toString();
    const url = `${serverApiUrl}/${apiPath}${searchParams ? `?${searchParams}` : ''}`;

    const headers = new Headers();
    headers.set('Authorization', `Bearer ${token.accessToken}`);
    headers.set('Content-Type', 'application/json');

    const options: RequestInit = {
      method,
      headers,
    };

    // Add body for POST, PUT, PATCH requests
    if (method !== 'GET' && method !== 'DELETE') {
      const body = await request.text();
      if (body) {
        options.body = body;
      }
    }

    const response = await fetch(url, options);

    if (!response.ok) {
      const error = await response.json().catch(() => null);
      return NextResponse.json(
        error || { error: `Request failed with status ${response.status}` },
        { status: response.status },
      );
    }

    const data = await response.json().catch(() => null);
    return NextResponse.json(data);
  } catch (error: any) {
    console.error('API Proxy error:', error);
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 },
    );
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const resolvedParams = await params;
  return handleRequest(request, resolvedParams.path, 'GET');
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const resolvedParams = await params;
  return handleRequest(request, resolvedParams.path, 'POST');
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const resolvedParams = await params;
  return handleRequest(request, resolvedParams.path, 'PUT');
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const resolvedParams = await params;
  return handleRequest(request, resolvedParams.path, 'DELETE');
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const resolvedParams = await params;
  return handleRequest(request, resolvedParams.path, 'PATCH');
}
