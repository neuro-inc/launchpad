import type { NextConfig } from 'next';
import { withSentryConfig } from '@sentry/nextjs';
import { execFileSync } from 'node:child_process';

import packageJson from './package.json';

const getCommitSha = (): string => {
  const commitSha = process.env.APP_COMMIT_SHA ?? process.env.GITHUB_SHA ?? '';

  if (commitSha) return commitSha.slice(0, 7);

  try {
    return execFileSync('git', ['rev-parse', '--short=7', 'HEAD'], {
      encoding: 'utf8',
    }).trim();
  } catch {
    return 'unknown';
  }
};

const buildInfo = {
  version: process.env.APP_VERSION || packageJson.version,
  commitSha: getCommitSha(),
  deployedAt: process.env.APP_DEPLOYED_AT || new Date().toISOString(),
};

const nextConfig = {
  output: 'standalone',
  env: {
    APP_VERSION: buildInfo.version,
    APP_COMMIT_SHA: buildInfo.commitSha,
    APP_DEPLOYED_AT: buildInfo.deployedAt,
  },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'storage.googleapis.com',
        port: '',
        pathname: '/**',
      },
    ],
  },
} satisfies NextConfig;

export default withSentryConfig(nextConfig, {
  // For all available options, see:
  // https://www.npmjs.com/package/@sentry/webpack-plugin#options

  org: 'apolo-launchpad-tw',
  project: 'web',

  // Only print logs for uploading source maps in CI
  silent: !process.env.CI,

  // For all available options, see:
  // https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/

  // Upload a larger set of source maps for prettier stack traces (increases build time)
  widenClientFileUpload: true,

  // Uncomment to route browser requests to Sentry through a Next.js rewrite to circumvent ad-blockers.
  // This can increase your server load as well as your hosting bill.
  // Note: Check that the configured route will not match with your Next.js middleware, otherwise reporting of client-
  // side errors will fail.
  // tunnelRoute: "/monitoring",

  webpack: {
    treeshake: {
      removeDebugLogging: true,
    },
    automaticVercelMonitors: true,
  },
});
