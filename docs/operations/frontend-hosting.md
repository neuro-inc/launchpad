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

## Component builds and release assembly

Backend, frontend, and hook images retain their existing registry names.
Each build waits for its own component checks and the release verifier checks.
Backend tests and frontend tests run independently.
Hook publication also waits for the selected backend and frontend images because the hook embeds their digests.

A successful `master` CI run records one `launchpad-release` artifact after every required check and image selection succeeds.
The artifact contains all three immutable image references, their build commits, their input fingerprints, and the packaged chart.
The chart record includes its source fingerprint and archive checksum.
This artifact identifies the tested App combination.
Publishing an individual image does not establish a complete App release.

Subsequent runs can reuse images from the latest successful `master` release when its artifact remains available.
Development reuse requires the baseline source commit to be an ancestor of the selected revision.
The verifier reconstructs each recorded fingerprint from its original Git commit.
It compares that fingerprint with the selected component's current inputs before permitting reuse.
The fingerprint covers tracked Docker inputs, publication recipes, and release verification code.
The hook fingerprint also includes the selected backend and frontend digests.

A backend-only change can therefore reuse the frontend image.
Changes to shared Python packaging or processor files can rebuild both backend and hook images.
Chart-only changes reuse images and create a different App release combination.

Reused images retain their original build commit in the release record and image metadata.
Registry alias publication must preserve the recorded digest.
CI verifies the published alias before accepting the component record.
Runs for the same Git ref publish serially to avoid concurrent alias updates.

An unavailable or expired baseline artifact causes fresh development builds.
Workflow retries replace their named artifacts.
Release downloads reject duplicate artifacts instead of selecting an earlier attempt.
Malformed release evidence or registry failures stop the release.
The first run without an available baseline builds all images.
If an earlier artifact lacks provenance, dispatch a forced rebuild.

Use `CI` workflow dispatch on `master` with `rebuild_images` enabled to refresh all images and their base images.
That run disables Docker layer reuse and records the replacement combination for subsequent reuse.
Floating base image tags refresh only during a forced build or another required rebuild.

## Production promotion

The `Verify production App promotion` workflow selects a successful `master` CI release.
It verifies both runtime images in the development App's managed backend and frontend Deployments.
Both Deployments must report completed generations and fully updated, ready, available replicas.
Aggregate image summaries cannot substitute for live Deployment manifests.
The Argo CD Application must also be healthy and synchronized.
Every completed source revision must match its observed synchronized revision.
The resolved Launchpad chart revision must have the recorded chart input fingerprint.
Promotion evidence binds the complete release manifest by checksum, including the hook image and chart archive.

Production publication requires an explicit dispatch against an existing `v*` tag.
Pushing a tag does not publish images.
The dispatch requires `promotion_run_id`, which identifies a successful `Verify production App promotion` run.
No repository variable selects the release.
Tag dispatches reuse the complete promoted combination without rebuilding images or repackaging the chart.
Each component's recorded inputs must match the tagged source.
A different repository commit can qualify when every build input remains unchanged.
Changed component or chart inputs require a new development release and promotion.
The built-in `GITHUB_TOKEN` reads artifacts within this repository.

### Environment setup

Keep nonsecret promotion settings in [production.env](../../.github/environments/production.env).
`ARGOCD_SERVER` identifies the development Argo CD HTTPS origin.
`DEV_LAUNCHPAD_ARGO_APPLICATION` identifies the exact installed development App to verify.
Confirm both values before importing them.

Create the GitHub `production` environment with the required approval rules.
Allow `master` because the promotion verifier runs from that branch.
Import the versioned configuration with this command:

```sh
make setup-production-environment
```

The command uses `gh variable set --env-file` for `neuro-inc/launchpad` and the `production` environment.
It rejects empty values before making a GitHub request.
It does not create the environment or change its protection rules.
Rerun the command after a reviewed configuration change.
Removing a key from the file does not delete its GitHub variable.

Configure these secrets separately:

| Location | Secret | Purpose |
| --- | --- | --- |
| Repository Actions secrets | `FONTAWESOME_NPM_AUTH_TOKEN` | It permits frontend dependency installation and Docker builds. |
| Repository Dependabot secrets | `FONTAWESOME_NPM_AUTH_TOKEN` | It permits private registry access for dependency updates. |
| `production` environment secrets | `ARGOCD_READ_TOKEN` | It permits read-only access to the development Argo Application. |

### Release commands

Set `BUILD_RUN_ID` to the successful `master` CI run for the tested App combination.
Dispatch the promotion verifier from `master` after development acceptance:

```sh
gh workflow run promote-release.yml --repo neuro-inc/launchpad --ref master \
  -f build_run_id="$BUILD_RUN_ID"
```

Wait for the promotion workflow to succeed.
Set `PROMOTION_RUN_ID` to that successful promotion run ID.
Create the reviewed version tag before dispatching publication.
Set `RELEASE_TAG` to that existing tag.
Do not move an existing tag.

```sh
gh workflow run ci.yaml --repo neuro-inc/launchpad --ref "$RELEASE_TAG" \
  -f promotion_run_id="$PROMOTION_RUN_ID"
```

The verifier rejects missing or invalid promotion IDs, unapproved artifacts, non-version tags, and forced production rebuilds.
A branch dispatch cannot select a production promotion.
Wait for image publication and final release assembly before installing the tagged App version.

Confirm that Launchpad's Actions token can publish the existing frontend GHCR package.
Grant package access to this repository if its current permissions permit only `launchpad-web-ui`.
Keep the complete release artifact and chart package with the operational release record.
Local hook builds without `APP_IMAGE_DIGEST` retain the existing tag behavior.

## Publication prerequisites

Freeze publication in the old frontend repository before enabling the consolidated pipeline.
Transfer its required Actions settings, Dependabot secret, production environment rules, and GHCR package access.
Require backend, frontend, hook, release validation, and release assembly checks in branch protection.

Fork PRs run the separate release checks and fail frontend validation before private dependency installation.
GitHub does not provide repository secrets to forks.
A maintainer must copy those changes to a repository branch and create a replacement PR for complete frontend validation.

Verify the consolidated validation, publication, promotion, and App upgrade before archiving the old repository.
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
7. Promote the tested App combination after all development verification passes.
8. Upgrade production Apps with the verified release combination.

Restore the previous verified App release combination for an ordinary rollback.
Use the previous frontend-free hook release when restoring legacy Netlify routing.
Keep Netlify credentials until all App upgrades and rollback periods have completed.
Coordinate wildcard DNS with the infrastructure migration procedure.
No replacement automatic PR preview environment is configured.

## Local validation

Run `make test-hooks` to verify processors, chart routing, and ownership.
Run `make test-release` with Python 3.12 and Helm 3.16.3 to verify provenance, reuse, packaging, and promotion.
Run `make lint-release` with mypy 1.18.2 to check all release scripts and tests.
The explicit configuration keeps release checks independent of backend mypy plugins.
Run `npm ci`, `npm run lint`, and `npm run build` from `frontend/` with Node.js 22.
Set `FONTAWESOME_NPM_AUTH_TOKEN` before dependency installation.
Verify `/api/health` in the built container with a synthetic session secret.
Local verification does not replace browser acceptance against the App's Keycloak and backend.
