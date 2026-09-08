"""Regression tests for WSL firewall rule scoping.

Covers GHSA-v558-4774-r6wq: the CDP bridge listens on 0.0.0.0, so the Windows
Firewall rule is the only boundary in front of an unauthenticated protocol. It
must be scoped to the WSL virtual adapter, because that adapter usually lands
on the Public network profile and profile filtering cannot separate it from a
real network. The privilege-failure fallback previously printed a command with
no -RemoteAddress at all, which defaults to Any.
"""

import subprocess
from unittest.mock import Mock

import pytest

from notebooklm_tools.utils import wsl


def _run_result(returncode: int, stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], returncode=returncode, stdout="", stderr=stderr)


@pytest.fixture
def _wsl_env(monkeypatch):
    monkeypatch.setattr(wsl, "is_wsl", lambda: True)
    monkeypatch.setattr(wsl, "_get_powershell_path", lambda: "/mnt/c/powershell.exe")


def test_created_rule_is_scoped_to_the_wsl_adapter(_wsl_env, monkeypatch):
    run = Mock(return_value=_run_result(0))
    monkeypatch.setattr(wsl.subprocess, "run", run)

    ok, _ = wsl.create_firewall_rule(9222)
    assert ok

    ps_cmd = run.call_args.args[0][-1]
    assert f"-InterfaceAlias '{wsl.WSL_ADAPTER_ALIAS}'" in ps_cmd
    assert "-RemoteAddress LocalSubnet" in ps_cmd


def test_privilege_fallback_command_is_not_wide_open(_wsl_env, monkeypatch):
    monkeypatch.setattr(
        wsl.subprocess, "run", Mock(return_value=_run_result(1, "Access is denied"))
    )

    ok, message = wsl.create_firewall_rule(9222)
    assert not ok
    assert "New-NetFirewallRule" in message, "fallback should print a command"
    assert f"-InterfaceAlias '{wsl.WSL_ADAPTER_ALIAS}'" in message
    assert "-RemoteAddress LocalSubnet" in message


def test_cli_prompt_prints_a_scoped_rule():
    """The command users actually copy must carry the same scoping."""
    from pathlib import Path

    source = Path(wsl.__file__).parent.parent / "cli" / "main.py"
    text = source.read_text(encoding="utf-8")
    line = next(ln for ln in text.splitlines() if "New-NetFirewallRule -DisplayName" in ln)
    assert "-InterfaceAlias" in line
    assert "-RemoteAddress LocalSubnet" in line


def test_docstring_makes_no_unqualified_isolation_claim():
    """The old docstring promised no other host could reach the port."""
    assert "No other network hosts can reach" not in (wsl.__doc__ or "")
    assert "SECURITY_REMEDIATION_PLAN" not in (wsl.__doc__ or "")
