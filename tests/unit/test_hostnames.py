import pytest

from launchpad.hostnames import canonical_authority, canonical_hostname


@pytest.mark.parametrize(
    "value,hostname,authority",
    [
        (
            "SILVERFIN.APPS.APOLO.US.",
            "silverfin.apps.apolo.us",
            "silverfin.apps.apolo.us",
        ),
        ("EXTERNAL.EXAMPLE.:443", "external.example", "external.example"),
        ("EXTERNAL.EXAMPLE.:8443", "external.example", "external.example:8443"),
        ("[::1]:8443", "::1", "[::1]:8443"),
    ],
)
def test_hostname_normalization(value: str, hostname: str, authority: str) -> None:
    assert canonical_hostname(value) == hostname
    assert canonical_authority(value) == authority


@pytest.mark.parametrize(
    "value",
    [
        "",
        ".",
        "user@host",
        "host/path",
        "host?query",
        "host#fragment",
        "host:bad",
        "host:99999",
        "host name",
        "[invalid",
    ],
)
def test_invalid_hostname_is_rejected(value: str) -> None:
    with pytest.raises(ValueError):
        canonical_hostname(value)
    with pytest.raises(ValueError):
        canonical_authority(value)
