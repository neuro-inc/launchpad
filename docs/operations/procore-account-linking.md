# Procore automatic account linking

Launchpad can link a Procore identity to an existing Keycloak account with a matching email or username.
The existing account keeps its ID, roles, and groups.
This policy removes the additional ownership check, including for administrator accounts.
Enable it only when you trust Procore's identity and email claims for every account that can match.

The App can configure the Procore provider through optional inputs.
It does not assign permissions to new users.
New accounts follow the realm's existing default roles and groups.
Other identity providers and the realm's default first-login flow remain unchanged.

## Configuration and migration

The App input `procore_automatic_linking` has three states:

| Value | Behavior |
| --- | --- |
| Unset (`null`) | Launchpad preserves the current first-login binding. |
| `true` | Launchpad creates or verifies `procore-auto-link` and binds only the `procore` provider. |
| `false` | Launchpad removes its binding and restores the realm's default first-login flow. It preserves existing identity links. |

For a new provider, enable **Configure Procore identity provider** in the App inputs.
Supply a user-level OAuth client ID and a project secret reference.
Select the Procore environment that issued those credentials.
Register this redirect URI in your Procore application's credentials:

```text
<Keycloak web URL>/realms/launchpad/broker/procore/endpoint
```

The existing Keycloak output provides the web URL.
The App uses Procore's OAuth endpoints and maps `id` to the user ID and `login` to username and email.
Production uses `login.procore.com` and `api.procore.com`.
Sandbox uses `login-sandbox.procore.com` and `sandbox.procore.com`.

This example configures a sandbox provider and enables automatic linking:

```yaml
procore_identity_provider:
  client_id: YOUR_PROCORE_CLIENT_ID
  client_secret:
    key: PROCORE_CLIENT_SECRET
  environment: sandbox
  enabled: true
  trust_email: true
procore_automatic_linking: true
```

Create the referenced secret in the same Apolo project before applying the configuration.
The processor and Helm values contain only its reference.
Only the configuration Job mounts the selected secret key.
Automatic linking requires both an enabled provider and explicit trust in Procore email claims.

Leave `procore_identity_provider` unset to preserve a manually configured provider.
Removing this input does not delete the provider, revoke credentials, or remove existing identity links.
To disable Procore sign-in, set its `enabled` field to `false`.
Also set `procore_automatic_linking` to `false` or leave it unset.
The App rejects automatic linking when the provider is disabled.
Update the referenced project secret and reconfigure the App to rotate the credential.
For existing providers, the App rejects changes to the client ID, environment endpoints, and ID, username, or email mappings.
It preserves other provider options, mappers, roles, groups, and existing first-login bindings unless you explicitly change the linking option.

For an existing installation, review its provider and matching administrator accounts before enabling this input.
A bounded Argo Sync Job applies the migration after Keycloak becomes healthy.
The Job mounts the Keycloak administrator credential and, when configured, the selected Procore client-secret key.
It does not replace the realm, import users, or modify roles and groups.
Keycloak skips startup imports for existing realms, so the Job uses the Admin API for migration.
New realms receive the same inactive flow definition during startup import.

The migration accepts the default provider binding or the dedicated `procore-auto-link` binding.
It adopts an existing flow only when its execution structure matches the dedicated definition.
It resumes incomplete flows only when their description identifies the managed definition.
It rejects custom bindings, custom executions, and execution configuration without changing them.
It refuses flow repairs when another login binding or a realm binding uses that flow.
Keep Keycloak configuration unchanged during migration because its Admin API does not provide conditional updates.

## Manual preflight

Use the backend environment from the same Launchpad revision.
Supply the administrator password through a protected file.
Do not put credentials in command arguments or logs.

```sh
poetry run python -m scripts.keycloak.procore_linking \
  --server https://KEYCLOAK_ORIGIN \
  --realm launchpad \
  --username admin \
  --password-file /protected/keycloak-admin-password \
  --flow-file charts/launchpad/files/procore-auto-link.json \
  --enable
```

This command validates the configuration without writes.
Add `--apply` only when the preflight passes and you intend to activate the policy.
For the managed App, use its configuration input instead of maintaining a separate manual policy.

## Validation and rollback

Run `make test-unit`, `make test-integration`, and `make test-hooks` before release.
The integration test uses disposable Keycloak 26.3.0 and requires Docker.
It verifies idempotency, fresh realm import, rollback, and preservation of users, roles, groups, and unrelated provider settings.

After deployment, test Procore login with an existing account and a new account.
Verify the existing account's identity link, ID, roles, and groups.
Verify that another provider still uses its previous login flow.
The automated tests do not use the external Procore service.

To restore the realm's default login policy, set `procore_automatic_linking: false` and reconfigure the App.
Leaving the input unset preserves the current binding; it does not disable an already active policy.
Rollback preserves existing identity links and the inactive flow.
Review an incorrectly linked identity separately before revoking it.

References: [Keycloak first broker login](https://www.keycloak.org/docs/latest/server_admin/index.html#_identity_broker_first_login)
and [startup realm import](https://www.keycloak.org/server/importExport).

Provider references: [Procore user information](https://developers.procore.com/reference/rest/me?version=latest)
and [Procore OAuth setup](https://developers.procore.com/documentation/content/quick-start-guide).
