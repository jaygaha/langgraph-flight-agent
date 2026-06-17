"""
Understanding and Defining Agent State in LangGraph

In LangGraph, the State acts as the central shared memory of anr agent. Architecturally, LangGraph treats agent
workflows as state machines.

What it is: A structured Python object (often a TypedDict or a Pydantic model) that tracks the agent's current knowledge.

Why it matters: Every node (function) in your graph reads from this state and returns updates to it. Without
a clearly defined state, your agent cannot pass information like flight options or user preferences from one step to
the next.
"""
from typing import TypedDict, List, Dict, Any, Annotated, Optional

turns: int = 0


def replace_list(current: list, update: list) -> list:
    """Replace old flight results with new ones on every search."""
    return update

class AgentState(TypedDict):
    # The raw text input from the user
    user_request: str

    # Structured key-value pairs for constraints (e.g., budget, dates)
    constraints: Dict[str, Any]

    flight_options: Annotated[List[Dict[str, Any]], replace_list]

    # Tracks what the agent is currently doing
    current_status: str

    # Track how many times the graph has looped
    turns: int

    booked_flight: Optional[Dict[str, Any]]
