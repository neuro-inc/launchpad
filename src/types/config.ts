export type LaunchpadConfig = {
  logoUrl: string | null;
  faviconUrl: string | null;
  title: string | null;
  background: string | null; // Color value or image URL
};

// Backend response type with snake_case
export type LaunchpadConfigResponse = {
  branding?: {
    logo_url: string | null;
    favicon_url: string | null;
    title: string | null;
    background: string | null;
    background_url: string | null;
  };
};

export const DEFAULT_CONFIG: LaunchpadConfig = {
  logoUrl: null,
  faviconUrl: null,
  title: 'Launchpad',
  background: null,
};
