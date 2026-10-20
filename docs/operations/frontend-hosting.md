# Launchpad frontend hosting

## App ownership

Each App with a selected frontend digest owns its frontend Deployment, Service, and session Secret.
The existing client Service retains its name and ingress route.
Its type changes from ExternalName to ClusterIP when the hook supplies a frontend digest.

The frontend reads `NEXTAUTH_SECRET` from its App-specific Kubernetes Secret.
The chart supplies the App's canonical HTTPS origin through `NEXTAUTH_URL` for Keycloak callbacks.
The processor stores the generated session value as the App secret `launchpad-frontend-session`.
Subsequent upgrades retrieve that value instead of invalidating sessions.
The frontend image rejects missing or short secrets before starting.

An empty `FRONTEND_IMAGE_DIGEST` retains Netlify routing and Netlify chart hooks for existing Apps.
Remove that compatibility path only after every installed App has migrated and its rollback period has ended.
Do not remove its persistent session secret during rollback.

## Complete App builds and release assembly

Backend, frontend, and hook images retain their existing registry names.
Backend, frontend, hook, and release checks run before the build job.
One CI job builds all three images from the same checked-out commit.
The hook build receives the backend and frontend digests directly from the preceding build steps.
The workflow does not select images from earlier runs.
Docker can reuse its normal build layers, and each build pulls current base images.

A successful `master` CI run records one `launchpad-release` artifact after every required check and build succeeds.
Its schema version is `2`.
The manifest contains the source commit, all three immutable image references, and the packaged chart's filename and SHA-256 checksum.
The complete CI job provides the source association for all three images.
No component fingerprints or baseline artifacts are required.
Earlier schema versions are rejected and require a new successful CI build.
Publishing an individual image does not establish a complete App release.

Builds use staging tags before final assembly.
After all checks and builds pass, master CI publishes the verified combination through the three `master` image aliases.
The hook alias changes last and embeds the selected backend and frontend digests.
Failed validation or assembly cannot advance these aliases.
A superseded master run cannot replace the current development aliases.
Runs for the same Git ref publish serially to avoid concurrent alias updates.
Workflow retries replace their named artifacts.
Release downloads reject duplicate artifacts instead of selecting an earlier attempt.
Malformed release evidence or registry failures stop the release.

The development catalog discovers the `master` template through its existing Git loader.
Catalog refresh can occur before image publication finishes.
Wait for successful master CI before installing or updating that template.
This workflow does not request App upgrades.
Apps tracking a Git branch can still synchronize chart changes through Argo CD.

## Production publication

A maintainer verifies the selected App combination in any development installation before publishing it.
Use the acceptance procedure below to check authentication, session continuity, custom hostnames, upgrades, and rollback.
Development acceptance is manual.
Do not rerun the selected CI build after development acceptance.
Repeat acceptance if that build produces a replacement artifact.
CI verifies artifact integrity and source compatibility without querying an installed App or Argo CD.

The `Release` workflow starts when a maintainer pushes a `v*` tag.
It selects the latest successful master `CI` run for that exact tagged commit.
A successful run must exist before publication starts.
If the tag arrives before CI finishes, wait for CI and rerun the failed Release workflow.
The workflow does not rebuild images or select a nearby commit.

The workflow accepts successful `CI` runs triggered by a master push or a manual master dispatch.
It rejects PR runs, failed runs, expired artifacts, and ambiguous artifacts.
The release manifest must identify the selected CI run's source commit.
The tagged commit, successful CI run, and release manifest must identify the same exact source commit.

Complete development acceptance before pushing the version tag:

```sh
git tag "$RELEASE_TAG" "$TESTED_COMMIT"
git push origin "$RELEASE_TAG"
```

Do not move an existing tag.
Pushing the tag confirms development acceptance of its CI combination.
No workflow queries an installed App or Argo CD to establish that acceptance.

The manual `Release` dispatch remains available from `master` for recovery and explicit selection:

| Input | Purpose |
| --- | --- |
| `build_run_id` | It selects the successful `master` CI run tested in development. |
| `release_tag` | It selects an existing reviewed `v*` Git tag to publish. |

```sh
gh workflow run release.yml --repo neuro-inc/launchpad --ref master \
  -f build_run_id="$BUILD_RUN_ID" -f release_tag="$RELEASE_TAG"
```

Manual recovery also requires the exact tagged commit.
A different commit requires another successful CI build and development acceptance, even when only documentation changes.

The workflow verifies all source images and existing version aliases before publishing any alias.
An existing alias must already select the tested digest.
Publication preserves each image digest and retains the original release manifest and chart archive without rebuilding or repackaging.
A retry with the same inputs can complete interrupted publication.
Wait for the complete Release workflow before installing the tagged App version.
Keep its `launchpad-release` artifact with the operational release record.

The maintainer's tag push or manual dispatch records release approval after development acceptance.
The GitHub `production` environment records the release job.
Configure additional environment approval rules when the repository supports them and the team requires them.
The built-in `GITHUB_TOKEN` reads repository artifacts and publishes registry aliases.
Publication needs no Argo credentials, App-name setting, or environment configuration variables.

Configure `FONTAWESOME_NPM_AUTH_TOKEN` as an Actions secret for frontend builds.
BuildKit mounts the committed `.npmrc` template and exposes the token only to the dependency installation command.
The workflow does not generate a credential file on the runner.
Configure that credential separately as a Dependabot registry secret.
Confirm that Launchpad's Actions token can publish the existing frontend GHCR package.
Grant package access to this repository if its current permissions permit only `launchpad-web-ui`.
Local hook builds without `APP_IMAGE_DIGEST` retain the existing tag behavior.

## Publication prerequisites

Freeze publication in the old frontend repository before enabling the consolidated pipeline.
Transfer its required Actions settings, Dependabot secret, production environment rules, and GHCR package access.
Require backend, frontend, hook, release validation, and release assembly checks in branch protection.

Fork PRs run the separate release checks and fail frontend validation before private dependency installation.
GitHub does not provide repository secrets to forks.
A maintainer must copy those changes to a repository branch and create a replacement PR for complete frontend validation.

Verify the consolidated validation, tag publication, and App upgrade before archiving the old repository.
Retain old deployment records and Netlify rollback access throughout the hosting migration.
The old `LAUNCHPAD_FRONTEND_IMAGE_DIGEST`, `FRONTEND_RELEASE_RUN_ID`, and `FRONTEND_RELEASE_READ_TOKEN` settings have no consumers in the consolidated pipeline.
Remove those settings after confirming the replacement workflows.

## Acceptance and rollback

1. Install or upgrade an App in the explicit development context.
2. Verify its frontend image digest, Deployment health, and client Service selector.
3. Verify the public hostname's DNS and TLS.
4. Verify login, logout, token refresh, and backend requests in a browser.
5. Upgrade the App and verify an existing session remains valid.
6. Verify custom hostname authentication when the App uses a custom hostname.
7. Publish the tested App combination after all development verification passes.
8. Upgrade production Apps with the verified release combination.

Restore the previous verified App release combination for an ordinary rollback.
Use the previous frontend-free hook release when restoring legacy Netlify routing.
Keep Netlify credentials until all App upgrades and rollback periods have completed.
Coordinate wildcard DNS with the infrastructure migration procedure.
No replacement automatic PR preview environment is configured.

## Local validation

Run `make test-hooks` to verify processors, chart routing, and ownership.
Run `make test-release` with Python 3.12 and Helm 3.16.3 to verify source identity, packaging, and publication.
Run `make lint-release` with mypy 1.18.2 to check all release scripts and tests.
The explicit configuration keeps release checks independent of backend mypy plugins.
Run `npm ci`, `npm run lint`, and `npm run build` from `frontend/` with Node.js 22.
Set `FONTAWESOME_NPM_AUTH_TOKEN` before dependency installation.
Verify `/api/health` in the built container with a synthetic session secret.
Local verification does not replace browser acceptance against the App's Keycloak and backend.
