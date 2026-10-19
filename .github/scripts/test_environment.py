"""Verify environment setup without writing GitHub settings."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


MAKEFILE = Path(__file__).resolve().parents[2] / "Makefile"


class EnvironmentSetupTests(unittest.TestCase):
    def test_setup_imports_only_complete_nonsecret_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            configuration = root / ".github/environments/production.env"
            configuration.parent.mkdir(parents=True)
            executable = root / "gh"
            executable.write_text(
                '#!/bin/sh\nprintf "%s\\n" "$@" > "$SETUP_ARGUMENTS"\n'
            )
            executable.chmod(0o700)
            arguments = root / "arguments.txt"
            for content, complete in (
                (
                    "ARGOCD_SERVER=\nDEV_LAUNCHPAD_ARGO_APPLICATION=dev-launchpad\n",
                    False,
                ),
                (
                    "ARGOCD_SERVER=https://argo.example.invalid\nDEV_LAUNCHPAD_ARGO_APPLICATION=\n",
                    False,
                ),
                ("ARGOCD_SERVER=https://argo.example.invalid\n", False),
                ("DEV_LAUNCHPAD_ARGO_APPLICATION=dev-launchpad\n", False),
                ("# No configured values.\n", False),
                (
                    "ARGOCD_SERVER=https://argo.example.invalid\nDEV_LAUNCHPAD_ARGO_APPLICATION=dev-launchpad\n",
                    True,
                ),
            ):
                with self.subTest(content=content):
                    arguments.unlink(missing_ok=True)
                    configuration.write_text(content)
                    result = subprocess.run(
                        ["make", "-f", str(MAKEFILE), "setup-production-environment"],
                        cwd=root,
                        env={
                            **os.environ,
                            "PATH": str(root) + os.pathsep + os.environ["PATH"],
                            "SETUP_ARGUMENTS": str(arguments),
                            "ARGOCD_SERVER": "https://inherited.example.invalid",
                            "DEV_LAUNCHPAD_ARGO_APPLICATION": "inherited-app",
                        },
                        capture_output=True,
                        text=True,
                        timeout=10,
                        check=False,
                    )
                    if complete:
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(
                            arguments.read_text().splitlines(),
                            [
                                "variable",
                                "set",
                                "--repo",
                                "neuro-inc/launchpad",
                                "--env",
                                "production",
                                "--env-file",
                                ".github/environments/production.env",
                            ],
                        )
                    else:
                        self.assertNotEqual(result.returncode, 0)
                        self.assertFalse(arguments.exists())


if __name__ == "__main__":
    unittest.main()
