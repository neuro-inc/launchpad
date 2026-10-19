'use client';

import { useEffect, useState } from 'react';

import { DEFAULT_CONFIG, LaunchpadConfig } from '@typings';

export function useConfig(): LaunchpadConfig {
  const [config, setConfig] = useState<LaunchpadConfig>(DEFAULT_CONFIG);

  useEffect(() => {
    fetch('/api/config')
      .then((res) => res.json())
      .then((data) => {
        setConfig({
          logoUrl: data.logoUrl ?? DEFAULT_CONFIG.logoUrl,
          faviconUrl: data.faviconUrl ?? DEFAULT_CONFIG.faviconUrl,
          title: data.title ?? DEFAULT_CONFIG.title,
          background: data.background ?? DEFAULT_CONFIG.background,
          cssUrl: data.cssUrl ?? DEFAULT_CONFIG.cssUrl,
        });
      })
      .catch((error) => {
        console.error('Error fetching config:', error);
      });
  }, []);

  return config;
}
