"""Build and verify an isolated, disposable Compose project, including persistence.

Requires Docker's Linux engine and the frontend browser dependencies. Existing
Compose projects are refused. Only resources owned by this invocation are removed.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="winddesk-phase6")
    parser.add_argument("--output", type=Path, default=Path("output/containers"))
    args = parser.parse_args()
    if not re.fullmatch(r"winddesk-(?:phase6|ci)(?:-[a-z0-9-]+)?", args.project):
        parser.error("Use a dedicated winddesk-phase6 or winddesk-ci project name")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    environment = os.environ | {
        "GRID_HTTP_PORT": os.environ.get("GRID_HTTP_PORT", "18000"),
        "GRID_POSTGRES_PORT": os.environ.get("GRID_POSTGRES_PORT", "15432"),
        "GRID_IMAGE_TAG": args.project,
    }
    # Keep the test database independent of any operator .env credentials.
    environment |= {
        "POSTGRES_USER": "winddesk",
        "POSTGRES_PASSWORD": "winddesk_local",
        "POSTGRES_DB": "winddesk",
    }
    docker = os.environ.get("GRID_DOCKER_EXECUTABLE", "docker")
    compose = [
        docker,
        "compose",
        "--project-name",
        args.project,
        "--file",
        str(ROOT / "compose.yaml"),
    ]

    def run(command, *, capture=False, timeout=600, check=True):
        return subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            text=True,
            check=check,
            capture_output=capture,
            timeout=timeout,
        )

    assert (
        run([docker, "info", "--format", "{{.OSType}}"], capture=True, timeout=20).stdout.strip()
        == "linux"
    )
    project_label = "label=com.docker.compose.project=" + args.project
    for resource in (
        ["ps", "--all", "--filter", project_label, "--quiet"],
        ["volume", "ls", "--filter", project_label, "--quiet"],
        ["network", "ls", "--filter", project_label, "--quiet"],
    ):
        assert not run([docker, *resource], capture=True, timeout=20).stdout.strip(), (
            "Refusing an existing project's containers, volumes or networks; choose a fresh name"
        )
    try:
        run(compose + ["build", "--pull"], timeout=1200)
        run(compose + ["up", "--detach", "--wait", "--wait-timeout", "180", "web"], timeout=240)
        container = run(compose + ["ps", "--quiet", "web"], capture=True).stdout.strip()
        detail = json.loads(run([docker, "inspect", container], capture=True).stdout)[0]
        assert detail["Config"]["User"] == "app"
        assert detail["HostConfig"]["ReadonlyRootfs"] is True
        assert "ALL" in detail["HostConfig"]["CapDrop"]
        assert "no-new-privileges:true" in detail["HostConfig"]["SecurityOpt"]
        assert detail["Config"]["Labels"]["org.opencontainers.image.revision"] == environment.get(
            "GRID_BUILD_SHA", "local"
        )
        base = "http://127.0.0.1:" + environment["GRID_HTTP_PORT"]
        before = output / "before.json"
        after = output / "after.json"
        run(
            [
                sys.executable,
                "scripts/verify_service.py",
                "--base-url",
                base,
                "--output",
                str(before),
            ]
        )
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        assert npm, "npm is required for the real browser gate"
        browser_env = environment | {
            "GRID_BROWSER_BASE_URL": base,
            "GRID_BROWSER_OUTPUT": str(output / "browser"),
        }
        subprocess.run(
            [npm, "run", "test:browser", "--prefix", "frontend"],
            cwd=ROOT,
            env=browser_env,
            check=True,
            timeout=180,
        )
        run(compose + ["run", "--rm", "initialize"], timeout=180)
        run(compose + ["restart", "postgres", "web"], timeout=60)
        run(
            [
                sys.executable,
                "scripts/verify_service.py",
                "--base-url",
                base,
                "--output",
                str(after),
            ]
        )
        first, second = (json.loads(file.read_text()) for file in (before, after))
        assert first["stable_fingerprint"] == second["stable_fingerprint"]
        report = {
            "project": args.project,
            "release_id": first["release_id"],
            "build_sha": first["build_sha"],
            "image_id": detail["Image"],
            "non_root": True,
            "read_only_root": True,
            "capabilities_dropped": True,
            "seed_replay": "passed",
            "database_and_web_restart": "passed",
            "stable_fingerprint": first["stable_fingerprint"],
        }
        (output / "container-report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
    finally:
        logs = run(compose + ["logs", "--no-color"], capture=True, check=False, timeout=30)
        (output / "compose.log").write_text(logs.stdout + logs.stderr, encoding="utf-8")
        # The explicit project was checked empty before any resource creation.
        run(compose + ["down", "--volumes", "--remove-orphans"], timeout=60)


if __name__ == "__main__":
    main()
