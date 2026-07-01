'use server';

import { cache } from 'react';

import { DEFAULT_CONFIG, LaunchpadConfig } from '@typings';
import { getRawConfig } from '@features';

export const getConfig = cache(async (): Promise<LaunchpadConfig> => {
  try {
    const raw = await getRawConfig();
    const branding = raw?.branding;

    return {
      logoUrl: branding?.logo_url ?? DEFAULT_CONFIG.logoUrl,
      faviconUrl: branding?.favicon_url ?? DEFAULT_CONFIG.faviconUrl,
      title: branding?.title ?? DEFAULT_CONFIG.title,
      background:
        branding?.background_url ??
        branding?.background ??
        DEFAULT_CONFIG.background,
    };
  } catch (error) {
    console.error('Error fetching config, using defaults:', error);
    return DEFAULT_CONFIG;
  }
});
