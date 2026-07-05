from core.memory_signals import (
    forget_memories,
    get_context_for_domain,
    get_conversations,
    get_domain_signals,
    get_signal,
    log_conversation,
    save_memory,
    search_memories,
    set_signal,
)


class TestSignals:
    def test_set_and_get(self, temp_db):
        set_signal("music", "preferred_platform", "spotify")
        assert get_signal("music", "preferred_platform") == "spotify"

    def test_get_nonexistent(self, temp_db):
        assert get_signal("nonexistent", "key") is None

    def test_get_nonexistent_with_default(self, temp_db):
        assert get_signal("music", "no_key", "default_val") == "default_val"

    def test_overwrite(self, temp_db):
        set_signal("music", "preferred_platform", "spotify")
        set_signal("music", "preferred_platform", "youtube")
        assert get_signal("music", "preferred_platform") == "youtube"

    def test_complex_values(self, temp_db):
        val = {"artists": ["jose jose", "bad bunny"], "count": 3}
        set_signal("music", "data", val)
        assert get_signal("music", "data") == val

    def test_get_domain_signals(self, temp_db):
        set_signal("music", "a", 1)
        set_signal("music", "b", 2)
        signals = get_domain_signals("music")
        assert signals == {"a": 1, "b": 2}

    def test_get_domain_signals_empty(self, temp_db):
        assert get_domain_signals("empty") == {}


class TestMemories:
    def test_save_and_search(self, temp_db):
        save_memory("A David le gusta Jose Jose", "music")
        results = search_memories("Jose", domain="music")
        assert len(results) >= 1
        assert "Jose Jose" in results[0]["content"]

    def test_search_all_domains(self, temp_db):
        save_memory("memoria 1", "general")
        save_memory("memoria 2", "music")
        results = search_memories("")
        assert len(results) >= 2

    def test_forget(self, temp_db):
        save_memory("cosa a olvidar", "general")
        result = forget_memories("olvidar")
        assert "Olvidé" in result
        results = search_memories("olvidar")
        assert len(results) == 0

    def test_forget_with_domain(self, temp_db):
        save_memory("secreto", "music")
        save_memory("secreto", "general")
        forget_memories("secreto", domain="music")
        results = search_memories("secreto")
        assert len(results) == 1
        assert results[0]["domain"] == "general"

    def test_empty_search(self, temp_db):
        results = search_memories("")
        assert isinstance(results, list)

    def test_search_limit(self, temp_db):
        for i in range(10):
            save_memory(f"memoria {i}", "general")
        results = search_memories("", limit=3)
        assert len(results) <= 3


class TestContext:
    def test_get_context(self, temp_db):
        set_signal("music", "preferred_platform", "spotify")
        save_memory("A David le gusta el rock", "music")
        ctx = get_context_for_domain("music")
        assert "spotify" in ctx
        assert "rock" in ctx

    def test_get_context_empty(self, temp_db):
        ctx = get_context_for_domain("empty_domain")
        assert ctx == ""


class TestConversations:
    def test_log_and_get(self, temp_db):
        log_conversation("user", "hola")
        log_conversation("assistant", "hola que tal")
        convos = get_conversations(limit=10)
        assert len(convos) >= 2
        assert convos[0]["role"] == "user"
        assert convos[1]["role"] == "assistant"

    def test_get_with_domain(self, temp_db):
        log_conversation("user", "msg1", domain="chat")
        log_conversation("user", "msg2", domain="music")
        convos = get_conversations(domain="music")
        assert len(convos) == 1
        assert convos[0]["content"] == "msg2"
