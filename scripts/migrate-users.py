#!/usr/bin/env python3
"""Copy Keycloak launchpad users. See docs/operations/user-migration.md."""

import argparse
import asyncio
import csv
import json
import os
import secrets
import string
import sys
import time
from copy import deepcopy
from urllib.error import HTTPError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID


REALM = "launchpad"
USER_FIELDS = (
    "username",
    "email",
    "firstName",
    "lastName",
    "enabled",
    "emailVerified",
    "attributes",
    "requiredActions",
    "createdTimestamp",
    "federatedIdentities",
)


class NoRedirects(HTTPRedirectHandler):
    # Never forward admin credentials or tokens to a redirected host.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = build_opener(NoRedirects())


def request(url, method="GET", payload=None, token=None, form=False):
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        data = (urlencode(payload) if form else json.dumps(payload)).encode()
        headers["Content-Type"] = (
            "application/x-www-form-urlencoded" if form else "application/json"
        )
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with OPENER.open(
            Request(url, data, headers, method=method), timeout=60
        ) as response:
            body = response.read()
            return json.loads(body) if body else None
    except HTTPError as exc:
        # Server error bodies can contain the submitted password; do not print them.
        raise RuntimeError(f"{method} {url}: HTTP {exc.code}") from None


def validate_url(value):
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "Use an HTTP(S) base URL without credentials, query, or fragment"
        )
    if parsed.scheme == "http" and parsed.hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise ValueError("Use HTTPS, or a localhost HTTP port-forward")
    return value.rstrip("/")


class Keycloak:
    def __init__(self, url, username, password, auth_realm):
        self.url = validate_url(url)
        self.credentials = {
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": username,
            "password": password,
        }
        self.token_url = f"{self.url}/realms/{quote(auth_realm, safe='')}/protocol/openid-connect/token"
        self.expires = 0
        self.token = None

    def call(self, path, method="GET", payload=None, **query):
        if time.monotonic() >= self.expires:
            auth = request(self.token_url, "POST", self.credentials, form=True)
            self.token = auth["access_token"]
            self.expires = time.monotonic() + max(0, auth["expires_in"] - 15)
        url = f"{self.url}/admin/realms/{REALM}/{path}"
        if query:
            url += "?" + urlencode(query)
        return request(url, method, payload, self.token)

    def pages(self, path, **query):
        first = 0
        while True:
            page = self.call(path, first=first, max=100, **query)
            if not page:
                return
            yield from page
            first += len(page)

    def export(self):
        return self.call(
            "partial-export", "POST", exportClients="true", exportGroupsAndRoles="true"
        )


def clean(value):
    """Drop instance-specific IDs, preserving references expressed as names/paths."""
    if isinstance(value, dict):
        return {
            key: item if key in {"attributes", "composites"} else clean(item)
            for key, item in value.items()
            if key not in {"id", "containerId", "access"}
        }
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


def canonical(value):
    if isinstance(value, dict):
        return {key: canonical(item) for key, item in value.items()}
    if isinstance(value, list):
        return sorted(
            (canonical(item) for item in value),
            key=lambda item: json.dumps(item, sort_keys=True),
        )
    return value


def roles_by_name(export):
    roles = export.get("roles", {})
    result = {(None, role["name"]): role for role in roles.get("realm", [])}
    for client, client_roles in roles.get("client", {}).items():
        result.update({(client, role["name"]): role for role in client_roles})
    return result


def compatible_resources(source, target, require_presence=False):
    clients = {client["clientId"] for client in target.get("clients", [])}
    missing = set(source.get("roles", {}).get("client", {})) - clients
    if missing:
        raise ValueError(f"Configure missing target clients first: {sorted(missing)}")
    target_roles = roles_by_name(target)
    for key, role in roles_by_name(source).items():
        if require_presence and key not in target_roles:
            raise RuntimeError(f"Imported role is missing: {key}")
        if key in target_roles and canonical(clean(role)) != canonical(
            clean(target_roles[key])
        ):
            raise ValueError(
                f"Target role differs from source: {key}; align it before migrating"
            )
    target_groups = {group["path"]: group for group in target.get("groups", [])}
    for group in source.get("groups", []):
        other = target_groups.get(group["path"])
        if require_presence and other is None:
            raise RuntimeError(f"Imported group is missing: {group['path']}")
        if other is not None and canonical(clean(group)) != canonical(clean(other)):
            raise ValueError(
                f"Target group tree differs: {group['path']}; align it before migrating"
            )
    for field in ("defaultRole", "defaultGroups"):
        if canonical(clean(source.get(field))) != canonical(clean(target.get(field))):
            raise ValueError(f"Target {field} differs; align defaults before migrating")


def role_mappings(api, path):
    mappings = api.call(f"{path}/role-mappings")
    return {
        "realmRoles": [role["name"] for role in mappings.get("realmMappings", [])],
        "clientRoles": {
            client: [role["name"] for role in entry.get("mappings", [])]
            for client, entry in mappings.get("clientMappings", {}).items()
        },
    }


def password():
    # 32 characters, including each common password-policy character class.
    chars = [
        secrets.choice(alphabet)
        for alphabet in (
            string.ascii_uppercase,
            string.ascii_lowercase,
            string.digits,
            "!@#%+-_",
        )
    ]
    chars += [
        secrets.choice(string.ascii_letters + string.digits + "!@#%+-_")
        for _ in range(28)
    ]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


def collect_users(source):
    users = []
    for entry in source.pages("users", briefRepresentation="false"):
        path = f"users/{quote(entry['id'], safe='')}"
        user = source.call(path)
        copied = {key: user[key] for key in USER_FIELDS if key in user}
        copied.update(role_mappings(source, path))
        copied["groups"] = [group["path"] for group in source.pages(f"{path}/groups")]
        copied["_migration"] = {
            "externalStorage": bool(user.get("federationLink")),
            "serviceAccount": bool(user.get("serviceAccountClientId")),
            "credentialTypes": sorted(
                {item["type"] for item in source.call(f"{path}/credentials")}
            ),
            "hasConsents": bool(source.call(f"{path}/consents")),
        }
        users.append(copied)
    return users


def prepare_users(source_users, target, existing, temporary):
    target_users = list(target.pages("users", briefRepresentation="false"))
    names = {user["username"].casefold() for user in target_users}
    emails = {user["email"].casefold() for user in target_users if user.get("email")}
    providers = {
        provider["alias"] for provider in target.call("identity-provider/instances")
    }
    actions = {
        action["alias"] for action in target.call("authentication/required-actions")
    }
    users, skipped = [], []
    for user in source_users:
        collision = user["username"].casefold() in names or (
            user.get("email") and user["email"].casefold() in emails
        )
        if collision:
            if existing == "fail":
                raise ValueError(f"Target user already exists: {user['username']}")
            skipped.append(user["username"])
            continue
        metadata = user["_migration"]
        if metadata["externalStorage"] or metadata["serviceAccount"]:
            raise ValueError(
                f"External-storage/service-account user requires separate migration: {user['username']}"
            )
        unsupported = set(metadata["credentialTypes"]) - {
            "password",
            "password-history",
        }
        if unsupported:
            raise ValueError(
                f"{user['username']} has non-exportable credentials {sorted(unsupported)}; use a CLI export"
            )
        if metadata["hasConsents"]:
            raise ValueError(
                f"{user['username']} has client consents; use a CLI export to preserve them"
            )
        for link in user.get("federatedIdentities", []):
            if link["identityProvider"] not in providers:
                raise ValueError(
                    f"Configure target identity provider first: {link['identityProvider']}"
                )
        copied = deepcopy(
            {key: value for key, value in user.items() if key != "_migration"}
        )
        copied["credentials"] = [
            {"type": "password", "value": password(), "temporary": temporary}
        ]
        if temporary:
            copied["requiredActions"] = sorted(
                set(copied.get("requiredActions", [])) | {"UPDATE_PASSWORD"}
            )
        missing_actions = set(copied.get("requiredActions", [])) - actions
        if missing_actions:
            raise ValueError(
                f"Configure target required actions first: {sorted(missing_actions)}"
            )
        users.append(copied)
    return users, skipped


def validate_snapshot(snapshot):
    if (
        not isinstance(snapshot, dict)
        or snapshot.get("formatVersion") != 1
        or snapshot.get("realm") != REALM
    ):
        raise ValueError("Expected a version 1 migration download for realm launchpad")
    if not isinstance(snapshot.get("sourceKeycloakUrl"), str) or not isinstance(
        snapshot.get("sourceAppId"), str
    ):
        raise ValueError("Download must identify its source App ID and Keycloak URL")
    validate_url(snapshot["sourceKeycloakUrl"])
    UUID(snapshot["sourceAppId"])
    if not isinstance(snapshot.get("users"), list) or not isinstance(
        snapshot.get("userProfile"), dict
    ):
        raise ValueError("Download must contain users and a userProfile schema")
    if not isinstance(snapshot.get("roles"), dict) or not isinstance(
        snapshot.get("groups"), list
    ):
        raise ValueError("Download must contain role definitions and group trees")
    seen = set()
    allowed = set(USER_FIELDS) | {"realmRoles", "clientRoles", "groups", "_migration"}
    for user in snapshot["users"]:
        if not isinstance(user, dict) or set(user) - allowed:
            raise ValueError(
                "Unexpected user fields in download; credentials and IDs are not accepted"
            )
        name = user.get("username")
        if not isinstance(name, str) or not name or name.casefold() in seen:
            raise ValueError(
                "Each downloaded user must have a unique, nonempty username"
            )
        seen.add(name.casefold())
        if any(
            key in user and not isinstance(user[key], str)
            for key in ("email", "firstName", "lastName")
        ):
            raise ValueError(f"Invalid profile strings for {name}")
        if any(
            key in user and not isinstance(user[key], bool)
            for key in ("enabled", "emailVerified")
        ):
            raise ValueError(f"Invalid account flags for {name}")
        attributes = user.get("attributes", {})
        if not isinstance(attributes, dict) or any(
            not isinstance(values, list)
            or any(not isinstance(value, str) for value in values)
            for values in attributes.values()
        ):
            raise ValueError(f"Invalid multivalued attributes for {name}")
        links = user.get("federatedIdentities", [])
        if not isinstance(links, list) or any(
            not isinstance(link, dict)
            or any(
                not isinstance(link.get(key), str)
                for key in ("identityProvider", "userId", "userName")
            )
            for link in links
        ):
            raise ValueError(f"Invalid identity-provider links for {name}")
        metadata = user.get("_migration")
        if not isinstance(metadata, dict) or any(
            not isinstance(metadata.get(key), bool)
            for key in ("externalStorage", "serviceAccount", "hasConsents")
        ):
            raise ValueError(f"Missing migration metadata for {name}")
        mappings = user.get("clientRoles")
        if not isinstance(mappings, dict):
            raise ValueError(f"Missing client-role mappings for {name}")
        lists = [
            user.get("realmRoles"),
            user.get("groups"),
            metadata.get("credentialTypes"),
            user.get("requiredActions", []),
            *mappings.values(),
        ]
        if any(
            not isinstance(items, list)
            or any(not isinstance(item, str) for item in items)
            for items in lists
        ):
            raise ValueError(
                f"Invalid role, group, or credential-type lists for {name}"
            )


def write_passwords(path, users):
    # Exclusive creation prevents overwriting a previous migration's only password copy.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(["username", "email", "password"])
        writer.writerows(
            [user["username"], user.get("email", ""), user["credentials"][0]["value"]]
            for user in users
        )
        output.flush()
        os.fsync(output.fileno())


def verify(target, users):
    for expected in users:
        matches = target.call("users", username=expected["username"], exact="true")
        if len(matches) != 1:
            raise RuntimeError(
                f"Could not verify imported user: {expected['username']}"
            )
        path = f"users/{quote(matches[0]['id'], safe='')}"
        actual = target.call(path)
        for field in USER_FIELDS:
            if field in expected and canonical(expected[field]) != canonical(
                actual.get(field)
            ):
                raise RuntimeError(
                    f"Verification failed for {expected['username']}: {field}"
                )
        mappings = role_mappings(target, path)
        if not set(expected["realmRoles"]) <= set(mappings["realmRoles"]):
            raise RuntimeError(
                f"Realm-role verification failed: {expected['username']}"
            )
        for client, roles in expected["clientRoles"].items():
            if not set(roles) <= set(mappings["clientRoles"].get(client, [])):
                raise RuntimeError(
                    f"Client-role verification failed: {expected['username']} / {client}"
                )
        groups = {group["path"] for group in target.pages(f"{path}/groups")}
        if not set(expected["groups"]) <= groups:
            raise RuntimeError(f"Group verification failed: {expected['username']}")


async def resolve_app(app_id, url_override=None):
    import apolo_sdk

    async with apolo_sdk.get() as client:
        app = await client.apps.get(str(app_id))
        context = {
            "cluster_name": app.cluster_name,
            "org_name": app.org_name,
            "project_name": app.project_name,
        }
        print(
            f"Apolo user {client.config.username}; App {app.id}; context {app.cluster_name}/{app.org_name}/{app.project_name}"
        )
        outputs = await client.apps.get_output(app.id, **context)
        config = outputs.get("keycloak_config")
        if not isinstance(config, dict):
            raise ValueError(f"App {app.id} has no Launchpad Keycloak outputs")
        reference = config.get("auth_admin_password")
        if (
            not isinstance(reference, dict)
            or not isinstance(reference.get("key"), str)
            or not reference["key"]
        ):
            raise ValueError(
                f"App {app.id} has no Keycloak administrator password reference"
            )
        url = url_override
        if not url:
            service = config.get("web_app_url") or {}
            endpoint = service.get("external_url")
            if not isinstance(endpoint, dict):
                raise ValueError(
                    "App has no external Keycloak URL; supply a --source-keycloak-url or --target-keycloak-url port-forward"
                )
            protocol, host = endpoint.get("protocol"), endpoint.get("host")
            if not isinstance(protocol, str) or not isinstance(host, str):
                raise ValueError("App Keycloak endpoint is malformed")
            if ":" in host and not host.startswith("["):
                host = f"[{host}]"
            port = endpoint.get("port")
            # Apolo's ingress helper reports 80 even for HTTPS public endpoints.
            if protocol == "https" and port is not None and int(port) == 80:
                port = None
            authority = f"{host}:{int(port)}" if port is not None else host
            url = f"{protocol}://{authority}/{(endpoint.get('base_path') or '').lstrip('/')}"
        validate_url(url)
        try:
            admin_password = (
                await client.secrets.get(reference["key"], **context)
            ).decode()
        except Exception:
            raise RuntimeError(
                f"Could not read Keycloak administrator secret for App {app.id}"
            ) from None
        # The Launchpad chart configures the Keycloak server administrator as admin.
        return Keycloak(url, "admin", admin_password, "master")


def connect(args, side):
    return asyncio.run(
        resolve_app(
            getattr(args, f"{side}_app_id"), getattr(args, f"{side}_keycloak_url")
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    download = commands.add_parser(
        "download", help="Save source users and metadata for manual review"
    )
    upload = commands.add_parser(
        "upload", help="Import a reviewed download into the target"
    )
    for command, side in ((download, "source"), (upload, "target")):
        command.add_argument(
            f"--{side}-app-id",
            required=True,
            type=UUID,
            help=f"{side.capitalize()} Launchpad Apolo App UUID",
        )
        command.add_argument(
            f"--{side}-keycloak-url",
            help="Override discovery, e.g. for a localhost port-forward",
        )
    download.add_argument(
        "--output", default="launchpad-users.json", help="New JSON file to review"
    )
    upload.add_argument(
        "--input", required=True, help="Reviewed JSON produced by download"
    )
    upload.add_argument("--passwords-csv", default="launchpad-passwords.csv")
    upload.add_argument("--existing-users", choices=("skip", "fail"), default="skip")
    upload.add_argument(
        "--temporary-passwords",
        action=argparse.BooleanOptionalAction,
        help="Require a password change on browser login (blocks direct-grant login until changed)",
        default=False,
    )
    upload.add_argument(
        "--dry-run",
        action="store_true",
        help="Only check target compatibility; do not import or write passwords",
    )
    args = parser.parse_args()
    if args.command == "download":
        source = connect(args, "source")
        exported = source.export()
        snapshot = {
            "formatVersion": 1,
            "realm": REALM,
            "sourceKeycloakUrl": source.url,
            "sourceAppId": str(args.source_app_id),
            "organizationsEnabled": exported.get("organizationsEnabled", False),
            "roles": clean(exported.get("roles", {})),
            "groups": clean(exported.get("groups", [])),
            "defaultRole": clean(exported.get("defaultRole")),
            "defaultGroups": exported.get("defaultGroups"),
            "userProfile": source.call("users/profile"),
            "users": collect_users(source),
        }
        validate_snapshot(snapshot)
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(snapshot, output, indent=2, ensure_ascii=False)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        print(
            f"Downloaded {len(snapshot['users'])} users to {args.output} (mode 0600). Review before upload."
        )
        return
    with open(args.input, encoding="utf-8") as input_file:
        source_export = json.load(input_file)
    validate_snapshot(source_export)
    if UUID(source_export["sourceAppId"]) == args.target_app_id:
        raise ValueError("Source and target App IDs must differ")
    target = connect(args, "target")
    if source_export["sourceKeycloakUrl"].rstrip("/") == target.url:
        raise ValueError("Source and target Keycloak URLs must differ")
    target_export = target.export()
    if source_export.get("organizationsEnabled"):
        raise ValueError("Organization memberships require a separate migration")
    compatible_resources(source_export, target_export)
    if canonical(source_export["userProfile"]) != canonical(
        target.call("users/profile")
    ):
        raise ValueError(
            "Target user-profile schema differs; align it to preserve custom attributes"
        )
    users, skipped = prepare_users(
        source_export["users"], target, args.existing_users, args.temporary_passwords
    )
    print(
        f"Realm {REALM}: {len(users)} users to copy; {len(skipped)} existing users skipped"
    )
    for username in skipped:
        print(f"Skipped existing user: {username}")
    if args.dry_run:
        print("Preflight passed. No users imported or password CSV written.")
        return
    # ponytail: one in-memory import; batch imports if realm size becomes a problem.
    payload = {
        "ifResourceExists": "SKIP",
        "users": users,
        "roles": clean(source_export.get("roles", {})),
        "groups": clean(source_export.get("groups", [])),
    }
    write_passwords(args.passwords_csv, users)
    print(f"Generated passwords saved to {args.passwords_csv} (mode 0600)")
    result = target.call("partialImport", "POST", payload)
    # A concurrent user creation must not silently make CSV passwords inaccurate.
    if any(
        item.get("resourceType") == "USER" and item.get("action") != "ADDED"
        for item in result.get("results", [])
    ):
        raise RuntimeError(
            "Some users were skipped during import; CSV credentials for them are not active"
        )
    verify(target, users)
    compatible_resources(source_export, target.export(), require_presence=True)
    print(
        f"Imported and verified {len(users)} users. Existing target users were retained."
    )


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError) as exc:
        print(
            f"Migration failed: {exc}. Keep any generated CSV; no rollback was attempted.",
            file=sys.stderr,
        )
        sys.exit(1)
