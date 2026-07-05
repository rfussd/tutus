class TestLogAction:
    def test_log_action_creates_table_and_inserts(self, temp_db):
        from core.proactive import get_patterns, log_action

        log_action("spotify_play", "music", {"query": "jose jose"})
        patterns = get_patterns()
        assert len(patterns) == 0

    def test_log_action_without_params(self, temp_db):
        from core.proactive import log_action

        log_action("open_app", "computer")
        from core.proactive import get_patterns

        patterns = get_patterns()
        assert isinstance(patterns, list)

    def test_multiple_logs(self, temp_db):
        from core.proactive import log_action

        for _ in range(5):
            log_action("spotify_play", "music", {"query": "jose jose"})
        from core.proactive import get_patterns

        patterns = get_patterns()
        assert len(patterns) >= 1


class TestGetPatterns:
    def test_get_patterns_empty(self, temp_db):
        from core.proactive import get_patterns

        assert get_patterns() == []

    def test_get_patterns_with_data(self, temp_db):
        from core.proactive import log_action

        for _ in range(3):
            log_action("spotify_play", "music", {"query": "jose jose"})
        from core.proactive import get_patterns

        patterns = get_patterns()
        assert len(patterns) >= 1


class TestCheckProactiveSuggestions:
    def test_check_with_no_patterns(self, temp_db):
        from core.proactive import check_proactive_suggestions

        check_proactive_suggestions()

    def test_check_with_matching_pattern(self, temp_db):
        from core.proactive import check_proactive_suggestions, log_action, set_callback

        for _ in range(3):
            log_action("spotify_play", "music", {"query": "jose jose"})

        self._called = False

        def callback(msg, pattern):
            self._called = True

        set_callback(callback)
        check_proactive_suggestions()


class TestStartProactiveEngine:
    def test_start_proactive_engine_starts_scheduler(self, monkeypatch):
        def fake_run_pending():
            pass

        monkeypatch.setattr("schedule.run_pending", fake_run_pending)

        callbacks = []

        def cb(msg, pattern):
            callbacks.append((msg, pattern))

        from core.proactive import start_proactive_engine

        start_proactive_engine(cb)

        start_proactive_engine(cb)

    def test_start_proactive_engine_sets_callback(self, monkeypatch):
        monkeypatch.setattr("schedule.run_pending", lambda: None)

        captured = []

        def cb(msg, pattern):
            captured.append((msg, pattern))

        from core.proactive import start_proactive_engine

        start_proactive_engine(cb)

        from core.proactive import _callback

        assert _callback is cb
