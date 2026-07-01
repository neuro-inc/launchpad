import { NextResponse } from 'next/server';

import {
  DEFAULT_CONFIG,
  LaunchpadConfig,
  LaunchpadConfigResponse,
} from '@typings';
import { getRawConfig } from '@features';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function GET() {
  try {
    const response = (await getRawConfig()) as LaunchpadConfigResponse;

    // Extract branding data and convert snake_case to camelCase
    const { branding } = response;

    const config: LaunchpadConfig = {
      logoUrl: branding?.logo_url ?? DEFAULT_CONFIG.logoUrl,
      faviconUrl: branding?.favicon_url ?? DEFAULT_CONFIG.faviconUrl,
      title: branding?.title ?? DEFAULT_CONFIG.title,
      background:
        branding?.background_url ??
        branding?.background ??
        DEFAULT_CONFIG.background,
    };

    return NextResponse.json(config);
  } catch (error) {
    console.error(
      JSON.stringify({
        scope: 'launchpad-net',
        event: 'api-config-error',
        ts: new Date().toISOString(),
        error:
          error instanceof Error
            ? { name: error.name, message: error.message }
            : { message: String(error) },
      }),
    );

    // Return default config on error
    return NextResponse.json({
      logoUrl: null,
      faviconUrl: null,
      title: null,
      background: null,
    });
  }
}
