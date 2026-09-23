import json

from projected_ai_interface.agent import AgentRuntime
from projected_ai_interface.skills import SkillRegistry, ToolRegistry


class FakeProvider:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = 0

    def complete(self, messages, tools):
        self.calls += 1
        return next(self.responses)


def runtime(provider, tmp_path, retries=1):
    skills = SkillRegistry(); skills.load_directory('skills')
    tools = ToolRegistry()
    tools.register('list_folder', lambda path: {'path': path, 'entries': []})
    tools.register('open_folder', lambda path: {'validated': True, 'path': path})
    return AgentRuntime(provider, skills, tools, max_retries=retries)


def test_agent_builds_skill_context_and_executes_valid_action(tmp_path):
    provider = FakeProvider([{'tool': 'list_folder', 'arguments': {'path': str(tmp_path)}}])
    result = runtime(provider, tmp_path).run('List this folder', {'event': 'touch'})
    assert result.ok
    assert result.action.tool == 'list_folder'
    assert result.tool_result.result['path'] == str(tmp_path)
    assert result.latency_ms >= 0


def test_agent_rejects_unregistered_tool(tmp_path):
    provider = FakeProvider([{'tool': 'run_shell', 'arguments': {'command': 'rm -rf /'}}])
    result = runtime(provider, tmp_path, retries=0).run('do it')
    assert not result.ok
    assert 'not registered' in result.error


def test_agent_retries_malformed_output(tmp_path):
    provider = FakeProvider(['not json', {'tool': 'open_folder', 'arguments': {'path': str(tmp_path)}}])
    result = runtime(provider, tmp_path, retries=1).run('Open this folder')
    assert result.ok
    assert provider.calls == 2


def test_agent_supports_noop_action(tmp_path):
    provider = FakeProvider([{'tool': None, 'arguments': {}}])
    result = runtime(provider, tmp_path).run('Do nothing')
    assert result.ok
    assert result.tool_result is None


def test_openai_style_tool_call_is_parsed(tmp_path):
    provider = FakeProvider([{'choices': [{'message': {'tool_calls': [{'function': {'name': 'open_folder', 'arguments': json.dumps({'path': str(tmp_path)})}}]}}]}])
    result = runtime(provider, tmp_path).run('Open folder')
    assert result.ok
    assert result.action.tool == 'open_folder'


def test_agent_accepts_markdown_fenced_json_action(tmp_path):
    response = '```json\n' + json.dumps({'tool': 'open_folder', 'arguments': {'path': str(tmp_path)}}) + '\n```'
    result = runtime(FakeProvider([response]), tmp_path).run('Open folder')
    assert result.ok
    assert result.action.tool == 'open_folder'


def test_agent_returns_structured_invalid_input_result(tmp_path):
    result = runtime(FakeProvider([]), tmp_path).run('')
    assert not result.ok
    assert result.status == 'invalid_input'
    assert result.attempts == 0


def test_agent_contains_unexpected_provider_exception(tmp_path):
    class BrokenProvider:
        def complete(self, messages, tools):
            raise OSError('model process crashed')

    result = runtime(BrokenProvider(), tmp_path, retries=0).run('Open folder')
    assert not result.ok
    assert result.status == 'provider_error'
    assert 'crashed' in result.error
