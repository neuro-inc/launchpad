# Launchpad security upgrade plan

## Follow-up findings

- [ ] Upgrade the pinned Keycloak image when a stable release includes CVE-2026-125652. Confirm the [26.8 backport](https://github.com/keycloak/keycloak/pull/55356) and the [release notes](https://www.keycloak.org/docs/latest/release_notes/) before selecting the image. Keep self-service password reset disabled.
- [ ] Drop legacy shared PostgreSQL support. Remove the Helm subchart and the installer's shared database fallback once both prerequisites are met.
  - [ ] Confirm every active Launchpad instance was originally installed on `26.11.0` or later. Upgrading an older installation keeps its shared database.
- [ ] Expose a PostgreSQL resource preset in the Launchpad App inputs for the bundled database.
- [ ] Integrate Apolo's Crunchy PostgreSQL App using `CrunchyPostgresUserCredentials` for Launchpad and Keycloak. Make the bundled PostgreSQL optional when using this integration.
- [ ] Rebuild the backend on a patched Python 3.13 base and scan the release images.
