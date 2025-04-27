"""Define the state structures for the agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing_extensions import Annotated
from langgraph.graph import add_messages
from langchain_core.messages import AnyMessage

@dataclass
class State:
    action: str
    messages: Annotated[list[AnyMessage], add_messages]

    # receipt_agent
    receipt_image: str = field(default_factory=lambda: "")
    receipt_json: str = field(default_factory=lambda: "")