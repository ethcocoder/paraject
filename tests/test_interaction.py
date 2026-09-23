import json

from projected_ai_interface.calibration import CalibrationProfile
from projected_ai_interface.interaction import EventLogger, InteractionEngine, UIObject
from projected_ai_interface.interaction_cli import main


def engine(**kwargs):
    profile = CalibrationProfile.from_points((100, 100), (100, 100), [(0, 0), (100, 0), (100, 100), (0, 100)], [(0, 0), (100, 0), (100, 100), (0, 100)])
    return InteractionEngine(profile, [UIObject('documents', 'folder', 10, 10, 40, 40)], **kwargs)


def test_hit_test_and_debounced_touch():
    interaction = engine(debounce_frames=2)
    assert interaction.process((20, 20), .95, 'touch', timestamp=1.0) == []
    events = interaction.process((20, 20), .95, 'touch', timestamp=1.1)
    assert [event.event for event in events] == ['touch']
    assert events[0].object_id == 'documents'


def test_button_touch_uses_same_schema():
    profile = CalibrationProfile.from_points((100, 100), (100, 100), [(0, 0), (100, 0), (100, 100), (0, 100)], [(0, 0), (100, 0), (100, 100), (0, 100)])
    interaction = InteractionEngine(profile, [UIObject('run', 'button', 50, 50, 30, 20)], debounce_frames=1)
    event = interaction.process((60, 60), .95, 'touch', timestamp=1.0)[0]
    assert event.object_type == 'button'
    assert event.object_id == 'run'


def test_low_confidence_never_triggers_touch():
    interaction = engine(debounce_frames=1)
    assert interaction.process((20, 20), .4, 'touch', timestamp=1.0) == []


def test_release_and_drag_events():
    interaction = engine(debounce_frames=1, drag_distance=5)
    assert interaction.process((20, 20), .95, 'touch', timestamp=1.0)[0].event == 'touch'
    assert interaction.process((28, 28), .95, 'hover', timestamp=1.1)[0].event == 'drag_start'
    assert interaction.process((30, 30), .95, 'hover', timestamp=1.2)[0].event == 'drag'
    assert interaction.process(None, .95, 'none', timestamp=1.3)[0].event == 'drag_end'


def test_event_logger_writes_jsonl(tmp_path):
    interaction = engine(debounce_frames=1)
    event = interaction.process((20, 20), .95, 'touch', timestamp=1.0)[0]
    path = tmp_path / 'events.jsonl'
    EventLogger(path).write(event)
    record = json.loads(path.read_text())
    assert record['event'] == 'touch'
    assert 'camera' not in record


def test_interaction_cli_demo(capsys):
    assert main(['--demo']) == 0
    result = json.loads(capsys.readouterr().out)
    assert [item['event'] for item in result['events']] == ['touch', 'release']
