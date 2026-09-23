import asyncio

from projected_ai_interface.agent import AgentRuntime
from projected_ai_interface.calibration import CalibrationProfile
from projected_ai_interface.camera import NetworkCameraSource
from projected_ai_interface.interaction import InteractionEngine, UIObject
from projected_ai_interface.pipeline import DesktopInteractionPipeline
from projected_ai_interface.skills import SkillRegistry, ToolRegistry


class FakeProvider:
    def complete(self, messages, tools):
        assert any(item["function"]["name"] == "open_folder" for item in tools)
        return {"tool": "open_folder", "arguments": {"path": messages[-1]["content"].split("path ")[-1].split("\\n")[0]}}


def make_pipeline(tmp_path):
    calibration = CalibrationProfile.from_points(
        (100, 100), (100, 100),
        [(0, 0), (100, 0), (100, 100), (0, 100)],
        [(0, 0), (100, 0), (100, 100), (0, 100)],
    )
    interaction = InteractionEngine(calibration, [UIObject("documents", "folder", 20, 20, 40, 40)], debounce_frames=2)
    skills = SkillRegistry()
    skills.load_directory("skills")
    tools = ToolRegistry()
    tools.register("open_folder", lambda path: {"validated": True, "path": path})
    return DesktopInteractionPipeline(interaction, AgentRuntime(FakeProvider(), skills, tools, max_retries=0))


def test_synthetic_folder_touch_flow_reaches_safe_tool(tmp_path):
    pipeline = make_pipeline(tmp_path)
    observations = [
        {"camera_point": (30, 30), "confidence": 0.95, "contact": "touch", "timestamp": 1.0},
        {"camera_point": (30, 30), "confidence": 0.95, "contact": "touch", "timestamp": 1.1},
    ]
    results = pipeline.process_observations(observations)
    assert results[0].agent_result is None
    assert results[1].events[0].event == "touch"
    assert results[1].agent_result is not None
    assert results[1].agent_result.ok
    assert results[1].feedback == "success"


def test_network_receiver_rejects_non_binary_and_bounds_queue():
    source = NetworkCameraSource(queue_size=1, decoder=lambda payload: (payload, 1, 1))

    class FakeSocket:
        def __init__(self):
            self.closed = None

        def __aiter__(self):
            async def items():
                for item in ["text is ignored", b"one", b"two"]:
                    yield item
            return items()

        async def close(self, **kwargs):
            self.closed = kwargs

    asyncio.run(source._handle_client(FakeSocket()))
    assert source.received_frames == 2
    assert source.dropped_frames == 1
    source._opened = True
    frame = source.read()
    assert frame is not None
    assert frame.sequence == 1


def test_network_receiver_rejects_wrong_path():
    source = NetworkCameraSource()

    class FakeSocket:
        path = "/wrong"
        closed = None

        async def close(self, **kwargs):
            self.closed = kwargs

    socket = FakeSocket()
    asyncio.run(source._handle_client(socket))
    assert socket.closed["code"] == 1008


def test_network_receiver_reports_decoder_failure_without_exposing_frame():
    source = NetworkCameraSource(decoder=lambda payload: (_ for _ in ()).throw(ValueError("bad jpeg")))
    source._opened = True
    source._frames.put_nowait((b"not-jpeg", 1.0, 0))
    assert source.read() is None
    assert source.invalid_frames == 1
