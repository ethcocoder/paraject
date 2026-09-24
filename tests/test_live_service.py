from pathlib import Path

from projected_ai_interface.camera import CameraFrame
from projected_ai_interface.live_service import LiveCameraAgent


class FakeVision:
    def analyze(self, frame):
        return {"clicked": True, "target_label": "Documents", "confidence": 0.95}


def test_live_service_maps_documents_to_child_folder_and_executes_smollm(tmp_path):
    model = Path(".models/smollm-135m/model_q4.onnx")
    tokenizer = Path(".models/smollm-135m/tokenizer.json")
    if not model.is_file() or not tokenizer.is_file():
        import pytest
        pytest.skip("real SmolLM artifacts are not present")
    agent = LiveCameraAgent(
        model_path=model,
        tokenizer_path=tokenizer,
        vision=FakeVision(),
        root=tmp_path,
        host="127.0.0.1",
        port=18765,
        launch_folders=False,
        cooldown_seconds=0,
    )
    agent._process_frame(CameraFrame(None, 0.0, 0, 1, 1))
    assert agent.metrics.actions_succeeded == 1
    assert agent.metrics.last_action["tool"] == "open_folder"
    assert agent.metrics.last_action["tool_result"]["path"] == str((tmp_path / "Documents").resolve())
