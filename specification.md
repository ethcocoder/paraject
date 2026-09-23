# Projected AI Interface — Specification

## Project Identity

**Working concept:** Projected AI Interface  
**Team:** Ethco Coder and Natnael Ermiyas  
**Primary platform:** Desktop computer + projector + mobile phone camera  
**AI approach:** Existing small local LLM + system prompt + `SKILL.md`; no fine-tuning required for the initial system.

## 1. Vision

Create a physical computing interface where a projector displays an interactive computer environment on a surface, a mobile phone provides visual sensing, and an AI agent connects physical interactions to computer actions.

The system should feel like touching projected computer objects directly.

## 2. Goals

### Primary goals
1. Use a phone as the camera sensor.
2. Transfer camera data to a desktop over local Wi-Fi and/or USB.
3. Detect hands and fingertips.
4. Map camera coordinates to projector coordinates.
5. Detect interaction with projected UI elements.
6. Control the desktop through safe tools.
7. Use an existing small LLM as an agent.
8. Describe capabilities with `SKILL.md`.
9. Keep core interaction fast and deterministic.
10. Keep processing local where practical.

### Non-goals for V1
- Training a new LLM.
- Fine-tuning the LLM.
- Making the LLM directly interpret raw camera frames.
- Giving the LLM unrestricted shell access.
- Building a general-purpose humanoid vision system.

## 3. Functional Requirements

### FR-01 Camera
The system shall accept frames from a camera source.

### FR-02 Phone camera
The system shall support a mobile phone camera as a camera source through a network connection. USB support is a secondary transport.

### FR-03 Camera abstraction
The desktop application shall treat webcam, network phone camera, and future camera sources through a common interface.

### FR-04 Hand detection
The vision subsystem shall detect a user's hand and fingertip position with confidence information.

### FR-05 Calibration
The system shall provide a calibration process that maps camera coordinates to projector coordinates.

### FR-06 Interaction detection
The system shall identify interactions with projected UI objects.

### FR-07 UI hit testing
The interaction engine shall determine the projected object associated with a fingertip coordinate.

### FR-08 Event protocol
The system shall represent interactions as structured events.

Example:

```json
{
  "event": "touch",
  "object_type": "folder",
  "object_id": "documents",
  "position": {"x": 712, "y": 421},
  "confidence": 0.96
}
```

### FR-09 LLM agent
The system shall support an existing small local LLM.

### FR-10 Skills
Each agent capability shall be described through a `SKILL.md` document and implemented by a controlled tool.

### FR-11 Tool calls
The LLM shall produce structured tool calls.

Example:

```json
{
  "tool": "open_folder",
  "arguments": {
    "path": "C:\Users\User\Documents"
  }
}
```

### FR-12 Tool validation
The application shall validate tool names and arguments before execution.

### FR-13 Feedback
The projected UI shall provide feedback for recognized interaction, processing, success, and failure.

### FR-14 Logging
The system shall log camera/interaction events, selected tools, validation results, execution results, and errors without unnecessarily storing sensitive camera data.

## 4. Non-Functional Requirements

### Performance
- Basic touch feedback should target less than 150 ms end-to-end where hardware permits.
- Vision processing should be asynchronous from slow LLM operations.
- Network video should tolerate temporary packet loss gracefully.

### Reliability
- Lost phone connection must be detected.
- Low-confidence hand detections must not trigger dangerous actions.
- Repeated accidental touches should be debounced.

### Security
- Never execute arbitrary generated shell commands without validation.
- Destructive filesystem operations should require confirmation.
- Prefer an allowlist of tools.
- Keep network camera access restricted to the local network during development.

### Privacy
- Camera frames should remain local unless the user explicitly chooses otherwise.
- Do not upload camera footage by default.

## 5. Component Specification

### Mobile Camera App
Responsibilities:
- Capture camera frames.
- Encode/stream frames.
- Provide connection information.
- Show connection status.
- Optionally expose resolution and FPS controls.

### Desktop Receiver
Responsibilities:
- Receive frames.
- Decode frames.
- Monitor latency and dropped frames.
- Expose frames to the vision subsystem.

### Vision Engine
Responsibilities:
- Hand detection.
- Fingertip tracking.
- Gesture detection.
- Confidence scoring.

### Calibration Engine
Responsibilities:
- Project calibration points.
- Collect corresponding camera coordinates.
- Calculate transformation.
- Save/load calibration.

### Interaction Engine
Responsibilities:
- Transform coordinates.
- Hit-test projected UI.
- Debounce interactions.
- Emit structured events.

### Projected UI
Responsibilities:
- Render interface.
- Show interaction targets.
- Show fingertip/hover feedback.
- Display execution results.

### Agent Runtime
Responsibilities:
- Build context for the LLM.
- Load system prompt.
- Load relevant skills.
- Ask the LLM for structured actions.
- Parse and validate outputs.

### Tool Runtime
Responsibilities:
- Execute approved operations.
- Validate arguments.
- Request confirmation when needed.
- Return structured results.

## 6. Skill Specification

Each skill should contain:
- Name.
- Purpose.
- Preconditions.
- Inputs.
- Output.
- Safety rules.
- Example tool call.

Suggested layout:

```text
skills/
  filesystem/
    open_folder/
      SKILL.md
      tool.py
    create_folder/
      SKILL.md
      tool.py
  applications/
    open_app/
      SKILL.md
      tool.py
```

## 7. Example Interaction

User touches projected folder:

```text
VISION
  fingertip = (840, 510)

CALIBRATION
  projector = (620, 330)

HIT TEST
  object = Documents

EVENT
  TOUCH(Documents)

AGENT
  select open_folder skill

TOOL
  open_folder(path)

VALIDATION
  allowed

EXECUTION
  Windows opens folder

UI
  show success
```

## 8. Failure Behavior

If camera unavailable:
- Show camera disconnected state.

If calibration is missing:
- Disable touch actions and request calibration.

If vision confidence is low:
- Ignore interaction.

If LLM output is invalid:
- Reject and retry with constrained context.

If tool arguments are unsafe:
- Reject.

If a destructive operation is requested:
- Require explicit user confirmation.

## 9. Extensibility

Future capabilities may include:
- Voice commands.
- Multi-hand interaction.
- Object recognition.
- Projected keyboard.
- File drag-and-drop.
- Browser interaction.
- Application-specific skills.
- Multi-device sensors.
- Multiple projectors/cameras.
