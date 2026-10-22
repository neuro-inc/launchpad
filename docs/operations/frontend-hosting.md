# Launchpad frontend hosting

## Configuration

Configure `FONTAWESOME_NPM_AUTH_TOKEN` as an Actions secret and a separate Dependabot registry secret.
Confirm that Launchpad's Actions token can publish all three GHCR packages, including `launchpad-web-ui`.
Cleanup requires admin access to those packages and `contents: write` for visibility of draft releases.
Require backend, frontend, hook, release validation, and release assembly checks before merging.
The `production` environment records publication; configure approval rules when the team requires them.

Freeze publication in the old frontend repository before enabling the consolidated pipeline.
Retain its deployment records, Netlify credentials, and rollback access throughout migration.

Each migrated App owns its frontend Deployment, Service, and session Secret.
The chart sets `NEXTAUTH_URL` to the App's canonical HTTPS origin.
Input processing persists the session secret in platform secrets before deployment and reuses it when an installation is retried.
Upgrades reuse `launchpad-frontend-session`; preserve this secret during rollback to avoid invalidating sessions.
Apps without `FRONTEND_IMAGE_DIGEST` retain the Netlify compatibility path.

## Development and release

Successful master CI builds backend, frontend, and hook images together and publishes their `master` aliases.
The development catalog discovers the `master` template through its Git loader.
Wait for successful master CI before installing or upgrading that template.
CI does not request installed App upgrades, although Argo CD can synchronize changes for Apps tracking a branch.

Complete development acceptance against the selected master CI combination before publishing a version.
If you rebuild that combination, repeat acceptance.
The tag, CI source commit, and release manifest must identify the same exact commit.

Use the Web UI convention `vYY.M.N`, such as `v26.10.1`.
`YY` is the two-digit year, and `M` is the month without a leading zero.
Set `N` to the month's highest existing number plus one, starting at `0` when no tags exist.
Do not move an existing tag.

```sh
git tag "$RELEASE_TAG" "$TESTED_COMMIT"
git push origin "$RELEASE_TAG"
```

The `Release` workflow selects successful master CI for the tagged commit and publishes its exact images and chart without rebuilding.
If CI has not finished, wait for success and rerun Release.
Initial publication requires the unexpired CI artifact.
Publication rejects mismatched sources, altered charts, ambiguous artifacts, and conflicting existing image aliases.
Wait for the entire Release workflow to succeed before installing the version.
Publication does not upgrade installed production Apps.

## Release recovery

The GitHub Release retains `release.json` and the original chart archive.
Assets must match exactly; publication never overwrites them.
The workflow publishes its draft only after all image aliases pass verification.
A retry can complete interrupted publication using the saved assets, even after the CI artifact expires.
Keep versioned images and release assets for supported App versions.

For manual recovery, dispatch Release from `master` with the existing tag and its successful master CI run:

```sh
gh workflow run release.yml --repo neuro-inc/launchpad --ref master \
  -f build_run_id="$BUILD_RUN_ID" -f release_tag="$RELEASE_TAG"
```

## Temporary image retention

Weekly cleanup removes CI image versions older than 90 days and their orphaned child manifests.
It preserves non-CI tags, including version, `master`, and branch aliases.
It also protects digests in draft and published release manifests and all descendants of protected indexes.
Unknown untagged versions remain unless they belong to an expired CI image graph.
Cleanup uses `ci-gc-<digest>` tags to retain ownership after interrupted deletions.
A retry can remove marked versions without another retention delay, unless publication has protected them.

Manual cleanup dispatch defaults to a dry run; review its output before setting `apply` to `true`.
Registry and metadata errors stop cleanup before deletion begins.
Publication and cleanup share the queued `launchpad-registry` concurrency group.
Launchpad collects protected digests from its release manifests before calling the shared `reuse` cleanup action.
Do not modify registry versions outside that group while cleanup runs.
Use published versions for installations that must remain supported beyond the CI retention window.

## Acceptance and rollback

1. Install or upgrade an App in the explicit development context.
2. Verify its image digests, Deployment health, and client Service selector.
3. Verify DNS and TLS for its public hostname before browser testing.
4. Verify login, logout, token refresh, and backend requests.
5. Upgrade the App and verify that an existing session remains valid.
6. Verify custom hostname authentication when applicable.
7. Publish the tested combination after development acceptance passes.
8. Upgrade production Apps explicitly through the normal App workflow.

Restore the previous verified App version for an ordinary rollback.
Use the previous frontend-free hook version when restoring Netlify routing.
Keep Netlify credentials until all App migrations and rollback periods have completed.
Coordinate DNS and TLS changes with the separate cloud-infra migration.

## Local checks

Run `make test-hooks`, `make test-release`, and `make lint-release` for processor, chart, and release checks.
Release checks require Python 3.12, Helm 3.16.3, mypy 1.18.2, Bash, and jq.
From `frontend/`, run `npm ci`, `npm run lint`, and `npm run build` with Node.js 22.
Set `FONTAWESOME_NPM_AUTH_TOKEN` before dependency installation.
Verify `/api/health` in the built container with a synthetic session secret.
Local checks do not replace browser acceptance against the App's Keycloak and backend.
