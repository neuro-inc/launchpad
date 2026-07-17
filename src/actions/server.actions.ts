'use server';

import { cache } from 'react';

import {
  DEFAULT_CONFIG,
  LaunchpadConfig,
  normalizeLaunchpadConfig,
} from '@typings';
import { getRawConfig } from '@features';

export const getConfig = cache(async (): Promise<LaunchpadConfig> => {
  try {
    const raw = await getRawConfig();

    return normalizeLaunchpadConfig(raw);
  } catch (error) {
    console.error('Error fetching config, using defaults:', error);
    return DEFAULT_CONFIG;
  }
});
