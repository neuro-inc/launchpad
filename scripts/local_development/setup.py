"""Create the frontend environment file without replacing existing settings."""

import os
import secrets
from pathlib import Path


def setup_frontend(path: Path) -> bool:
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    with os.fdopen(descriptor, "w") as stream:
        stream.write(
            "NEXT_PUBLIC_ENVIRONMENT=local\n"
            "NEXT_PUBLIC_SITE_URL=http://dev.localhost:8080\n"
            "NEXTAUTH_URL=http://dev.localhost:13000\n"
            f"NEXTAUTH_SECRET={secrets.token_hex(32)}\n"
        )
    return True


def main() -> None:
    path = Path(__file__).resolve().parents[2] / "frontend" / ".env.local"
    if setup_frontend(path):
        print("Created frontend/.env.local with local development settings.")
    else:
        print("Preserved existing frontend/.env.local settings.")


if __name__ == "__main__":
    main()
