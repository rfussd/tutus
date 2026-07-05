from unittest.mock import MagicMock


class MockPopen:
    def __init__(self, *args, **kwargs):
        pass


class TestStartLmStudio:
    def test_start_lmstudio_headless_success(self, monkeypatch):
        monkeypatch.setattr("os.path.exists", lambda p: True)
        popen_calls = []

        def fake_popen(args, **kwargs):
            popen_calls.append(args)
            return MagicMock()

        monkeypatch.setattr("subprocess.Popen", fake_popen)
        monkeypatch.setattr("time.sleep", lambda s: None)

        from core.startup import start_lmstudio

        start_lmstudio()
        assert any("server" in str(a) for a in popen_calls)

    def test_start_lmstudio_no_lms_fallback_gui(self, monkeypatch):
        def exists_side_effect(path):
            if "lms.exe" in path:
                return False
            if "LM Studio.exe" in path or "LM Studio" in path:
                return True
            return True

        monkeypatch.setattr("os.path.exists", exists_side_effect)
        monkeypatch.setattr("os.environ", {"LOCALAPPDATA": "C:\\Users\\test\\AppData\\Local"})
        popen_calls = []

        def fake_popen(args, **kwargs):
            popen_calls.append(args)
            return MagicMock()

        monkeypatch.setattr("subprocess.Popen", fake_popen)
        monkeypatch.setattr("time.sleep", lambda s: None)

        from core.startup import start_lmstudio

        start_lmstudio()
        gui_calls = [a for a in popen_calls if "LM Studio.exe" in str(a)]
        assert len(gui_calls) >= 1

    def test_start_lmstudio_no_lms_no_gui(self, monkeypatch):
        monkeypatch.setattr("os.path.exists", lambda p: False)
        monkeypatch.setattr("os.environ", {"LOCALAPPDATA": "C:\\Users\\test\\AppData\\Local"})
        popen_calls = []

        def fake_popen(args, **kwargs):
            popen_calls.append(args)
            return MagicMock()

        monkeypatch.setattr("subprocess.Popen", fake_popen)
        monkeypatch.setattr("time.sleep", lambda s: None)

        from core.startup import start_lmstudio

        start_lmstudio()
        assert len(popen_calls) == 0


class TestEnableDisableStartup:
    def test_enable_startup(self, monkeypatch):
        opened_keys = []
        set_values = []

        def fake_open_key(key, subkey, res, access):
            opened_keys.append((key, subkey, access))
            return "fake_key_handle"

        def fake_set_value(key, name, reserved, regtype, value):
            set_values.append((name, value))

        monkeypatch.setattr("winreg.OpenKey", fake_open_key)
        monkeypatch.setattr("winreg.SetValueEx", fake_set_value)
        monkeypatch.setattr("winreg.CloseKey", lambda k: None)
        monkeypatch.setattr("winreg.HKEY_CURRENT_USER", "HKCU")
        monkeypatch.setattr("winreg.KEY_SET_VALUE", 2)
        monkeypatch.setattr("winreg.REG_SZ", 1)
        monkeypatch.setattr("winreg.KEY_WOW64_64KEY", 256)

        from core.startup import enable_startup

        enable_startup()
        assert any("TUTUS" in str(s) for s in set_values)

    def test_disable_startup(self, monkeypatch):
        deleted_values = []

        def fake_open_key(key, subkey, res, access):
            return "fake_key_handle"

        def fake_delete_value(key, name):
            deleted_values.append(name)

        monkeypatch.setattr("winreg.OpenKey", fake_open_key)
        monkeypatch.setattr("winreg.DeleteValue", fake_delete_value)
        monkeypatch.setattr("winreg.CloseKey", lambda k: None)
        monkeypatch.setattr("winreg.HKEY_CURRENT_USER", "HKCU")
        monkeypatch.setattr("winreg.KEY_SET_VALUE", 2)
        monkeypatch.setattr("winreg.KEY_WOW64_64KEY", 256)

        from core.startup import disable_startup

        disable_startup()
        assert "TUTUS" in deleted_values

    def test_disable_startup_not_found(self, monkeypatch):
        def fake_open_key(key, subkey, res, access):
            return "fake_key_handle"

        def fake_delete_value(key, name):
            raise FileNotFoundError()

        monkeypatch.setattr("winreg.OpenKey", fake_open_key)
        monkeypatch.setattr("winreg.DeleteValue", fake_delete_value)
        monkeypatch.setattr("winreg.CloseKey", lambda k: None)
        monkeypatch.setattr("winreg.HKEY_CURRENT_USER", "HKCU")
        monkeypatch.setattr("winreg.KEY_SET_VALUE", 2)
        monkeypatch.setattr("winreg.KEY_WOW64_64KEY", 256)

        from core.startup import disable_startup

        disable_startup()

    def test_is_startup_enabled_true(self, monkeypatch):
        def fake_open_key(key, subkey, res, access):
            return "fake_key_handle"

        def fake_query_value(key, name):
            return ("value", 1)

        monkeypatch.setattr("winreg.OpenKey", fake_open_key)
        monkeypatch.setattr("winreg.QueryValueEx", fake_query_value)
        monkeypatch.setattr("winreg.CloseKey", lambda k: None)
        monkeypatch.setattr("winreg.HKEY_CURRENT_USER", "HKCU")
        monkeypatch.setattr("winreg.KEY_READ", 1)
        monkeypatch.setattr("winreg.KEY_WOW64_64KEY", 256)

        from core.startup import is_startup_enabled

        assert is_startup_enabled() is True

    def test_is_startup_enabled_false(self, monkeypatch):
        def fake_open_key(key, subkey, res, access):
            raise FileNotFoundError()

        monkeypatch.setattr("winreg.OpenKey", fake_open_key)
        monkeypatch.setattr("winreg.HKEY_CURRENT_USER", "HKCU")
        monkeypatch.setattr("winreg.KEY_READ", 1)
        monkeypatch.setattr("winreg.KEY_WOW64_64KEY", 256)

        from core.startup import is_startup_enabled

        assert is_startup_enabled() is False
