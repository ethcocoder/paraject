import json

from projected_ai_interface.builtin_tools import ConfirmationRequired, PathSandbox, copy_file, create_folder, delete_file, list_folder, move_file, open_app, open_folder, search_files
from projected_ai_interface.skills import SkillRegistry, ToolRegistry, parse_skill_markdown

ROOT = 'skills'


def test_loads_documented_skills():
    registry = SkillRegistry()
    assert registry.load_directory(ROOT) == 8
    assert registry.names() == ('copy_file', 'create_folder', 'delete_file', 'list_folder', 'move_file', 'open_app', 'open_folder', 'search_files')
    assert registry.get('open_folder').tool == 'open_folder'


def test_tool_registry_is_an_allowlist(tmp_path):
    tools = ToolRegistry()
    tools.register('list_folder', lambda path: {'path': path})
    assert tools.call('list_folder', {'path': str(tmp_path)}).ok
    denied = tools.call('rm', {'path': '/tmp/file'})
    assert not denied.ok
    assert 'not allowlisted' in denied.error


def test_filesystem_tools_reject_path_escape(tmp_path):
    sandbox = PathSandbox([tmp_path])
    outside = tmp_path.parent / 'outside'
    result = ToolRegistry()
    result.register('open_folder', lambda path: open_folder(path, sandbox))
    assert not result.call('open_folder', {'path': str(outside)}).ok


def test_safe_filesystem_tool_flow(tmp_path):
    sandbox = PathSandbox([tmp_path])
    project = tmp_path / 'project'
    assert create_folder(str(project), sandbox)['created']
    (project / 'notes.txt').write_text('hello')
    assert list_folder(str(project), sandbox)['entries'][0]['name'] == 'notes.txt'
    assert search_files(str(tmp_path), 'note', sandbox)['matches']
    assert open_folder(str(project), sandbox)['validated']


def test_open_app_requires_explicit_allowlist():
    assert open_app('notepad', {'notepad'})['validated']
    try:
        open_app('powershell dangerous text', {'notepad'})
    except PermissionError:
        pass
    else:
        raise AssertionError('unallowlisted application was accepted')


def test_move_copy_and_delete_confirmation(tmp_path):
    sandbox = PathSandbox([tmp_path])
    source = tmp_path / 'source.txt'
    source.write_text('payload')
    copied = tmp_path / 'copied.txt'
    moved = tmp_path / 'moved.txt'
    assert copy_file(str(source), str(copied), sandbox)['copied']
    assert move_file(str(copied), str(moved), sandbox)['moved']
    try:
        delete_file(str(moved), sandbox)
    except ConfirmationRequired:
        pass
    else:
        raise AssertionError('delete without confirmation was accepted')
    assert delete_file(str(moved), sandbox, confirmed=True)['deleted']


def test_skill_parser_rejects_missing_sections(tmp_path):
    path = tmp_path / 'SKILL.md'
    path.write_text('## Name\nmissing-fields\n')
    try:
        parse_skill_markdown(path)
    except ValueError as exc:
        assert 'missing sections' in str(exc)
    else:
        raise AssertionError('invalid skill was accepted')
