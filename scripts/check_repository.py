"""Check publishable Git inputs, including currently untracked non-ignored source.

Reports only filenames, line numbers and rule names, never matched credential values.
This high-confidence check supplements account secret scanning and human review.
"""

import os
import re
import subprocess
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = {
    ".cache",
    ".tools",
    ".venv",
    ".vercel",
    ".playwright-cli",
    ".aws",
    ".agents",
    ".codex",
    "node_modules",
    "__pycache__",
    "output",
    "coverage",
    ".pytest_cache",
    ".ruff_cache",
}
PATTERNS = {
    "private key": re.compile(r"-----BEGIN " + r"(?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(
        r"(?:gh[pousr]_" + r"[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})"
    ),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)" + r"[A-Z0-9]{16}\b"),
    "API secret": re.compile(r"\bsk-(?:proj-|svcacct-)?" + r"[A-Za-z0-9_-]{40,}\b"),
}
URL = re.compile(r"(?:postgres(?:ql)?(?:\+psycopg)?|https?)://[^\s:/]+:([^\s@]+)@")
ALLOWED_PASSWORDS = {"winddesk_local", "password", "PASSWORD", "pass", "p", "secret", "x"}


def main():
    git = os.environ.get("GRID_GIT_EXECUTABLE", "git")
    raw = subprocess.check_output(
        [git, "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT
    )
    files = sorted(set(raw.decode().split("\0")) - {""})
    failures = []
    for name in files:
        parts = PurePosixPath(name).parts
        path = ROOT / name
        if (
            any(part in FORBIDDEN for part in parts)
            or (path.name.startswith(".env") and path.name != ".env.example")
            or path.suffix.lower() in {".docx", ".pem", ".key", ".log"}
        ):
            failures.append(f"{name}: forbidden publication input")
            continue
        if path.is_symlink():
            failures.append(f"{name}: review symlink before publication")
            continue
        if not path.is_file():
            continue
        data = path.read_bytes()
        if b"\0" in data[:8192]:
            continue
        try:
            lines = data.decode("utf-8-sig").splitlines()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(lines, 1):
            for label, pattern in PATTERNS.items():
                if pattern.search(line):
                    failures.append(f"{name}:{number}: {label}")
            for match in URL.finditer(line):
                value = match.group(1)
                if value not in ALLOWED_PASSWORDS and not any(
                    marker in value for marker in ("${", "<", "example", "replace", "test", "%")
                ):
                    failures.append(f"{name}:{number}: credential in connection URL")
    if failures:
        raise SystemExit("Repository check failed:\n" + "\n".join(failures))
    print(
        f"Publication input check passed for {len(files)} source files "
        "(ignored local files excluded)."
    )


if __name__ == "__main__":
    main()
