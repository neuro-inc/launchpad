import pytest

from launchpad.config import EnvironConfigFactory


def test_environ_factory_create_missing_vars_raises() -> None:
    factory = EnvironConfigFactory(environ={})

    with pytest.raises(KeyError):
        factory.create()
