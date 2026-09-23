import numpy as np
import onnx
from onnx import TensorProto, helper

from projected_ai_interface.agent import AgentConfig, OnnxActionProvider, provider_from_config


def write_tiny_action_model(path):
    inputs = [helper.make_tensor_value_info("input_ids", TensorProto.INT64, [1, 8])]
    output = helper.make_tensor_value_info("logits", TensorProto.FLOAT, [1, 3])
    weights = np.zeros((8, 3), dtype=np.float32)
    weights[0, 1] = 4.0  # first token 1 selects open_folder
    weights[0, 2] = 4.0  # first token 2 selects list_folder
    initializer = helper.make_tensor("weights", TensorProto.FLOAT, [8, 3], weights.flatten().tolist())
    cast = helper.make_node("Cast", inputs=["input_ids"], outputs=["input_float"], to=TensorProto.FLOAT)
    matmul = helper.make_node("MatMul", inputs=["input_float", "weights"], outputs=["logits"])
    graph = helper.make_graph([cast, matmul], "tiny-projected-action", inputs, [output], initializer=[initializer])
    model = helper.make_model(graph, producer_name="projected-ai-interface", opset_imports=[helper.make_opsetid("", 13)])
    model.ir_version = 13
    onnx.checker.check_model(model)
    onnx.save(model, path)


def test_onnx_provider_runs_standalone_tiny_model(tmp_path):
    model_path = tmp_path / "tiny-action.onnx"
    write_tiny_action_model(model_path)
    provider = OnnxActionProvider(str(model_path), vocabulary={"open": 1, "list": 2}, labels=("null", "open_folder", "list_folder"), max_tokens=8)
    response = provider.complete([{"role": "user", "content": "Open the touched folder"}], [])
    assert response == {"tool": "open_folder", "arguments": {}}


def test_onnx_provider_can_be_selected_from_config(tmp_path):
    model_path = tmp_path / "tiny-action.onnx"
    write_tiny_action_model(model_path)
    config = AgentConfig(backend="onnx", onnx_model=str(model_path))
    provider = provider_from_config(config)
    assert isinstance(provider, OnnxActionProvider)
