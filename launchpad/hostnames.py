from urllib.parse import urlsplit


def canonical_hostname(authority: str) -> str:
    parsed = urlsplit(f"https://{authority}")
    hostname = (parsed.hostname or "").rstrip(".")
    if (
        not hostname
        or parsed.username is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
        or any(character.isspace() for character in authority)
    ):
        raise ValueError("Invalid hostname")
    # Reading the port validates its format and range.
    _ = parsed.port
    return hostname


def canonical_authority(authority: str) -> str:
    hostname = canonical_hostname(authority)
    if ":" in hostname:
        hostname = f"[{hostname}]"
    port = urlsplit(f"https://{authority}").port
    return f"{hostname}:{port}" if port not in (None, 443) else hostname
