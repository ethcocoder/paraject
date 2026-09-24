# v2 Packaging and Installation

## Architecture

The v2 release uses two model stages. The camera/vision stage produces a structured event such as `{ "clicked": true, "target_label": "Documents", "confidence": 0.94 }`. The local SmolLM-135M stage receives that event and the documented skills, then selects a safe action. `AgentRuntime`, `ToolRegistry`, and `PathSandbox` remain the final authority for execution.

The Electron desktop package contains the React UI, a bundled Python backend executable, and the pinned SmolLM ONNX model plus tokenizer. The backend now owns the live WebSocket receiver on port `8765`, advertises `_projected-ai._tcp.local.`, decodes mobile JPEG frames, invokes the configured vision provider, passes the structured event through SmolLM and `AgentRuntime`, and executes only sandboxed tools. The mobile application contains only camera capture and local-network discovery; it does not download or run the model.

For live vision inference, configure `OPENAI_API_KEY` and, when needed, `OPENAI_BASE_URL` in the desktop process environment. The vision model is accessed remotely; the SmolLM action model is bundled locally. If no vision key is configured, the backend still exposes health status but intentionally does not advertise an active camera-processing session.

## Build the desktop installer

Provide the model assets locally before building:

```text
.models/smollm-135m/model_q4.onnx
.models/smollm-135m/tokenizer.json
```

Then build from the repository root:

```bash
cd desktop-electron
npm install
npm run typecheck
npm run build:web
npm run dist
```

`npm run dist` creates the Python backend in a packaging virtual environment, verifies that model assets exist, and passes them to electron-builder as extra resources. There is no model download step in the installed app. The installer outputs are written under `desktop-electron/release/`.

The live desktop flow is verified with:

```bash
PYTHONPATH=src python3 scripts/test_live_mobile_to_tool_e2e.py
```

That test sends the generated JPEG through the same binary WebSocket protocol used by the mobile client and verifies the final sandboxed `open_folder` result.

## Mobile build

The existing Capacitor app discovers the desktop receiver through the `_projected-ai._tcp.local.` service, requests camera permission, and streams JPEG frames to the selected local endpoint:

```bash
cd mobile-camera
npm install
npm run build
npm run cap:sync
cd android
./gradlew assembleDebug
```

APK packaging requires a JDK with `javac`, Android SDK platform/build-tools, and `ANDROID_HOME` (or `android/local.properties` with `sdk.dir`). The repository can validate the web build and Capacitor sync without the SDK, but a CI runner or Android workstation must supply the SDK to produce the final APK.

Install the generated Android APK on the phone, start the desktop app on the same trusted Wi-Fi network, scan from the phone, select the discovered desktop, and start the camera. The phone must never receive the model files.

## Network and production requirements

The desktop receiver must bind only to the intended local-network interface, use bounded queues, and be isolated from untrusted networks. Before a public or shared-network deployment, add transport authentication and TLS. The v2 installer currently packages the local backend and health endpoint; camera processing and target-workstation hardware validation remain required release checks.

## Artifact verification

Record the model and tokenizer SHA-256 values from `packaging/backend-dist/MODEL_SHA256SUMS.txt` in the release record. Do not commit the model binaries or generated installers to source control. Distribute them through the signed desktop installer or a controlled artifact repository.
