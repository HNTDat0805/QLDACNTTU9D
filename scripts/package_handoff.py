"""Build a source-only ZIP from reviewed Git files, never from a recursive glob."""

import argparse
import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
EXTRA_FILES = (
    "scripts/check_demo_readiness.py",
    "scripts/package_handoff.py",
    "docs/hung-demo-readiness.md",
    "backend/tests/api/routes/test_demo_readiness.py",
    "frontend/tests/demo-readiness.spec.ts",
)
EXCLUDED_DIRS = {
    ".git",
    ".agents",
    ".codex",
    ".aws",
    ".vscode",
    ".idea",
    ".tanstack",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".cache",
    ".auth",
    "test-results",
    "playwright-report",
    "blob-report",
    "coverage",
    "htmlcov",
    "artifacts",
    "dist",
    "logs",
    "tmp",
    "temp",
}
EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".log",
    ".tmp",
    ".temp",
    ".bak",
    ".zip",
    ".7z",
    ".tar",
    ".gz",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".sql",
    ".dump",
    ".pem",
    ".key",
    ".crt",
    ".cert",
    ".p12",
    ".pfx",
    ".tsbuildinfo",
}
SECRET_PATTERNS = (
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{10,}"),
    re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
)


def git(*args: str) -> bytes:
    return subprocess.check_output(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", *args],
        cwd=ROOT,
    )


def excluded(name: str) -> bool:
    path = PurePosixPath(name)
    lower = [part.lower() for part in path.parts]
    return (
        path.is_absolute()
        or ".." in path.parts
        or "\\" in name
        or bool(set(lower) & EXCLUDED_DIRS)
        or path.name.lower().startswith(".env")
        or path.name.lower() in {"credentials", "id_rsa", "id_ed25519", ".coverage"}
        or path.suffix.lower() in EXCLUDED_SUFFIXES
        or name.startswith("backend/app/frontend/")
    )


def verify(archive_path: Path) -> int:
    with ZipFile(archive_path) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("Archive CRC verification failed")
        manifest = json.loads(archive.read("FixCare/HANDOFF-MANIFEST.json"))
        expected = {"FixCare/HANDOFF-MANIFEST.json"}
        for item in manifest["files"]:
            name = item["path"]
            if excluded(name):
                raise RuntimeError("Excluded path found in archive")
            entry = f"FixCare/{name}"
            expected.add(entry)
            data = archive.read(entry)
            if hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise RuntimeError("Archive file digest mismatch")
            if any(pattern.search(data) for pattern in SECRET_PATTERNS):
                raise RuntimeError("Sensitive pattern detected in archive")
        if set(archive.namelist()) != expected or len(archive.namelist()) != len(
            expected
        ):
            raise RuntimeError("Unexpected or duplicate archive entry")
    print(
        json.dumps(
            {
                "zip_integrity": "PASS",
                "file_count": len(manifest["files"]),
                "excluded_paths": 0,
                "sensitive_pattern_matches": 0,
            }
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify:
        return verify(args.verify.resolve())
    candidates = set(git("ls-files", "-z").decode("utf-8").strip("\0").split("\0"))
    candidates.update(EXTRA_FILES)
    payloads: list[tuple[str, bytes]] = []
    for name in sorted(candidates):
        if excluded(name):
            continue
        source = ROOT / name
        if not source.is_file():
            raise RuntimeError("A selected source file is missing")
        if source.is_symlink() or not source.resolve().is_relative_to(ROOT):
            raise RuntimeError("Symlink or path outside workspace rejected")
        data = source.read_bytes()
        if any(pattern.search(data) for pattern in SECRET_PATTERNS):
            raise RuntimeError(f"Sensitive pattern detected; packaging stopped: {name}")
        payloads.append((name, data))
    manifest = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "source_commit": git("rev-parse", "HEAD").decode().strip(),
        "snapshot": "Working tree: includes uncommitted demo fixes and documents",
        "kind": "source-only; no environment configuration or database data",
        "files": [
            {"path": name, "sha256": hashlib.sha256(data).hexdigest()}
            for name, data in payloads
        ],
    }
    output_dir = ROOT / "artifacts"
    output_dir.mkdir(exist_ok=True)
    output = output_dir / f"FixCare-handoff-{datetime.now(UTC):%Y%m%d-%H%M%S-%f}.zip"
    with ZipFile(output, "x", compression=ZIP_DEFLATED) as archive:
        for name, data in payloads:
            archive.writestr(f"FixCare/{name}", data)
        archive.writestr(
            "FixCare/HANDOFF-MANIFEST.json",
            json.dumps(manifest, ensure_ascii=False, indent=2),
        )
    verify(output)
    print(
        json.dumps(
            {
                "zip": str(output.relative_to(ROOT)),
                "bytes": output.stat().st_size,
                "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
