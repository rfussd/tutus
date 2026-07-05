import pytest


@pytest.fixture
def isolated_skill():
    from skills.project_skill import _TEMP_PERMITS, ALLOWED_DIRS, _resolve_path

    _TEMP_PERMITS.clear()
    return _resolve_path, ALLOWED_DIRS


class TestPathResolution:
    def test_allowed_path(self, isolated_skill):
        _resolve_path, _ = isolated_skill
        result = _resolve_path("core/config.py")
        assert result is not None
        assert result.exists()

    def test_denied_path(self, isolated_skill):
        _resolve_path, _ = isolated_skill
        result = _resolve_path(r"C:\Windows\system32\config")
        assert result is None

    def test_absolute_allowed(self, isolated_skill):
        _resolve_path, allowed = isolated_skill
        target = allowed[0] / "core" / "config.py"
        result = _resolve_path(str(target))
        assert result is not None


class TestReadWrite:
    def test_read_file(self):
        from skills.project_skill import read_file

        content = read_file("core/config.py")
        assert content is not None
        assert "LM_STUDIO_URL" in content

    def test_read_denied(self):
        from skills.project_skill import read_file

        result = read_file(r"C:\Windows\system32\drivers\etc\hosts")
        assert "denegado" in result.lower()

    def test_read_nonexistent(self):
        from skills.project_skill import read_file

        result = read_file("nonexistent_file_xyz.py")
        assert "encontrado" in result.lower()


class TestRunShell:
    def test_blocked_command(self):
        from skills.project_skill import run_shell

        result = run_shell("rm -rf /")
        assert "bloqueado" in result.lower()

    def test_blocked_pipe(self):
        from skills.project_skill import run_shell

        result = run_shell("dir | more")
        assert "bloqueado" in result.lower()


class TestSyntax:
    def test_good_syntax(self):
        from skills.project_skill import check_syntax

        result = check_syntax("core/config.py")
        assert "Syntax OK" in result

    def test_nonexistent_file(self):
        from skills.project_skill import check_syntax

        result = check_syntax("no_existe.py")
        assert "encontrado" in result.lower()
