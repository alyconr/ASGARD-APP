"""Unit tests for repository guardrail preflight script."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from assert_asgard_context import (  # noqa: E402
    check_branch_allowed,
    is_valid_remote,
    normalize_remote,
    verify_asgard_context,
)


def test_normalize_remote() -> None:
    """Test remote URL normalization."""
    assert normalize_remote("https://github.com/alyconr/ASGARD-APP.git") == "https://github.com/alyconr/asgard-app"
    assert normalize_remote("git@github.com:alyconr/ASGARD-APP.git ") == "git@github.com:alyconr/asgard-app"


def test_is_valid_remote_accepts_asgard() -> None:
    """Valid ASGARD-APP remote URLs are accepted."""
    assert is_valid_remote("https://github.com/alyconr/ASGARD-APP.git")
    assert is_valid_remote("git@github.com:alyconr/ASGARD-APP.git")
    assert is_valid_remote("https://github.com/alyconr/asgard-app")
    assert is_valid_remote("git@github.com:alyconr/asgard-app")


def test_is_valid_remote_rejects_foreign_repos() -> None:
    """Foreign repository remotes must be rejected explicitly."""
    assert not is_valid_remote("https://github.com/someone/schedule-stack.git")
    assert not is_valid_remote("https://github.com/someone/horarios-app.git")
    assert not is_valid_remote("https://github.com/someone/SCHEDULE.git")
    assert not is_valid_remote("https://github.com/alyconr/other-repo.git")


def test_branch_validation_develop() -> None:
    """Branch 'develop' is allowed."""
    allowed, err = check_branch_allowed("develop")
    assert allowed
    assert err is None


def test_branch_validation_feature_branches() -> None:
    """Branches starting with feature/, fix/, chore/, test/, docs/ are allowed."""
    for prefix in ("feature/login-fix", "fix/security-cookie", "chore/guardrails", "test/concurrency", "docs/branch"):
        allowed, err = check_branch_allowed(prefix)
        assert allowed
        assert err is None


def test_branch_validation_main_rejected_by_default() -> None:
    """Branch 'main' or 'master' must be rejected for automated agents without explicit bypass."""
    allowed_main, err_main = check_branch_allowed("main", allow_main=False)
    assert not allowed_main
    assert err_main is not None
    assert "Modificaciones automáticas no permitidas en rama 'main'" in err_main

    allowed_master, err_master = check_branch_allowed("master", allow_main=False)
    assert not allowed_master
    assert "Modificaciones automáticas no permitidas en rama 'master'" in err_master


def test_branch_validation_main_allowed_with_explicit_flag() -> None:
    """Branch 'main' can be allowed when allow_main=True (human administrative intervention)."""
    allowed, err = check_branch_allowed("main", allow_main=True)
    assert allowed
    assert err is None


def test_branch_validation_unknown_branch_rejected() -> None:
    """Arbitrary branch names outside allowed prefixes are rejected."""
    allowed, err = check_branch_allowed("release-2026")
    assert not allowed
    assert "no cumple con el patrón permitido" in (err or "")


def test_verify_asgard_context_real_repo() -> None:
    """Verify context in current working repository succeeds."""
    result = verify_asgard_context(start_dir=REPO_ROOT, allow_main=False)
    assert result["ok"]
    assert result["repository"] == "ASGARD-APP"
    assert result["checks"]["git"]
    assert result["checks"]["remote"]
    assert result["checks"]["sentinels"]
    assert result["checks"]["branch"]
    assert len(result["errors"]) == 0


def test_verify_asgard_context_non_git_directory(tmp_path: Path) -> None:
    """Non-git directory fails with descriptive error."""
    result = verify_asgard_context(start_dir=tmp_path)
    assert not result["ok"]
    assert not result["checks"]["git"]
    assert any("no forma parte de un repositorio Git" in err for err in result["errors"])


def test_verify_asgard_context_missing_sentinels() -> None:
    """Failing sentinels check when files are missing."""
    with patch("assert_asgard_context.REQUIRED_SENTINELS", ("non_existent_sentinel_file_12345.xyz",)):
        result = verify_asgard_context(start_dir=REPO_ROOT)
        assert not result["ok"]
        assert not result["checks"]["sentinels"]
        assert any("Faltan archivos centinela" in err for err in result["errors"])


def test_verify_asgard_context_invalid_remote() -> None:
    """Failing remote origin check when origin is not ASGARD."""
    with patch("assert_asgard_context.run_git_command") as mock_git:
        def side_effect(args: list[str], cwd: Path | None = None) -> tuple[int, str]:
            if "rev-parse" in args:
                return 0, str(REPO_ROOT)
            if "remote" in args:
                return 0, "https://github.com/fake/schedule-stack.git"
            if "branch" in args:
                return 0, "develop"
            return 1, ""

        mock_git.side_effect = side_effect
        result = verify_asgard_context(start_dir=REPO_ROOT)
        assert not result["ok"]
        assert not result["checks"]["remote"]
        assert any("no corresponde a ASGARD-APP" in err for err in result["errors"])
