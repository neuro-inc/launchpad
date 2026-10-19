import { Metadata } from 'next';

import { AuthPage } from './AuthPage';

export const metadata: Metadata = {
  title: 'Sign In - Launchpad',
  description:
    'Sign in to Launchpad to access your applications and development environments.',
  keywords: ['login', 'sign in', 'authentication', 'launchpad', 'keycloak'],
  robots: {
    index: false,
    follow: false,
  },
};

export default AuthPage;
