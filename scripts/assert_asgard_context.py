#!/usr/bin/env python3
"""Preflight guardrail script to assert execution context inside ASGARD-APP repository.

This script ensures agents, CI jobs, and developers do not accidentally execute
modifications on the wrong repository, from an unapproved branch (such as 'main' for agents),
or without the required sentinel project structure.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

FORBIDDEN_IDENTIFIERS = ("schedule-stack", "horarios-app", "schedule")
ALLOWED_BRANCH_PREFIXES = ("develop", "feature/", "fix/", "chore/", "test/", "docs/")
REQUIRED_SENTINELS = (
    "AGENTS.md",
    "backend",
    "frontend",
    "package.json",
    "backend/src/infrastructure/db/models/planeacion.py",
    "frontend/src/features/programa",
    "frontend/src/features/proyecto",
)


def run_git_command(args: list[str], cwd: Path | None = None) -> tuple[int, str]:
    """Execute a git command and return (exit_code, output_stripped)."""
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.returncode, proc.stdout.strip()
    except Exception as exc:
        return 1, str(exc)


def normalize_remote(remote_url: str) -> str:
    """Normalize git remote URL for comparison."""
    url = remote_url.strip()
    if url.endswith(".git"):
        url = url[:-4]
    return url.lower()


def is_valid_remote(remote_url: str) -> bool:
    """Check if the remote URL corresponds to ASGARD-APP."""
    normalized = normalize_remote(remote_url)
    if any(forbidden in normalized for forbidden in FORBIDDEN_IDENTIFIERS):
        return False
    # Matches formats like:
    # https://github.com/alyconr/ASGARD-APP
    # git@github.com:alyconr/ASGARD-APP
    # /path/to/ASGARD-APP
    return "alyconr/asgard-app" in normalized or normalized.endswith("/asgard-app") or normalized == "asgard-app"


def check_branch_allowed(branch_name: str, allow_main: bool = False) -> tuple[bool, str | None]:
    """Verify if the current branch is allowed for automated agent modifications."""
    if not branch_name:
        return False, "No se pudo determinar la rama actual (detached HEAD o no Git)."

    if branch_name.lower() in ("main", "master"):
        if allow_main:
            return True, None
        return (
            False,
            f"Modificaciones automáticas no permitidas en rama '{branch_name}'. "
            "Use 'develop' o una rama de trabajo ('feature/*', 'fix/*', 'chore/*', etc.), "
            "o especifique --allow-main para una operación humana.",
        )

    for prefix in ALLOWED_BRANCH_PREFIXES:
        if branch_name.startswith(prefix):
            return True, None

    return (
        False,
        f"Rama '{branch_name}' no cumple con el patrón permitido: develop, feature/*, fix/*, chore/*, test/*, docs/*.",
    )


def verify_asgard_context(
    start_dir: Path | None = None,
    allow_main: bool = False,
) -> dict[str, Any]:
    """Perform comprehensive validation of repository context."""
    results: dict[str, Any] = {
        "ok": False,
        "repository": None,
        "remote": None,
        "branch": None,
        "root": None,
        "checks": {
            "git": False,
            "remote": False,
            "sentinels": False,
            "branch": False,
        },
        "errors": [],
    }

    cwd = start_dir or Path.cwd()

    # 1. Resolve git repo root
    ret, toplevel = run_git_command(["rev-parse", "--show-toplevel"], cwd=cwd)
    if ret != 0 or not toplevel:
        results["errors"].append("El directorio actual no forma parte de un repositorio Git válido.")
        return results

    repo_root = Path(toplevel).resolve()
    results["root"] = str(repo_root)
    results["checks"]["git"] = True

    # 2. Check remote origin
    ret_remote, remote_url = run_git_command(["remote", "get-url", "origin"], cwd=repo_root)
    if ret_remote != 0 or not remote_url:
        results["errors"].append("No se pudo obtener el remote origin del repositorio.")
    else:
        results["remote"] = remote_url
        if is_valid_remote(remote_url):
            results["checks"]["remote"] = True
            results["repository"] = "ASGARD-APP"
        else:
            results["errors"].append(
                f"El remote '{remote_url}' no corresponde a ASGARD-APP (alyconr/ASGARD-APP)."
            )

    # 3. Check sentinels
    missing_sentinels: list[str] = []
    for sentinel in REQUIRED_SENTINELS:
        target_path = repo_root / sentinel
        if not target_path.exists():
            missing_sentinels.append(sentinel)

    if missing_sentinels:
        results["errors"].append(
            f"Faltan archivos centinela del proyecto ASGARD: {', '.join(missing_sentinels)}"
        )
    else:
        results["checks"]["sentinels"] = True

    # 4. Check branch
    ret_branch, branch_name = run_git_command(["branch", "--show-current"], cwd=repo_root)
    if ret_branch == 0 and branch_name:
        results["branch"] = branch_name
    else:
        # Fallback to CI environment variables if available
        branch_name = os.getenv("GITHUB_REF_NAME") or os.getenv("CI_COMMIT_REF_NAME") or ""
        results["branch"] = branch_name

    allowed, branch_err = check_branch_allowed(branch_name, allow_main=allow_main)
    if allowed:
        results["checks"]["branch"] = True
    else:
        if branch_err:
            results["errors"].append(branch_err)

    all_checks_passed = (
        results["checks"]["git"]
        and results["checks"]["remote"]
        and results["checks"]["sentinels"]
        and results["checks"]["branch"]
    )
    results["ok"] = all_checks_passed
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Validar contexto de repositorio ASGARD-APP")
    parser.add_argument("--json", action="store_true", help="Salida en formato JSON")
    parser.add_argument(
        "--allow-main",
        action="store_true",
        default=os.getenv("ALLOW_MAIN", "0") in ("1", "true", "True"),
        help="Permitir ejecución sobre rama main",
    )
    args = parser.parse_args()

    data = verify_asgard_context(allow_main=args.allow_main)

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        if data["ok"]:
            print("ASGARD context OK")
            print(f"  Root:   {data['root']}")
            print(f"  Remote: {data['remote']}")
            print(f"  Branch: {data['branch']}")
        else:
            print("ERROR: Este agente no está ejecutándose dentro de ASGARD-APP.")
            print("No se realizarán modificaciones.")
            for err in data["errors"]:
                print(f"  - {err}")

    return 0 if data["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
