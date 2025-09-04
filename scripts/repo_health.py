#!/usr/bin/env python3
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

ALLOW_TOP = {
    "services",
    "apps",
    "packages",
    "monitoring",
    "scripts",
    "data",
    "config",
    "docs",
    ".github",
    "models",
    "runbooks",
    "test-results",
    "ops",
    "logs",
    "LICENSE",
    "README.md",
    "ROADMAP.md",
    "AGENTS.md",
    "SECURITY.md",
    "pnpm-lock.yaml",
    "pnpm-workspace.yaml",
    "turbo.json",
    "docker-compose.yml",
    "docker-compose.override.yml" "GITHUB_SETUP.md",
    "CONTRIBUTING.md",
    "docs",
}
BLOCK_DIRS = {"node_modules", "__pycache__", "dist", "build"}
MAX_FILES_PR = int(os.getenv("MAX_FILES_PR", "200"))


def list_top():
    names = set()
    for p in ROOT.iterdir():
        if p.name.startswith(".") and p.name != ".github":
            continue
        names.add(p.name)
    return names


def is_tracked(path: pathlib.Path) -> bool:
    try:
        subprocess.check_output(
            ["git", "ls-files", "--error-unmatch", str(path)], cwd=str(ROOT)
        )
        return True
    except subprocess.CalledProcessError:
        return False
    except Exception:
        return False


def scan_block_dirs():
    bad = []
    for d in BLOCK_DIRS:
        p = ROOT / d
        if p.exists() and is_tracked(p):
            bad.append(str(p))
    return bad


def count_files():
    n = 0
    for dirpath, _, files in os.walk(ROOT):
        # skip blocked dirs entirely for count
        parts = pathlib.Path(dirpath).parts
        if any(part in BLOCK_DIRS for part in parts):
            continue
        n += len(files)
    return n


def main():
    top = list_top()
    unknown = sorted(
        [
            x
            for x in top
            if x not in ALLOW_TOP
            and not x.endswith(
                (
                    ".md",
                    ".yml",
                    ".yaml",
                    ".json",
                    ".toml",
                    ".lock",
                    ".txt",
                    ".gitignore",
                    ".editorconfig",
                )
            )
        ]
    )
    blocked = scan_block_dirs()
    files_total = count_files()
    report = {
        "unknown_top": unknown,
        "blocked_dirs": blocked,
        "files_total": files_total,
    }
    print(json.dumps(report, indent=2))
    if unknown or blocked:
        print("Repo structure issues detected", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
