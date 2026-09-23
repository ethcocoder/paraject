import time

from projected_ai_interface.agent import AgentConfig, AgentRuntime, OpenAICompatibleProvider
from projected_ai_interface.skills import SkillRegistry, ToolRegistry


def make_runtime(provider, retries=0):
    skills = SkillRegistry()
    skills.load_directory("skills")
    tools = ToolRegistry()
    tools.register("open_folder", lambda path: {"path": path})
    return AgentRuntime(provider, skills, tools, max_retries=retries)


class Provider:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    def complete(self, messages, tools):
        self.calls += 1
        return self.response


def test_agent_requires_exact_action_shape(tmp_path):
    result = make_runtime(Provider({"tool": "open_folder", "arguments": {"path": str(tmp_path)}, "extra": True})).run("open")
    assert not result.ok
    assert result.status == "invalid_output"


def test_agent_retries_provider_failure_and_reports_attempts():
    class Failing:
        def complete(self, messages, tools):
            raise RuntimeError("local model unavailable: refused")

    result = make_runtime(Failing(), retries=2).run("open")
    assert not result.ok
    assert result.attempts == 3
    assert result.status == "provider_error"
    assert "unavailable" in result.error


def test_tool_registry_rejects_malformed_arguments_and_logs():
    tools = ToolRegistry()
    tools.register("echo", lambda value: value)
    result = tools.call("echo", {"unexpected": "x"})
    assert not result.ok
    assert result.code == "malformed_arguments"
    assert tools.execution_log[-1].name == "echo"


def test_tool_registry_timeout_is_structured():
    tools = ToolRegistry()

    def slow():
        time.sleep(0.2)
        return "done"

    tools.register("slow", slow)
    result = tools.call("slow", {}, timeout_seconds=0.01)
    assert not result.ok
    assert result.code == "timeout"


def test_tool_registry_contains_unexpected_exception():
    tools = ToolRegistry()
    def broken():
        raise RuntimeError("boom")
    tools.register("broken", broken)
    result = tools.call("broken", {})
    assert not result.ok
    assert result.code == "RuntimeError"
    assert result.error == "boom"


def test_tool_registry_rejects_duplicate_registration():
    tools = ToolRegistry()
    tools.register("echo", lambda: "first")
    try:
        tools.register("echo", lambda: "second")
    except ValueError as exc:
        assert "already registered" in str(exc)
    else:
        raise AssertionError("duplicate tool registration was accepted")


def test_config_reads_environment(monkeypatch):
    monkeypatch.setenv("PROJECTED_AGENT_BASE_URL", "http://localhost:9000/v1")
    monkeypatch.setenv("PROJECTED_AGENT_MODEL", "local-model")
    monkeypatch.setenv("PROJECTED_AGENT_TIMEOUT", "4.5")
    monkeypatch.setenv("PROJECTED_AGENT_RETRIES", "3")
    config = AgentConfig.from_env()
    assert config.base_url.endswith("9000/v1")
    assert config.model == "local-model"
    assert config.timeout_seconds == 4.5
    assert config.max_retries == 3


def test_provider_rejects_invalid_timeout():
    try:
        OpenAICompatibleProvider(timeout_seconds=0)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid timeout accepted")
