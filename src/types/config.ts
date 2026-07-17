export type LaunchpadConfig = {
  logoUrl: string | null;
  faviconUrl: string | null;
  title: string | null;
  background: string | null; // Color value or image URL
  cssUrl: string | null;
};

// Backend response type with snake_case
export type LaunchpadConfigResponse = {
  branding?: {
    logo_url: string | null;
    favicon_url: string | null;
    title: string | null;
    background: string | null;
    background_url: string | null;
    css_url?: string | null;
  };
};

export const DEFAULT_CONFIG: LaunchpadConfig = {
  logoUrl: null,
  faviconUrl: null,
  title: 'Launchpad',
  background: null,
  cssUrl: null,
};

export const normalizeLaunchpadConfig = (
  response?: LaunchpadConfigResponse | null,
): LaunchpadConfig => {
  const branding = response?.branding;

  return {
    logoUrl: branding?.logo_url ?? DEFAULT_CONFIG.logoUrl,
    faviconUrl: branding?.favicon_url ?? DEFAULT_CONFIG.faviconUrl,
    title: branding?.title ?? DEFAULT_CONFIG.title,
    background:
      branding?.background_url ??
      branding?.background ??
      DEFAULT_CONFIG.background,
    cssUrl: branding?.css_url?.trim() || DEFAULT_CONFIG.cssUrl,
  };
};
