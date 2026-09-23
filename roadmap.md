# Projected AI Interface — Roadmap

## Project Team

**Ethco Coder**  
**Natnael Ermiyas**

## Long-Term Vision

Build a local, intelligent projected computing environment where physical interaction with projected objects becomes a direct interface to the computer, supported by computer vision and a small tool-using LLM.

The goal is not to make the LLM perform every task. Fast deterministic interaction should be handled by the interaction engine, while the LLM handles interpretation, planning, and skill selection.

---

## Milestone 1 — Proof of Concept

### Objective
Prove that a hand can interact with a projected object.

### Deliverables
- Projector UI.
- Webcam.
- Hand tracking.
- Fingertip detection.
- Manual camera/projector calibration.
- Touch detection.
- Projected feedback.

### Success criterion

```text
Finger touches projected square
        ↓
System recognizes touch
        ↓
Projected square changes state
```

---

## Milestone 2 — Real Computer Interaction

### Objective
Make projected UI control the desktop.

### Deliverables
- Folder/file UI.
- Structured interaction events.
- Safe desktop tools.
- Open-folder skill.
- Tool validation.

### Success criterion

```text
Touch projected Documents
        ↓
open_folder tool
        ↓
Windows opens Documents
```

---

## Milestone 3 — Local Small-LLM Agent

### Objective
Introduce an existing small LLM without fine-tuning.

### Deliverables
- Local LLM runtime.
- System prompt.
- `SKILL.md` format.
- Skill loader.
- Structured tool calls.
- Agent-to-tool execution.

### Success criterion

The LLM can receive a structured event or natural-language request and select an available skill correctly.

---

## Milestone 4 — Phone as Camera

### Objective
Replace the webcam with a mobile phone.

### Deliverables
- Mobile camera app/prototype.
- Wi-Fi video stream.
- Desktop receiver.
- Camera abstraction.
- Connection monitoring.

### Success criterion

```text
Phone camera
    ↓ Wi-Fi
Desktop
    ↓
Vision system
```

The user can move their hand in front of the phone and see the tracking result on the desktop/projector.

---

## Milestone 5 — Full Integrated Prototype

### Objective
Combine all major components.

### Deliverables

```text
Phone
  ↓
Local network
  ↓
Desktop receiver
  ↓
Vision
  ↓
Calibration
  ↓
Projected UI
  ↓
Interaction event
  ↓
Small LLM
  ↓
SKILL.md
  ↓
Validated tool
  ↓
Windows
  ↓
Projector feedback
```

### Success criterion

A user can physically touch a projected folder and cause the correct computer action.

---

## Milestone 6 — Advanced Physical UI

Potential features:
- Drag files by hand.
- Swipe between projected screens.
- Multi-touch.
- Gesture shortcuts.
- Projected keyboard.
- Context menus.
- Physical object tracking.
- Hand + voice commands.

---

## Milestone 7 — AI Workspace

The system evolves from a projected file browser into an AI workspace.

Example:

```text
User points at a group of files
        +
User says:
"Put these into my project folder."
        ↓
Vision identifies selection
        ↓
LLM interprets request
        ↓
move_file skill
        ↓
Validation
        ↓
Execution
        ↓
Projected confirmation
```

---

## Milestone 8 — Research / Novelty

Once the prototype works, investigate:
- Latency compared with conventional mouse/touch interfaces.
- Reliability of phone-camera tracking.
- Robustness of projector/camera calibration.
- Small-LLM tool-selection accuracy.
- Skill-document formats for tiny local agents.
- Human-computer interaction usability.
- Privacy benefits of local processing.
- Comparison with existing projected-interaction systems.

This phase is where the team can determine whether the exact architecture or interaction technique offers a meaningful research contribution.

---

## Roadmap Principles

1. Build the physical interaction first.
2. Keep the LLM out of the raw vision loop.
3. Use existing models before considering training.
4. Keep skills modular.
5. Make tools deterministic and validated.
6. Keep latency-sensitive operations independent of the LLM.
7. Keep camera transport replaceable.
8. Prefer local processing.
9. Measure performance rather than assuming it.
10. Start with a small working demo and expand.
