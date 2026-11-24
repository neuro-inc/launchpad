# Database backup and restore

Keycloak upgrades can migrate its database schema when the new pod starts. Keep a pre-upgrade backup of both the Keycloak and Launchpad databases so you can restore the previous versions together. An App revision rollback alone leaves the migrated schemas in place. [Keycloak upgrading guide](https://www.keycloak.org/docs/latest/upgrading/)

## Back up before upgrading

1. Record the Apolo App ID and current revision, the running Launchpad, Keycloak, and PostgreSQL image versions, and the database and PVC names. Record the credential references and confirm your organization’s recovery process can restore their values. Keep existing hostname and realm configuration with the backup. Verify that self-service password reset is disabled in the running realm. Keycloak preserves the settings of an existing realm when it starts with realm import enabled.
2. Confirm the database layout. New installations use one PostgreSQL server with separate `launchpad` and `keycloak` databases and login roles. Upgrades retain the shared login on legacy Bitnami installations. Verify the saved Apolo credentials before upgrading. Legacy Bitnami uses `keycloak-db-pswd-<app-id>`. Installations with dedicated roles use one `<role>-dedicated-db-pswd-<app-id>` secret per role. Recover missing credentials from the existing deployment through the approved secrets workflow before continuing.
3. Schedule a maintenance window and stop writes from Launchpad and Keycloak. Keep the database servers online while taking both backups. This gives you a consistent rollback point for the App and its login configuration.
4. Use a new restricted backup directory and a PostgreSQL client at least as new as the database server. Take a custom-format dump of each database using approved connections with access to all tables and sequences. The example assumes libpq services named `launchpad-backup` and `keycloak-backup`. In a shared installation, both services connect to the same host. Use the actual database names if they differ.

   ```sh
   umask 077
   pg_dump --format=custom --file=launchpad.dump 'service=launchpad-backup dbname=launchpad'
   pg_dump --format=custom --file=keycloak.dump 'service=keycloak-backup dbname=keycloak'
   pg_restore --list launchpad.dump >/dev/null
   pg_restore --list keycloak.dump >/dev/null
   ```

5. Store both dumps together in encrypted, access-controlled storage. They contain sensitive user and authentication data. Record the database owners, database-level grants, and settings separately. Keep role credentials recoverable through your secrets store. Rehearse the restore below on separate PostgreSQL instances before rolling out.

## Restore and verify

1. For a rehearsal, provision separate recovery servers on the previous PostgreSQL major version. For a managed App rollback, coordinate with the platform operator to keep Launchpad and Keycloak stopped while PostgreSQL stays available. The App derives its database Service names from its App ID. Preserve the upgraded databases with a snapshot or separate backup, then rename them and create empty databases with the original names on the original servers. Restore the recorded owners, credentials, grants, and settings. Agree on this procedure before upgrading so the App can keep its original database connections during recovery.
2. Restore both pre-upgrade backups. Use connections with privileges to restore the original ownership.

   ```sh
   pg_restore --exit-on-error --single-transaction \
     --dbname='service=launchpad-recovery dbname=launchpad' launchpad.dump
   pg_restore --exit-on-error --single-transaction \
     --dbname='service=keycloak-recovery dbname=keycloak' keycloak.dump
   ```

3. Apply the previous App revision after both database restores complete. Verify that the previous image pins and credential references are in place when the App starts. Keep the upgraded databases and PVCs for investigation until recovery is verified.
4. Verify Keycloak and Launchpad readiness. Sign in as an existing user, confirm their realm roles and registered Apps, and open a protected App through the auth middleware. Reopen traffic after these checks pass. The restored state is from the time of the backup, so reconcile any writes made after that point.

If PostgreSQL itself fails to initialize or open its data directory, preserve the volume and diagnose the PostgreSQL failure before retrying. Launchpad retries database and role setup after PostgreSQL can start.
