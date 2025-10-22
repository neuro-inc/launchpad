import { Session } from 'next-auth';

/**
 * Check if a user has admin role
 * Checks client_roles first (what backend uses), then falls back to realm_roles
 */
export function isAdmin(session: Session | null): boolean {
  if (!session) return false;

  const clientRoles = (session.client_roles as string[]) || [];
  const realmRoles = (session.realm_roles as string[]) || [];
  const roles = clientRoles.length > 0 ? clientRoles : realmRoles;

  return roles.includes('admin');
}
