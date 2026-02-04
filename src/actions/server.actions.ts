'use server';

import { cache } from 'react';

import {
  DEFAULT_CONFIG,
  LaunchpadConfig,
  LaunchpadConfigResponse,
} from '@typings';
import { serverRequest } from '@utils/helpers/request';

/**
 * Get Launchpad configuration with caching
 * This will be cached for the duration of the request
 */
export const getConfig = cache(async (): Promise<LaunchpadConfig> => {
  try {
    const response = await serverRequest<LaunchpadConfigResponse>('/config');

    // Extract branding data and convert snake_case to camelCase
    // Defensively handle missing response or branding to avoid runtime errors
    const branding = response?.branding;

    // Merge with defaults to ensure all fields are present
    return {
      logoUrl: branding?.logo_url ?? DEFAULT_CONFIG.logoUrl,
      faviconUrl: branding?.favicon_url ?? DEFAULT_CONFIG.faviconUrl,
      title: branding?.title ?? DEFAULT_CONFIG.title,
      background: branding?.background ?? DEFAULT_CONFIG.background,
    };
  } catch (error) {
    console.error('Error fetching config, using defaults:', error);
    return DEFAULT_CONFIG;
  }
});
