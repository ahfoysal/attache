"""Policy engine tests — the security choke point."""

from attache.gateway.policy import PolicyEngine

pe = PolicyEngine()


def test_readonly_tools_are_t0():
    assert pe.evaluate("Read", {"file_path": "x"}).tier == "T0"
    assert pe.evaluate("Grep", {"pattern": "x"}).allowed is True


def test_edit_tools_are_t1():
    v = pe.evaluate("Edit", {"file_path": "x"})
    assert v.tier == "T1" and v.allowed is True


def test_read_only_shell_allowed():
    assert pe.evaluate("Bash", {"command": "git status"}).tier == "T0"
    assert pe.evaluate("Bash", {"command": "ls -la"}).allowed is True
    assert pe.evaluate("Bash", {"command": "pytest -q"}).tier == "T0"


def test_push_needs_confirmation():
    v = pe.evaluate("Bash", {"command": "git push origin main"})
    assert v.tier == "T3" and v.needs_approval and not v.allowed


def test_install_is_one_time_consent():
    assert pe.evaluate("Bash", {"command": "npm install left-pad"}).tier == "T2"
    assert pe.evaluate("Bash", {"command": "pip install requests"}).tier == "T2"


def test_destructive_is_prohibited():
    v = pe.evaluate("Bash", {"command": "rm -rf /"})
    assert v.tier == "T4" and v.prohibited and not v.allowed
    assert pe.evaluate("Bash", {"command": "git push --force origin main"}).prohibited


def test_unknown_shell_defaults_to_workspace_tier():
    assert pe.evaluate("Bash", {"command": "python build.py"}).tier == "T1"


def test_unknown_tool_defaults_to_consent():
    assert pe.evaluate("SomeNewTool", {}).tier == "T2"
