import { NextResponse } from 'next/server';

import {
  DEFAULT_CONFIG,
  LaunchpadConfigResponse,
  normalizeLaunchpadConfig,
} from '@typings';
import { getRawConfig } from '@features';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function GET() {
  try {
    const response = (await getRawConfig()) as LaunchpadConfigResponse;

    const config = normalizeLaunchpadConfig(response);

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
    return NextResponse.json(DEFAULT_CONFIG);
  }
}
