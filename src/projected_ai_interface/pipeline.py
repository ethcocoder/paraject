"""Deterministic desktop composition for synthetic and hardware-free integration tests."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .agent import AgentResult, AgentRuntime
from .interaction import InteractionEngine, InteractionEvent


@dataclass(frozen=True)
class PipelineResult:
    events: tuple[InteractionEvent, ...]
    agent_result: AgentResult | None
    feedback: str


class DesktopInteractionPipeline:
    """Connect deterministic interaction events to the safe agent runtime.

    Camera transport and vision remain injectable upstream. This class consumes
    camera-space fingertip observations, lets the interaction engine perform all
    touch/debounce decisions, then invokes the agent only for a stable touch.
    """

    def __init__(self, interaction: InteractionEngine, agent: AgentRuntime) -> None:
        self.interaction = interaction
        self.agent = agent

    def process(
        self,
        camera_point: tuple[float, float] | None,
        confidence: float,
        contact: str,
        *,
        timestamp: float | None = None,
    ) -> PipelineResult:
        events = tuple(self.interaction.process(camera_point, confidence, contact, timestamp=timestamp))
        touch = next((event for event in events if event.event == "touch"), None)
        if touch is None:
            return PipelineResult(events, None, "idle" if not events else events[-1].event)
        agent_result = self.agent.run(
            f"Open the touched projected folder {touch.object_id}",
            event=touch.to_dict(),
        )
        return PipelineResult(events, agent_result, "success" if agent_result.ok else "failure")

    def process_observations(self, observations: list[dict[str, Any]]) -> list[PipelineResult]:
        """Run a deterministic sequence of vision-like observations."""
        return [
            self.process(
                observation.get("camera_point"),
                float(observation.get("confidence", 0.0)),
                str(observation.get("contact", "none")),
                timestamp=observation.get("timestamp"),
            )
            for observation in observations
        ]
