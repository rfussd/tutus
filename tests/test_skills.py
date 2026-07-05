"""Unit tests for TUTUS skills modules.
All external services (subprocess, mss, PIL, requests, pygetwindow, ctypes) are mocked."""

from __future__ import annotations

import base64
import subprocess

import pytest

# ===========================================================================
# 1. TestCodeSandboxSkill — code_sandbox_skill.py
# ===========================================================================


class TestCodeSandboxSkill:
    """Verify _check_code_safety and execute_python with mocked subprocess."""

    # -- _check_code_safety (pure, no mocks needed) -------------------------

    def test_safe_simple_print(self):
        from skills.code_sandbox_skill import _check_code_safety

        safe, msg = _check_code_safety("print('hello world')")
        assert safe
        assert msg == ""

    def test_safe_math_operations(self):
        from skills.code_sandbox_skill import _check_code_safety

        safe, msg = _check_code_safety("result = 2 + 2\nprint(result)")
        assert safe

    def test_safe_list_comprehension(self):
        from skills.code_sandbox_skill import _check_code_safety

        safe, msg = _check_code_safety("[x**2 for x in range(10)]")
        assert safe

    def test_blocked_import_os(self):
        from skills.code_sandbox_skill import _check_code_safety

        safe, msg = _check_code_safety("import os")
        assert not safe
        assert "os" in msg

    def test_blocked_import_subprocess(self):
        from skills.code_sandbox_skill import _check_code_safety

        safe, msg = _check_code_safety("import subprocess")
        assert not safe
        assert "subprocess" in msg

    def test_blocked_import_sys(self):
        from skills.code_sandbox_skill import _check_code_safety

        safe, msg = _check_code_safety("import sys")
        assert not safe
        assert "sys" in msg

    def test_blocked_import_builtins(self):
        from skills.code_sandbox_skill import _check_code_safety

        safe, msg = _check_code_safety("import builtins")
        assert not safe
        assert "builtins" in msg

    def test_blocked_import_ctypes(self):
        from skills.code_sandbox_skill import _check_code_safety

        safe, msg = _check_code_safety("import ctypes")
        assert not safe
        assert "ctypes" in msg

    def test_blocked_import_from_os(self):
        from skills.code_sandbox_skill import _check_code_safety

        safe, msg = _check_code_safety("from os import path")
        assert not safe
        assert "os" in msg

    def test_blocked_builtin_call(self):
        from skills.code_sandbox_skill import _check_code_safety

        safe, msg = _check_code_safety("__import__('os')")
        assert not safe
        assert "__import__" in msg

    def test_blocked_open_call(self):
        from skills.code_sandbox_skill import _check_code_safety

        safe, msg = _check_code_safety("open('/etc/passwd')")
        assert not safe
        assert "open" in msg

    def test_blocked_exec_call(self):
        from skills.code_sandbox_skill import _check_code_safety

        safe, msg = _check_code_safety("exec('print(1)')")
        assert not safe
        assert "exec" in msg

    def test_blocked_eval_call(self):
        from skills.code_sandbox_skill import _check_code_safety

        safe, msg = _check_code_safety("eval('2+2')")
        assert not safe
        assert "eval" in msg

    def test_blocked_compile_call(self):
        from skills.code_sandbox_skill import _check_code_safety

        safe, msg = _check_code_safety("compile('x=1', '<string>', 'exec')")
        assert not safe
        assert "compile" in msg

    def test_blocked_attribute_os_system(self):
        from skills.code_sandbox_skill import _check_code_safety

        safe, msg = _check_code_safety("os.system('ls')")
        assert not safe
        assert "os" in msg.lower()

    def test_blocked_attribute_subprocess_run(self):
        from skills.code_sandbox_skill import _check_code_safety

        safe, msg = _check_code_safety("subprocess.run(['ls'])")
        assert not safe
        assert "subprocess" in msg.lower()

    def test_blocked_attribute_shutil_rmtree(self):
        from skills.code_sandbox_skill import _check_code_safety

        safe, msg = _check_code_safety("shutil.rmtree('/')")
        assert not safe
        assert "shutil" in msg.lower()

    def test_syntax_error(self):
        from skills.code_sandbox_skill import _check_code_safety

        safe, msg = _check_code_safety("print('hello")
        assert not safe
        assert "sintaxis" in msg.lower()

    def test_syntax_error_bad_token(self):
        from skills.code_sandbox_skill import _check_code_safety

        safe, msg = _check_code_safety("break continue")
        assert not safe
        assert "sintaxis" in msg.lower()

    # -- execute_python (mocked subprocess) --------------------------------

    def test_execute_safe_code(self, monkeypatch):
        from skills.code_sandbox_skill import execute_python

        class MockProc:
            stdout = "Hola mundo"
            stderr = ""

        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: MockProc())
        result = execute_python("print('Hola mundo')")
        assert "Hola mundo" in result

    def test_execute_with_stderr(self, monkeypatch):
        from skills.code_sandbox_skill import execute_python

        class MockProc:
            stdout = ""
            stderr = "Warning: something"

        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: MockProc())
        result = execute_python("import warnings; warnings.warn('x')")
        assert "Warning" in result

    def test_execute_no_output(self, monkeypatch):
        from skills.code_sandbox_skill import execute_python

        class MockProc:
            stdout = ""
            stderr = ""

        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: MockProc())
        result = execute_python("x = 42")
        assert "sin salida" in result

    def test_execute_unsafe_import_returns_error(self, monkeypatch):
        """Unsafe code MUST return error WITHOUT calling subprocess."""
        from skills.code_sandbox_skill import execute_python

        called = []

        def fail_run(*a, **kw):
            called.append(True)
            raise RuntimeError("should not be called")

        monkeypatch.setattr(subprocess, "run", fail_run)
        result = execute_python("import os")
        assert "no permitido" in result.lower()
        assert not called

    def test_execute_unsafe_builtin_returns_error(self, monkeypatch):
        from skills.code_sandbox_skill import execute_python

        called = []

        def fail_run(*a, **kw):
            called.append(True)
            raise RuntimeError("should not be called")

        monkeypatch.setattr(subprocess, "run", fail_run)
        result = execute_python("open('test.txt')")
        assert "no permitida" in result.lower()
        assert not called

    def test_execute_timeout(self, monkeypatch):
        from skills.code_sandbox_skill import execute_python

        def timeout_run(*a, **kw):
            raise subprocess.TimeoutExpired(cmd="", timeout=30)

        monkeypatch.setattr(subprocess, "run", timeout_run)
        result = execute_python("while True: pass")
        assert "tardó" in result or "cancelado" in result

    def test_execute_subprocess_error(self, monkeypatch):
        from skills.code_sandbox_skill import execute_python

        def error_run(*a, **kw):
            raise FileNotFoundError("python not found")

        monkeypatch.setattr(subprocess, "run", error_run)
        result = execute_python("print('hi')")
        assert "error" in result.lower()

    def test_execute_whitespace_code(self, monkeypatch):
        from skills.code_sandbox_skill import execute_python

        class MockProc:
            stdout = "   "
            stderr = ""

        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: MockProc())
        result = execute_python("   ")
        # stripped whitespace should return "sin salida"
        assert "sin salida" in result

    def test_execute_stdout_and_stderr(self, monkeypatch):
        from skills.code_sandbox_skill import execute_python

        class MockProc:
            stdout = "normal output"
            stderr = "error output"

        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: MockProc())
        result = execute_python("print('x')")
        assert "normal output" in result
        assert "error output" in result


# ===========================================================================
# 2. TestVisionSkill — vision_skill.py
# ===========================================================================


class TestVisionSkill:
    """Verify capture_screen, analyze_screen, take_screenshot with mocks."""

    # -- Fixture helpers ----------------------------------------------------

    @pytest.fixture
    def mock_mss(self, monkeypatch):
        """Mock mss.MSS so no real screen capture happens."""

        class MockScreenshot:
            size = (1920, 1080)
            bgra = b"B" * (1920 * 1080 * 4)

        class MockMSS:
            def __init__(self):
                self.monitors = [
                    {"left": 0, "top": 0, "width": 1920, "height": 1080},
                    {"left": 0, "top": 0, "width": 1920, "height": 1080},
                ]

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def grab(self, monitor):
                return MockScreenshot()

        monkeypatch.setattr("skills.vision_skill.mss.MSS", MockMSS)

    @pytest.fixture
    def mock_pil(self, monkeypatch):
        """Mock PIL.Image so no actual image processing occurs."""

        class MockImage:
            _saved_path = None

            @staticmethod
            def frombytes(*args, **kwargs):
                return MockImage()

            def thumbnail(self, size):
                pass

            def save(self, path, *args, **kwargs):
                MockImage._saved_path = path

        monkeypatch.setattr("skills.vision_skill.Image", MockImage)
        return MockImage

    @pytest.fixture
    def mock_tempfile(self, monkeypatch):
        """Mock tempfile.NamedTemporaryFile to avoid real files."""

        class MockTempFile:
            name = "C:\\tmp\\test_screenshot.jpg"

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def close(self):
                pass

        def mock_ntf(*args, **kwargs):
            return MockTempFile()

        monkeypatch.setattr("tempfile.NamedTemporaryFile", mock_ntf)

    @pytest.fixture
    def mock_file_read(self, monkeypatch):
        """Mock open() for reading the temp file (returns fake binary data)."""

        class MockFileObj:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def read(self):
                return b"fake_jpeg_bytes_12345"

        monkeypatch.setattr("builtins.open", lambda *a, **kw: MockFileObj())

    @pytest.fixture
    def mock_unlink(self, monkeypatch):
        monkeypatch.setattr("os.unlink", lambda p: None)

    @pytest.fixture
    def mock_startfile(self, monkeypatch):
        monkeypatch.setattr("os.startfile", lambda p: None)

    # -- capture_screen ----------------------------------------------------

    def test_capture_screen_returns_base64(
        self,
        mock_mss,
        mock_pil,
        mock_tempfile,
        mock_file_read,
        mock_unlink,
    ):
        from skills.vision_skill import capture_screen

        result = capture_screen()
        assert isinstance(result, str)
        assert len(result) > 0
        # Verify it's valid base64
        decoded = base64.b64decode(result)
        assert decoded == b"fake_jpeg_bytes_12345"

    def test_capture_screen_monitor_parameter(
        self,
        mock_mss,
        mock_pil,
        mock_tempfile,
        mock_file_read,
        mock_unlink,
    ):
        from skills.vision_skill import capture_screen

        result = capture_screen(monitor=1)
        assert isinstance(result, str)
        assert len(result) > 0

    # -- analyze_screen ----------------------------------------------------

    def test_analyze_screen_success(self, mock_mss, mock_pil, mock_tempfile, mock_file_read, mock_unlink, monkeypatch):
        from tests.helpers import MockResponse

        monkeypatch.setattr(
            "skills.vision_skill.requests.post",
            lambda url, **kw: MockResponse(json_data={"choices": [{"message": {"content": "Veo una pantalla con iconos."}}]}),
        )

        from skills.vision_skill import analyze_screen

        result = analyze_screen("¿Qué ves?")
        assert isinstance(result, str)
        assert "Veo una pantalla" in result

    def test_analyze_screen_error_handling(self, mock_mss, mock_pil, mock_tempfile, mock_file_read, mock_unlink, monkeypatch):
        def failing_post(url, **kw):
            raise ConnectionError("Connection refused")

        monkeypatch.setattr("skills.vision_skill.requests.post", failing_post)

        from skills.vision_skill import analyze_screen

        result = analyze_screen()
        assert "Error" in result or "error" in result

    def test_analyze_screen_custom_question(self, mock_mss, mock_pil, mock_tempfile, mock_file_read, mock_unlink, monkeypatch):
        from tests.helpers import MockResponse

        captured = {}

        def tracking_post(url, **kw):
            body = kw.get("json", {})
            captured["body"] = body
            return MockResponse(json_data={"choices": [{"message": {"content": "Respuesta mock"}}]})

        monkeypatch.setattr("skills.vision_skill.requests.post", tracking_post)

        from skills.vision_skill import analyze_screen

        analyze_screen("¿Hay alguna ventana abierta?")
        msgs = captured["body"].get("messages", [])
        user_msg = msgs[-1]
        # user msg content is a list: [image, text]
        assert any("ventana" in str(c) for c in user_msg.get("content", []))

    # -- take_screenshot ---------------------------------------------------

    def test_take_screenshot_returns_name(self, mock_mss, mock_pil, mock_startfile, monkeypatch):
        from skills.vision_skill import take_screenshot

        class MockPath:
            _call_count = 0

            def __init__(self, *parts):
                MockPath._call_count += 1

            @property
            def parent(self):
                return MockPath()

            def mkdir(self, parents=False, exist_ok=False):
                pass

            def __truediv__(self, other):
                return MockPath()

            @property
            def name(self):
                return "test_img_20250705_120000.jpg"

        monkeypatch.setattr("pathlib.Path", MockPath)

        result = take_screenshot("test_img")
        assert "Captura guardada" in result
        assert "test_img" in result

    def test_take_screenshot_default_filename(self, mock_mss, mock_pil, mock_startfile, monkeypatch):
        from skills.vision_skill import take_screenshot

        class MockPath:
            def __init__(self, *parts):
                pass

            @property
            def parent(self):
                return MockPath()

            def mkdir(self, parents=False, exist_ok=False):
                pass

            def __truediv__(self, other):
                return MockPath()

            @property
            def name(self):
                return "screenshot_20250705_120000.jpg"

        monkeypatch.setattr("pathlib.Path", MockPath)

        result = take_screenshot()
        assert "Captura guardada" in result
        assert "screenshot" in result


# ===========================================================================
# 3. TestWindowControlSkill — window_control_skill.py
# ===========================================================================


class TestWindowControlSkill:
    """Verify window operations with mocked pygetwindow, ctypes, subprocess."""

    # -- Fixture helpers ----------------------------------------------------

    @pytest.fixture
    def mock_windows(self, monkeypatch):
        """Replace gw.getAllWindows with a controllable list."""

        class MockWindow:
            def __init__(self, title, visible=True):
                self.title = title
                self._minimized = False
                self._maximized = False
                self._closed = False
                self._activated = False
                self._x = self._y = self._w = self._h = 0

            def minimize(self):
                self._minimized = True

            def maximize(self):
                self._maximized = True

            def close(self):
                self._closed = True

            def activate(self):
                self._activated = True

            def moveTo(self, x, y):
                self._x, self._y = x, y

            def resizeTo(self, w, h):
                self._w, self._h = w, h

        windows = [
            MockWindow("Spotify"),
            MockWindow("Google Chrome"),
            MockWindow("Terminal"),
            MockWindow(""),  # empty title should be filtered in list_windows
        ]

        monkeypatch.setattr("pygetwindow.getAllWindows", lambda: windows)
        return windows

    @pytest.fixture
    def mock_no_windows(self, monkeypatch):
        monkeypatch.setattr("pygetwindow.getAllWindows", lambda: [])

    @pytest.fixture
    def mock_ctypes(self, monkeypatch):
        """Mock ctypes.windll.user32 for move_window."""

        class MockUser32:
            def GetSystemMetrics(self, n):
                return {0: 1920, 1: 1080}.get(n, 0)

        class MockWinDLL:
            user32 = MockUser32()

        monkeypatch.setattr("ctypes.windll", MockWinDLL())

    @pytest.fixture
    def mock_subprocess_run(self, monkeypatch):
        """Mock subprocess.run for close_window fallback."""

        class MockProc:
            stdout = ""
            stderr = ""

        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: MockProc())

    # -- _find_window (indirectly tested via operations) -------------------

    def test_focus_window_found(self, mock_windows):
        from skills.window_control_skill import focus_window

        result = focus_window("spotify")
        assert "Enfoqué" in result
        assert mock_windows[0]._activated

    def test_focus_window_not_found(self, mock_windows):
        from skills.window_control_skill import focus_window

        result = focus_window("nonexistent")
        assert "No encontré" in result
        # Ensure no window was activated
        assert not any(w._activated for w in mock_windows)

    def test_focus_window_case_insensitive(self, mock_windows):
        from skills.window_control_skill import focus_window

        result = focus_window("GOOGLE CHROME")
        assert "Enfoqué" in result
        assert mock_windows[1]._activated

    def test_list_windows(self, mock_windows):
        from skills.window_control_skill import list_windows

        result = list_windows()
        assert "Ventanas abiertas" in result
        assert "Spotify" in result
        assert "Google Chrome" in result
        assert "Terminal" in result
        # empty-title window should NOT appear
        assert "Ventanas abiertas (3)" in result

    def test_list_windows_none_open(self, mock_no_windows):
        from skills.window_control_skill import list_windows

        result = list_windows()
        assert "No hay ventanas" in result

    def test_list_windows_up_to_15(self, monkeypatch):
        many = []
        for i in range(20):
            w = type("W", (), {"title": f"Window {i}", "strip": lambda self: self.title})()
            w.title = f"Window {i}"
            many.append(w)

        monkeypatch.setattr("pygetwindow.getAllWindows", lambda: many)

        from skills.window_control_skill import list_windows

        result = list_windows()
        lines = result.strip().split("\n")
        # Header + up to 15 windows
        assert len(lines) <= 16

    def test_minimize_window(self, mock_windows):
        from skills.window_control_skill import minimize_window

        result = minimize_window("spotify")
        assert "Minimicé" in result
        assert mock_windows[0]._minimized

    def test_minimize_window_not_found(self, mock_windows):
        from skills.window_control_skill import minimize_window

        result = minimize_window("nope")
        assert "No encontré" in result

    def test_maximize_window(self, mock_windows):
        from skills.window_control_skill import maximize_window

        result = maximize_window("spotify")
        assert "Maximicé" in result
        assert mock_windows[0]._maximized

    def test_maximize_window_not_found(self, mock_windows):
        from skills.window_control_skill import maximize_window

        result = maximize_window("nope")
        assert "No encontré" in result

    def test_close_window_found(self, mock_windows):
        from skills.window_control_skill import close_window

        result = close_window("spotify")
        assert "Cerré" in result
        assert mock_windows[0]._closed

    def test_close_window_not_found_falls_back_to_taskkill(
        self,
        mock_windows,
        mock_subprocess_run,
    ):
        from skills.window_control_skill import close_window

        result = close_window("notepad")
        assert "Cerré" in result
        assert not any(w._closed for w in mock_windows)

    def test_move_window_center(self, mock_windows, mock_ctypes):
        from skills.window_control_skill import move_window

        result = move_window("spotify", "center")
        assert "Moví" in result
        assert mock_windows[0]._x == 1920 // 4
        assert mock_windows[0]._y == 1080 // 8

    def test_move_window_left(self, mock_windows, mock_ctypes):
        from skills.window_control_skill import move_window

        result = move_window("spotify", "left")
        assert "Moví" in result
        assert mock_windows[0]._x == 0
        assert mock_windows[0]._w == 1920 // 2

    def test_move_window_right(self, mock_windows, mock_ctypes):
        from skills.window_control_skill import move_window

        result = move_window("spotify", "right")
        assert "Moví" in result
        assert mock_windows[0]._x == 1920 // 2

    def test_move_window_fullscreen(self, mock_windows, mock_ctypes):
        from skills.window_control_skill import move_window

        result = move_window("spotify", "fullscreen")
        assert "Moví" in result
        assert mock_windows[0]._x == 0
        assert mock_windows[0]._w == 1920
        assert mock_windows[0]._h == 1080

    def test_move_window_unknown_position_falls_to_center(
        self,
        mock_windows,
        mock_ctypes,
    ):
        from skills.window_control_skill import move_window

        result = move_window("spotify", "topright")
        assert "Moví" in result
        assert mock_windows[0]._x == 1920 // 4

    def test_move_window_not_found(self, mock_windows, mock_ctypes):
        from skills.window_control_skill import move_window

        result = move_window("nonexistent", "center")
        assert "No encontré" in result

    # -- Error handling ----------------------------------------------------

    def test_generic_error_on_list_windows(self, monkeypatch):
        def explode(*a, **kw):
            raise RuntimeError("mock explosion")

        monkeypatch.setattr("pygetwindow.getAllWindows", explode)

        from skills.window_control_skill import list_windows

        result = list_windows()
        assert "Error" in result

    def test_generic_error_on_focus_window(self, monkeypatch):
        def explode(*a, **kw):
            raise RuntimeError("mock explosion")

        monkeypatch.setattr("pygetwindow.getAllWindows", explode)

        from skills.window_control_skill import focus_window

        result = focus_window("spotify")
        assert "Error" in result

    def test_generic_error_on_minimize_window(self, monkeypatch):
        class BadWindow:
            title = "Spotify"

            def minimize(self):
                raise RuntimeError("minimize fail")

        monkeypatch.setattr(
            "pygetwindow.getAllWindows",
            lambda: [BadWindow()],
        )

        from skills.window_control_skill import minimize_window

        result = minimize_window("spotify")
        assert "Error" in result

    def test_generic_error_on_move_window(self, mock_ctypes, monkeypatch):
        class BadWindow:
            title = "Spotify"

            def moveTo(self, x, y):
                raise RuntimeError("move fail")

            def resizeTo(self, w, h):
                pass

        monkeypatch.setattr(
            "pygetwindow.getAllWindows",
            lambda: [BadWindow()],
        )

        from skills.window_control_skill import move_window

        result = move_window("spotify", "left")
        assert "Error" in result
