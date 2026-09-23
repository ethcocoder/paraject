# Projected AI Interface — TODO

## Legend

- [ ] Not started
- [~] In progress
- [x] Completed
- [!] Needs decision/investigation

## Phase 0 — Foundation

- [ ] Create repository.
- [ ] Create Python virtual environment.
- [ ] Define project package structure.
- [ ] Add logging system.
- [ ] Add configuration file.
- [ ] Add `.gitignore`.
- [ ] Add basic README.
- [ ] Decide license.
- [ ] Define minimum desktop hardware requirements.

## Phase 1 — Projector

- [x] Detect projector/secondary display.
- [x] Create fullscreen projected window.
- [x] Render test grid.
- [x] Render projected folder icons.
- [x] Add hover/highlight state.
- [x] Add visual touch feedback.

## Phase 2 — Camera

- [x] Implement generic `CameraSource`.
- [x] Add webcam source.
- [x] Measure FPS.
- [x] Measure frame latency.
- [x] Add camera reconnect behavior.

## Phase 3 — Phone Camera

- [x] Choose Android first target.
- [x] Create minimal React Native Web + Capacitor camera-streaming app.
- [x] Implement desktop mDNS/DNS-SD advertisement.
- [x] Implement Android NSD device detection and selection.
- [x] Stream JPEG frames to desktop.
- [x] Add compression/resolution controls.
- [x] Add connection monitoring.
- [ ] Test Wi-Fi latency.
- [ ] Investigate USB transport.
- [ ] Add USB mode if practical.

## Phase 4 — Vision

- [x] Select hand-tracking library/model: MediaPipe adapter.
- [x] Detect hand landmarks.
- [x] Track index fingertip.
- [x] Add confidence threshold.
- [x] Add temporal smoothing.
- [x] Detect touch/hover.
- [ ] Detect drag.
- [ ] Detect swipe.
- [ ] Test different lighting conditions.

## Phase 5 — Calibration

- [x] Display four calibration points.
- [x] Capture corresponding camera coordinates.
- [x] Calculate homography.
- [x] Save calibration profile.
- [x] Load calibration on startup.
- [x] Add recalibration command.
- [ ] Test different projector angles.

## Phase 6 — Interaction Engine

- [x] Implement coordinate transform.
- [x] Implement UI hit testing.
- [x] Implement event schema.
- [x] Implement touch debounce.
- [x] Implement event confidence.
- [x] Add event logger.
- [x] Test folder touch.
- [x] Test button touch.
- [x] Test drag operation.

## Phase 7 — Skills

- [x] Define `SKILL.md` format.
- [x] Build skill loader.
- [x] Build skill registry.
- [x] Build tool registry.
- [x] Create `open_folder` skill.
- [x] Create `list_folder` skill.
- [x] Create `open_app` skill.
- [x] Create `create_folder` skill.
- [x] Create `search_files` skill.
- [x] Create `move_file` skill.
- [x] Create `copy_file` skill.
- [x] Add destructive-operation confirmation.

## Phase 8 — LLM

- [x] Select initial existing small LLM: OpenAI-compatible TinyLlama-class endpoint.
- [ ] Run model locally.
- [x] Define system prompt.
- [x] Define structured tool-call format.
- [x] Feed structured interaction events to model.
- [x] Load relevant `SKILL.md` content.
- [x] Validate model output.
- [x] Add retry behavior.
- [x] Measure inference latency.
- [x] Test model with simple commands.
- [ ] Test model with ambiguous commands.

## Phase 9 — Tool Safety

- [ ] Build tool validation layer.
- [ ] Allowlist tools.
- [ ] Validate filesystem paths.
- [ ] Prevent path traversal.
- [ ] Separate read and write permissions.
- [ ] Add confirmation for delete.
- [ ] Add execution timeout.
- [ ] Log tool execution.
- [ ] Never directly execute arbitrary LLM shell text.

## Phase 10 — Integration

- [ ] Connect phone camera to vision.
- [ ] Connect vision to calibration.
- [ ] Connect calibration to projected UI.
- [ ] Connect events to agent runtime.
- [ ] Connect agent to skills.
- [ ] Connect skills to tools.
- [ ] Connect tools to Windows.
- [ ] Return tool results to UI.
- [ ] Build complete folder-touch demonstration.

## Phase 11 — Testing

- [ ] Test bright lighting.
- [ ] Test low lighting.
- [ ] Test different camera angles.
- [ ] Test different projector angles.
- [ ] Test network interruption.
- [ ] Test camera disconnect.
- [ ] Test false touch.
- [ ] Test slow LLM.
- [ ] Test malformed LLM output.
- [ ] Test unsafe tool call.
- [ ] Test destructive command confirmation.

## V1 Demo Checklist

- [ ] Phone is camera.
- [ ] Desktop receives phone video.
- [ ] Projector displays UI.
- [ ] Hand is detected.
- [ ] Fingertip is tracked.
- [ ] Calibration works.
- [ ] Projected folder can be touched.
- [ ] Folder action is generated.
- [ ] Tool is validated.
- [ ] Folder opens.
- [ ] Projected UI shows result.

## Future Ideas

- [ ] Voice + projected interaction.
- [ ] Multiple phones/cameras.
- [ ] Gesture-controlled window management.
- [ ] Projected keyboard.
- [ ] Natural-language projected workspace.
- [ ] Multi-agent skills.
- [ ] Automatic skill discovery.
- [ ] Sensor fusion.
