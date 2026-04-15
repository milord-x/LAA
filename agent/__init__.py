"""
Agent package — autonomous decision layer for the LAA pipeline.

Sits between ASR/processing and outputs (subtitles, avatar, summary).
Every segment is evaluated by AgentPolicy and routed via AgentController.
"""

from agent.decision import AgentDecision
from agent.policy import AgentPolicy
from agent.controller import AgentController, agent_controller

__all__ = ["AgentDecision", "AgentPolicy", "AgentController", "agent_controller"]
