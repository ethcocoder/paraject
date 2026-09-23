"""Verify real autoregressive text generation with a local SmolLM ONNX export."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer


def generate(model_path: Path, tokenizer_path: Path, prompt: str, max_new_tokens: int) -> dict[str, object]:
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    encoded = tokenizer.encode(prompt, add_special_tokens=False)
    token_ids = encoded.ids
    session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    specs = session.get_inputs()
    input_names = {item.name for item in specs}
    past_names = sorted(name for name in input_names if name.startswith("past_key_values."))
    output_specs = session.get_outputs()
    output_names = {item.name for item in output_specs}
    if len(past_names) != 60 or sum(name.startswith("present.") for name in output_names) != 60:
        raise RuntimeError("unexpected SmolLM KV-cache graph contract")

    generated = list(token_ids)
    started = time.perf_counter()
    feeds: dict[str, np.ndarray] = {
        "input_ids": np.asarray([token_ids], dtype=np.int64),
        "attention_mask": np.ones((1, len(token_ids)), dtype=np.int64),
        "position_ids": np.arange(len(token_ids), dtype=np.int64)[None, :],
    }
    for name in past_names:
        spec = next(item for item in specs if item.name == name)
        _, heads, _, head_dim = spec.shape
        feeds[name] = np.zeros((1, int(heads), 0, int(head_dim)), dtype=np.float32)

    outputs = session.run(None, feeds)
    by_name = {spec.name: value for spec, value in zip(output_specs, outputs)}
    for _ in range(max_new_tokens):
        next_id = int(np.argmax(by_name["logits"][0, -1]))
        generated.append(next_id)
        if next_id == 2:
            break
        total_length = len(generated)
        feeds = {
            "input_ids": np.asarray([[next_id]], dtype=np.int64),
            "attention_mask": np.ones((1, total_length), dtype=np.int64),
            "position_ids": np.asarray([[total_length - 1]], dtype=np.int64),
        }
        for name in past_names:
            present = "present." + name[len("past_key_values."):]
            feeds[name] = by_name[present]
        outputs = session.run(None, feeds)
        by_name = {spec.name: value for spec, value in zip(output_specs, outputs)}

    decoded = tokenizer.decode(generated, skip_special_tokens=True)
    prompt_decoded = tokenizer.decode(token_ids, skip_special_tokens=True)
    generated_text = decoded[len(prompt_decoded):].strip() if decoded.startswith(prompt_decoded) else decoded
    return {
        "model": "onnx-community/SmolLM-135M-Instruct-ONNX",
        "artifact": str(model_path),
        "artifact_bytes": model_path.stat().st_size,
        "prompt_tokens": len(token_ids),
        "generated_tokens": len(generated) - len(token_ids),
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "text": generated_text,
        "providers": session.get_providers(),
        "onnx_inputs": len(input_names),
        "onnx_outputs": len(output_names),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--tokenizer", required=True, type=Path)
    parser.add_argument("--max-new-tokens", type=int, default=24)
    parser.add_argument("--prompt", default="Say exactly: ONNX local model works.")
    args = parser.parse_args(argv)
    prompt = f"<|im_start|>system\nYou are a concise local assistant.<|im_end|>\n<|im_start|>user\n{args.prompt}<|im_end|>\n<|im_start|>assistant\n"
    result = generate(args.model, args.tokenizer, prompt, args.max_new_tokens)
    print(json.dumps(result, indent=2))
    if not result["text"]:
        raise RuntimeError("real model produced empty decoded output")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
