# Production Readiness and Operations

## Scope

Projected AI Interface is a local desktop application, not a hosted web service. Production deployment therefore means a controlled workstation installation with an attached projector and camera, a pinned local model artifact, explicit filesystem roots, and an operator-visible recovery path. The application must not be deployed with unrestricted filesystem roots or arbitrary shell execution.

## Required release inputs

The release must be built from a tagged commit and installed in a dedicated virtual environment with the version-pinned Python runtime supported by CI. Install the tested extras with:

```bash
python -m pip install -e '.[test,onnx,network]'
python -m pytest -q
```

The causal SmolLM backend requires both `model_q4.onnx` and its matching `tokenizer.json`. Store them in a read-only model directory, record the source revision and SHA-256 checksums in the deployment record, and configure:

```bash
export PROJECTED_AGENT_BACKEND=smollm
export PROJECTED_AGENT_ONNX_MODEL=/opt/projected-ai/models/model_q4.onnx
export PROJECTED_AGENT_ONNX_TOKENIZER=/opt/projected-ai/models/tokenizer.json
export PROJECTED_AGENT_ONNX_MAX_NEW_TOKENS=64
export PROJECTED_AGENT_RETRIES=1
```

Never commit model artifacts, API keys, camera captures, event logs containing personal data, or local filesystem paths to the repository.

## Safety controls

Register only documented skills. Construct `PathSandbox` with the smallest required set of roots. Keep destructive tools confirmation-gated. Treat model output as untrusted input: `AgentRuntime` bounds request/event sizes, requires the exact `tool`/`arguments` shape, checks the tool allowlist and documented skills, and returns structured failure statuses instead of executing arbitrary text. Network camera input must remain on the trusted local network or behind an authenticated transport before field deployment.

## Release gate

A release is not ready until all of the following are true:

1. CI passes on Python 3.10, 3.11, and 3.12.
2. `python -m pytest -q` passes locally, including the pipeline-to-filesystem end-to-end test.
3. The real pinned SmolLM ONNX artifact passes `scripts/verify_smollm_onnx.py` on the target workstation.
4. A target-workstation smoke test completes camera discovery, calibration loading, a debounced touch, safe tool validation, and projector feedback.
5. Model and source checksums are recorded, and the rollback tag is known.
6. Logs are writable, bounded, and do not contain camera frames or secrets.
7. An operator can stop the camera receiver and projector UI without deleting user data.

## Operational limitations

The current repository does not provide a supervisor, authenticated remote administration, automatic model download, crash restart policy, or a hardware-in-the-loop CI runner. Those are deployment-specific controls and must be supplied by the workstation environment before claiming unattended production operation. The application is production-hardened at its local agent/tool boundary, but hardware deployment remains subject to target-device validation.

## Incident response

On unsafe or unexpected behavior, stop the projector UI and camera receiver, preserve the structured event/tool logs, disable the model backend, and run the deterministic UI and tool path only. Do not rerun destructive tools until the model artifact, skill files, filesystem roots, and recent tool execution log have been reviewed.
