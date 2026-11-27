from contextlib import closing
from pathlib import Path

import yaml
from testcontainers.core.container import DockerContainer
from testcontainers.core.docker_client import DockerClient
from testcontainers.core.wait_strategies import ExecWaitStrategy


CHART = Path(__file__).resolve().parents[2] / "charts/launchpad"
INIT_PATH = "/docker-entrypoint-initdb.d/init.sh"
APP_PSQL = 'PGPASSWORD="$LAUNCHPAD_DB_PASSWORD" psql -Xw -h 127.0.0.1 -U launchpad -d launchpad -Atqc'
KEYCLOAK_PSQL = 'PGPASSWORD="$KEYCLOAK_DB_PASSWORD" psql -Xw -h 127.0.0.1 -U keycloak'


def test_isolated_postgresql_retries_bootstrap_on_the_same_volume(
    tmp_path: Path,
) -> None:
    image = yaml.safe_load((CHART / "values.yaml").read_text())["isolatedDatabases"][
        "image"
    ]
    script = tmp_path / "init.sh"
    script.write_bytes((CHART / "files/init-postgresql.sh").read_bytes())
    script.chmod(0o555)

    with closing(DockerClient().client) as docker:
        volume = docker.volumes.create()
        try:

            def database(launchpad_password: str) -> DockerContainer:
                return (
                    DockerContainer(
                        image,
                        entrypoint=[INIT_PATH],
                        user="999:999",
                        cap_drop=["ALL"],
                        security_opt=["no-new-privileges"],
                    )
                    .with_command(["postgres"])
                    .with_envs(
                        PGDATA="/var/lib/postgresql/data/pgdata",
                        POSTGRES_INITDB_ARGS="--auth-local=peer --auth-host=scram-sha-256",
                        LAUNCHPAD_DB_PASSWORD=launchpad_password,
                        KEYCLOAK_DB_PASSWORD="keycloak-test-password",
                    )
                    .with_volume_mapping(volume.name, "/var/lib/postgresql/data", "rw")
                    .with_volume_mapping(script, INIT_PATH)
                )

            # Stop after initdb and Keycloak setup, before Launchpad setup.
            with database("") as failed:
                assert (
                    failed.get_wrapped_container().wait(timeout=40)["StatusCode"] != 0
                )
                _, stderr = failed.get_logs()
                assert b"Set LAUNCHPAD_DB_PASSWORD" in stderr

            ready = ExecWaitStrategy([INIT_PATH, "ready"])
            with database("launchpad-test-password").waiting_for(ready) as recovered:
                result = recovered.exec(
                    [
                        "sh",
                        "-ec",
                        f'{APP_PSQL} "CREATE TABLE recovered (id int); INSERT INTO recovered VALUES (42)"',
                    ]
                )
                assert result.exit_code == 0, result.output
                admin = recovered.exec(
                    [
                        "psql",
                        "-Xw",
                        "-U",
                        "postgres",
                        "-Atqc",
                        "SELECT rolpassword IS NULL FROM pg_authid WHERE rolname = 'postgres'",
                    ]
                )
                assert (admin.exit_code, admin.output.strip()) == (0, b"t")
                own_db = recovered.exec(
                    [
                        "sh",
                        "-ec",
                        f'{KEYCLOAK_PSQL} -d keycloak -Atqc "CREATE TABLE realm (id int); INSERT INTO realm VALUES (24)"',
                    ]
                )
                assert own_db.exit_code == 0, own_db.output
                for command in (
                    f'{KEYCLOAK_PSQL} -d launchpad -Atqc "SELECT 1"',
                    'PGPASSWORD="$LAUNCHPAD_DB_PASSWORD" psql -Xw -h 127.0.0.1 -U launchpad -d keycloak -Atqc "SELECT 1"',
                    f'{APP_PSQL} "SET ROLE keycloak"',
                ):
                    denied = recovered.exec(["sh", "-ec", command])
                    assert denied.exit_code != 0
                    assert b"permission denied" in denied.output

            with database("launchpad-test-password").waiting_for(ready) as restarted:
                result = restarted.exec(
                    ["sh", "-ec", f'{APP_PSQL} "SELECT id FROM recovered"']
                )
                assert (result.exit_code, result.output.strip()) == (0, b"42")
                result = restarted.exec(
                    [
                        "sh",
                        "-ec",
                        f'{KEYCLOAK_PSQL} -d keycloak -Atqc "SELECT id FROM realm"',
                    ]
                )
                assert (result.exit_code, result.output.strip()) == (0, b"24")
        finally:
            volume.remove()
