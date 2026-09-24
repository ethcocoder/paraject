# Projected AI Interface

> A local AI-powered projected computer interface using a mobile phone camera, computer vision, a projector, and an existing small LLM with tool skills.

## Team

- **Ethco Coder**
- **Natnael Ermiyas**

## Concept

The project turns a normal projected computer display into a physical interaction surface.

A mobile phone acts as the camera sensor. The phone sends camera frames to a desktop through a local network or, where practical, USB. The desktop detects the user's hand and fingertip, maps the camera coordinates to the projector coordinates, identifies projected UI objects, and generates structured interaction events.

An existing small local LLM — for example, a TinyLlama-class model — can then act as an agent using a system prompt and `SKILL.md` capability descriptions.

**No LLM fine-tuning is required for the initial design.**

## Architecture

```text
                 📱 MOBILE PHONE
                  Camera Sensor
                       |
                  Wi-Fi / USB
                       |
                       v
              ┌─────────────────┐
              │ Desktop Receiver│
              └────────┬────────┘
                       |
                       v
              ┌─────────────────┐
              │ Computer Vision │
              │ Hand/Fingertip  │
              └────────┬────────┘
                       |
                       v
              ┌─────────────────┐
              │  Calibration +  │
              │ Interaction     │
              └────────┬────────┘
                       |
                 Structured Event
                       |
                       v
              ┌─────────────────┐
              │   Small Local   │
              │       LLM       │
              │ System Prompt + │
              │    SKILL.md     │
              └────────┬────────┘
                       |
                       v
              ┌─────────────────┐
              │ Tool Validation │
              └────────┬────────┘
                       |
             ┌─────────┼─────────┐
             v         v         v
        PowerShell   CMD      Python/OS
             \         |         /
              \        |        /
               v       v       v
                  Windows
                     |
                     v
                 Projector
```

## Example

Imagine a projected folder named **Documents**.

The user places a finger on it.

```text
Camera
  ↓
Hand tracking
  ↓
Fingertip detected
  ↓
Coordinate transformation
  ↓
Projected object = Documents
  ↓
TOUCH(Documents)
  ↓
Agent selects open_folder skill
  ↓
Tool validation
  ↓
Windows opens Documents
  ↓
Projector displays feedback
```

## Why the LLM is not in the raw vision loop

Basic physical interaction should be fast.

Instead of sending camera images directly to the LLM:

```text
Camera → LLM → action
```

the system uses:

```text
Camera
  ↓
Vision
  ↓
Interaction engine
  ↓
Structured event
  ↓
LLM when reasoning/tool selection is needed
```

This reduces latency and allows a very small model to be useful.

## Skills

Capabilities are described using `SKILL.md`.

Example structure:

```text
skills/
├── filesystem/
│   ├── open_folder/
│   │   ├── SKILL.md
│   │   └── tool.py
│   ├── create_folder/
│   │   ├── SKILL.md
│   │   └── tool.py
│   └── search_files/
│       ├── SKILL.md
│       └── tool.py
└── applications/
    └── open_app/
        ├── SKILL.md
        └── tool.py
```

The LLM should select from registered skills rather than being given unrestricted access to the operating system.

## Safety Model

The LLM should **not** directly generate arbitrary PowerShell and have it executed automatically.

Use:

```text
LLM
 ↓
Structured tool call
 ↓
Tool allowlist
 ↓
Argument validation
 ↓
Permission / confirmation
 ↓
Execution
```

Destructive operations such as deleting files should require explicit confirmation.

## Camera Transport

### Wi-Fi

The first mobile-camera implementation should use the local Wi-Fi network:

```text
Phone ───── Wi-Fi ───── Desktop
```

This makes early development relatively simple and keeps the camera data local.

### USB

USB can be investigated later when lower latency or more reliable bandwidth is needed.

The application should use a common camera interface so that the vision engine does not care whether the frames come from a webcam, Wi-Fi phone, or USB phone.

## Suggested Technology Direction

- **Python** — desktop orchestration and vision integration.
- **OpenCV** — image processing and projector/camera calibration.
- **Hand-tracking model/library** — fingertip and hand landmarks.
- **Existing small local LLM** — agent reasoning and skill selection.
- **JSON** — structured events and tool calls.
- **PowerShell / Python / OS APIs** — controlled desktop tools.
- **Mobile application** — camera capture and local streaming.
- **Projector** — visual output and interface.

The exact libraries are intentionally left replaceable during the prototype stage.

## Repository Documents

- [`specification.md`](specification.md) — system requirements and architecture.
- [`implementation-plan.md`](implementation-plan.md) — technical implementation sequence.
- [`todo.md`](todo.md) — task checklist.
- [`roadmap.md`](roadmap.md) — project milestones and long-term direction.
- [`PRODUCTION.md`](PRODUCTION.md) — release gate, deployment controls, and operational limitations.
- [`V2_PACKAGING.md`](V2_PACKAGING.md) — Electron desktop bundling, mobile pairing, and no-download model delivery.

## First Prototype

The recommended first demonstration is deliberately small:

1. Connect a projector.
2. Display a folder icon.
3. Use a webcam initially.
4. Detect a fingertip.
5. Calibrate camera → projector coordinates.
6. Detect a finger touching the folder.
7. Trigger `open_folder`.
8. Validate the requested path.
9. Open the folder.
10. Display success on the projector.

After this works, replace the webcam with the mobile phone.

## Development Philosophy

**Do not build everything at once.**

First prove:

```text
Hand → Projected UI
```

Then prove:

```text
Projected UI → Windows
```

Then prove:

```text
Event → Small LLM → Skill → Tool
```

Then combine:

```text
Phone Camera
      ↓
Vision
      ↓
Projected Interaction
      ↓
Small LLM Agent
      ↓
Skills
      ↓
Validated Tools
      ↓
Windows
```

## Status

**Stage:** Architecture / early implementation planning

**V1 objective:** A working projected folder interaction controlled by a hand, with the phone eventually serving as the camera sensor and a small local LLM providing optional agent/tool intelligence.

## Phase 1 Prototype

The first implementation milestone is available in `src/projected_ai_interface`. It provides a borderless Tk projected UI with a logical 4×3 test grid, responsive folder targets, hover highlighting, click/touch feedback, display selection, and a headless dry-run mode for machines without a projector or graphical session.

```bash
python3 -m pip install -e '.[test]'
python3 -m pytest -q
PYTHONPATH=src python3 -m projected_ai_interface.cli --dry-run
PYTHONPATH=src python3 -m projected_ai_interface.cli
```

Use `--display N` to select a detected display. When no display-detection library or graphical display is available, `--dry-run` uses a configurable fallback size (`--width` and `--height`) and prints the complete UI model as JSON. Press **Escape** to close the fullscreen UI.

## Phase 2 Camera Prototype

Phase 2 adds a transport-neutral `CameraSource` interface, an OpenCV webcam source, capture metrics, bounded reconnect support, and a deterministic synthetic source for testing without a camera. Install webcam support with `python3 -m pip install -e '.[camera]'`, then run `projected-camera --device 0 --frames 30`. For a headless smoke test, run `projected-camera --synthetic --frames 30`.

## Phase 3 Android Camera Client

The Android-first camera client lives in `mobile-camera/`. It is written with React Native primitives rendered through React Native Web so the same UI can be exercised in a browser first, then bundled into a Capacitor Android WebView. It requests camera permission, previews the camera, discovers nearby desktop receivers through Android NSD, presents them as radar-style device cards, and sends binary JPEG frames after selection. No API or IP address is typed into the mobile UI.

```bash
cd mobile-camera
npm install
npm run build                 # browser/WebView production validation
npm run dev                   # browser-first camera test
npx cap sync android          # copy the validated web bundle
cd android && ./gradlew assembleDebug
```

The desktop advertises itself with `projected-discovery --name "Projected AI Desktop" --port 8765`, using `_projected-ai._tcp.local.`. The Capacitor project targets Android SDK 35 and includes the camera and Internet permissions. APK compilation requires a full JDK with `javac`, Android SDK platform/build tools, and `ANDROID_HOME` or `ANDROID_SDK_ROOT`; see [`mobile-camera/PROTOCOL.md`](mobile-camera/PROTOCOL.md) for the discovery protocol and build prerequisites.

### Desktop application phases

The desktop is not a separate late-stage product. It is built in layers: **Phase 1** is the projector UI, **Phase 2** is the camera abstraction and webcam path, **Phase 3** adds the desktop discovery advertisement and phone transport contract, **Phase 4** adds hand/fingertip vision, **Phases 5–6** add calibration and deterministic interaction, and **Phase 10** packages these components into the complete folder-touch desktop application. Phase 4 can be exercised headlessly with `projected-vision --demo`; live MediaPipe processing is available with `python3 -m pip install -e '.[vision]'`.

Phase 5 adds four-point camera-to-projector homography calibration and JSON profile persistence. Run `projected-calibration --demo` to create a deterministic `.calibration/demo.json` profile and verify the center-point mapping. The live calibration UI will use the same profile API when the camera and projector interaction loop is connected.

Phase 6 adds the deterministic interaction engine. It maps camera points through a calibration profile, hit-tests projected folders/buttons, debounces touches, rejects low-confidence input, emits touch/release/drag events, and writes privacy-preserving JSONL event logs. Run `projected-interaction --demo` for a headless check. This layer remains independent of the LLM.

Phase 7 adds the documented skill system. Each capability is defined by a `skills/**/SKILL.md` file and connected only to an explicitly registered Python tool. Run `projected-skills` to inspect the loaded registry. Skills now cover opening/listing folders, creating folders, searching files, moving/copying files, and validating an allowlisted application intent. Delete is confirmation-gated, paths are sandbox-checked, existing destinations are never overwritten, and arbitrary LLM shell text is not accepted or executed.

Phase 8 adds the local-agent contract in `src/projected_ai_interface/agent.py`. The default standalone backend uses ONNX Runtime and a small local action model; it does not require Ollama, a model server, or Torch. An OpenAI-compatible endpoint remains an optional backend for later language-model experiments. The runtime loads `SKILL.md` context, receives structured interaction events, validates only documented and registered tools, retries malformed responses, and records inference latency. Run `projected-agent` to inspect the generated skill/tool contract. A model is never required for the deterministic test suite.

The local provider can be configured without code changes through `PROJECTED_AGENT_BACKEND=onnx`, `PROJECTED_AGENT_ONNX_MODEL`, and `PROJECTED_AGENT_ONNX_LABELS`. The verified causal SmolLM path uses `PROJECTED_AGENT_BACKEND=smollm`, `PROJECTED_AGENT_ONNX_MODEL`, `PROJECTED_AGENT_ONNX_TOKENIZER`, and optionally `PROJECTED_AGENT_ONNX_MAX_NEW_TOKENS`; it performs the same KV-cache generation as the verification runner and returns generated text to the runtime. The optional server backend uses `PROJECTED_AGENT_BASE_URL`, `PROJECTED_AGENT_MODEL`, and `PROJECTED_AGENT_API_KEY`; all backends support `PROJECTED_AGENT_TIMEOUT` and `PROJECTED_AGENT_RETRIES`. The corresponding `projected-agent` CLI options expose these choices. Provider failures and malformed responses are returned as structured status values; the runtime never sends camera frames to the model. The classifier ONNX contract accepts an `input_ids` tensor shaped `[1, sequence]` and returns `[1, label_count]` logits, with labels mapped to the strict `{tool, arguments}` action format. Causal text responses may be wrapped in a Markdown JSON fence; the runtime removes that fence before applying exact-shape and tool allowlist validation.

The real text-generation verification runner is `scripts/verify_smollm_onnx.py`. It has been tested with the public [`onnx-community/SmolLM-135M-Instruct-ONNX`](https://huggingface.co/onnx-community/SmolLM-135M-Instruct-ONNX) export, which is a 135M-parameter SmolLM model. After installing `python3 -m pip install -e '.[onnx]'` and downloading the model's `onnx/model_q4.onnx` and `tokenizer.json` files, run `python3 scripts/verify_smollm_onnx.py --model /path/to/model_q4.onnx --tokenizer /path/to/tokenizer.json`. The runner verifies the 30-layer KV-cache graph, performs autoregressive CPU generation, decodes the output, and reports latency and generated text.

The complete visual handoff is exercised by `scripts/test_vision_to_smollm_e2e.py`: a vision model emits only a click/label event, the real local SmolLM-135M provider receives that event plus the loaded `SKILL.md` context, and `AgentRuntime` validates the resulting `open_folder` action before the sandboxed tool runs. Because a 135M model can produce explanatory prose or punctuation artifacts instead of strict JSON, its adapter has a narrow recovery path that requires one registered `open_folder` tool and one explicitly approved runtime path; it never invents a filesystem path.

The live mobile protocol is exercised by `scripts/test_live_mobile_to_tool_e2e.py`. It sends a JPEG over the same `/frames` WebSocket endpoint used by the Capacitor camera app, verifies frame decoding and mDNS receiver readiness, runs vision inference, invokes the bundled SmolLM action provider, and asserts the final sandboxed folder action.

Phase 9 adds a bounded `ToolRegistry` execution layer. Only registered Python callables are dispatchable, tool arguments are signature-checked, execution can be timed out, and every call is recorded with its result and elapsed time. Filesystem tools continue to resolve paths inside an explicit sandbox, reject overwrites, and require `confirmed=true` for deletion. Arbitrary model-generated shell text is not accepted.

Phase 10 now includes `NetworkCameraSource`, a queue-backed desktop WebSocket receiver for the mobile client's binary JPEG messages at `/frames`. It can be exercised with `projected-camera --network --port 8765` and remains compatible with the existing synchronous `CameraSource` interface. The receiver bounds memory, drops old frames when vision is slow, ignores text messages, rejects invalid payloads, and reports receive/drop/decode state without storing camera frames. `DesktopInteractionPipeline` provides a deterministic hardware-free composition from calibrated fingertip observations through touch debounce, agent selection, and validated tool results.

## Team

**Ethco Coder & Natnael Ermiyas**

This project is intended to evolve experimentally. Architecture and technology choices may change as measurements from the prototype reveal better approaches.
