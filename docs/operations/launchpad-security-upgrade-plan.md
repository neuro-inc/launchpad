# Launchpad security upgrade plan

## Follow-up findings

- [ ] Drop legacy shared PostgreSQL support. Remove the Helm subchart and the installer's shared database fallback once both prerequisites are met.
  - [ ] Confirm every active Launchpad instance was originally installed on `26.11.0` or later. Upgrading an older installation keeps its shared database.
  - [ ] Verify that Launchpad and Keycloak use separate PostgreSQL services in every active instance.
- [ ] Restrict public Keycloak administration and the master realm. Review ForwardAuth and remove shared-domain bearer cookies from requests delivered to less-trusted downstream applications.
- [ ] Rebuild the backend on a patched Python 3.13 base and scan the release images.
