# Projected AI Interface — Implementation Plan

## Project Team
- Ethco Coder
- Natnael Ermiyas

## 1. Purpose

Build a local, projector-based computer interface in which a mobile phone acts as a camera sensor, a desktop application receives the camera stream over a local network or USB, computer vision detects hand/finger interaction, and an existing small local LLM (for example TinyLlama-class models) acts as a tool-using agent through a system prompt and `SKILL.md` files.

The project does **not** require fine-tuning the LLM.

## 2. Core Architecture

```text
Mobile Phone Camera
        |
   Wi-Fi / USB
        |
        v
Desktop Camera Receiver
        |
        v
Computer Vision / Hand Tracking
        |
        v
Interaction + Coordinate Mapping
        |
        +----> Basic UI interaction
        |
        v
Structured Event
        |
        v
Small Local LLM
(System Prompt + Skills)
        |
        v
Tool Router / Validation
        |
        +----> PowerShell
        +----> CMD
        +----> Python / OS APIs
        |
        v
Windows Computer
        |
        v
Projector / Projected UI
```

## 3. Implementation Phases

### Phase 0 — Repository and development environment
- Create the repository structure.
- Define Python environment and dependency management.
- Establish coding conventions and logging.
- Create a minimal desktop application shell.

### Phase 1 — Projector display
- Connect a projector as a secondary display.
- Create a borderless projected UI.
- Render folders, files, buttons, and visual feedback.
- Define a logical projector coordinate system.

### Phase 2 — Camera input
- Implement a camera abstraction.
- Support a normal webcam first.
- Add phone camera input later.
- Keep the vision layer independent from the camera transport.

### Phase 3 — Phone camera transport
- Build a mobile camera application/prototype.
- Stream frames over a local Wi-Fi network.
- Investigate USB transport as a lower-latency option.
- Add connection status and frame-rate monitoring.
- Ensure the desktop application can switch between webcam and phone source.

### Phase 4 — Hand and finger detection
- Detect hand landmarks.
- Identify fingertip position.
- Estimate gestures such as touch, press, drag, and swipe.
- Filter noisy detections.
- Add confidence thresholds.

### Phase 5 — Camera/projector calibration
- Calibrate the relationship between camera coordinates and projector coordinates.
- Use a four-point calibration process.
- Implement perspective/homography transformation.
- Store calibration data locally.
- Provide a recalibration UI.

### Phase 6 — Projected interaction engine
- Map fingertip coordinates into projected UI coordinates.
- Determine which projected object is under the fingertip.
- Generate events such as:
  - `touch`
  - `press`
  - `release`
  - `drag_start`
  - `drag`
  - `drag_end`
  - `swipe`
- Keep basic interactions deterministic and independent of the LLM.

### Phase 7 — Agent and skill system
- Integrate an existing small local LLM.
- Define a strict system prompt.
- Create a `skills/` directory.
- Define each capability using `SKILL.md`.
- Convert interaction events into structured agent input.
- Require structured tool calls rather than arbitrary shell execution.

### Phase 8 — Desktop tools
Initial skills:
- Open folder.
- List folder.
- Open application.
- Create folder.
- Move file.
- Copy file.
- Delete file with confirmation.
- Search files.
- Launch approved PowerShell commands.

### Phase 9 — Safety and validation
- Validate all tool arguments.
- Restrict filesystem operations to permitted paths where appropriate.
- Require confirmation for destructive actions.
- Log every tool request and result.
- Never execute arbitrary LLM-generated shell text directly.

### Phase 10 — End-to-end prototype
Demonstrate:

```text
Hand touches projected "Documents"
        ↓
Camera detects fingertip
        ↓
Coordinate mapping identifies Documents
        ↓
Event = TOUCH(Documents)
        ↓
Agent/interaction layer selects open_folder
        ↓
Validated tool executes
        ↓
Documents opens
        ↓
Projector updates UI
```

## 4. Recommended Development Order

1. Projector UI
2. Webcam input
3. Hand tracking
4. Calibration
5. Touch detection
6. Desktop file tools
7. Skill format
8. Local LLM integration
9. Phone camera streaming
10. Full integration

This order minimizes debugging complexity.

## 5. Technology Direction

Suggested starting stack:
- Python for orchestration and computer vision.
- OpenCV for image processing and calibration.
- A hand-landmark model/library for hand tracking.
- Local inference runtime compatible with the selected small LLM.
- JSON for structured events/tool calls.
- PowerShell and/or Python for desktop tools.
- A lightweight desktop UI framework suitable for fullscreen projected rendering.
- Android/iOS camera app or existing phone-camera streaming mechanism for the first mobile prototype.

Technology choices should remain modular so components can be replaced later.

## 6. Performance Targets

Initial prototype targets:
- Camera input: 20–30 FPS where hardware permits.
- Interaction latency: target below 150 ms for basic touch feedback.
- Basic touch handling should not depend on LLM inference.
- LLM operations may have higher latency but should run asynchronously.
- Prefer local processing to minimize privacy and network dependency.

## 7. Testing Strategy

Test each layer independently:
- Camera stream test.
- Hand detection test.
- Calibration test.
- Touch classification test.
- UI hit-test test.
- Tool validation test.
- LLM structured-output test.
- End-to-end test.

Record latency and failure cases at each layer.

## 8. Definition of Done for V1

V1 is complete when:
- A phone can provide camera frames to the desktop.
- A hand/fingertip can be tracked.
- Camera and projector coordinates can be calibrated.
- A user can touch a projected folder.
- The desktop recognizes the intended folder.
- The folder can be opened safely.
- The LLM can use at least one documented skill.
- Tool execution is validated and logged.
