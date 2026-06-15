"""
using LangGraph's StateGraph.

Architectural Concept: StateGraph is the blueprint of our agent. We initialize it with our AgentState layout,
add our functions as Nodes, and connect them using Edges.

Edges: Define the control flow. A normal edge simply points from Node A straight to Node B.

---

State Persistence with Checkpointers

In production agent architectures, workflows often need to pause, recover from errors, or handle multi-turn
conversations over days. To achieve this, LangGraph uses Checkpointers.

Architectural Concept: A checkpointer automatically saves a snapshot of the AgentState after every single node execution.

Why it matters: It gives our agent persistent memory. If the application crashes mid-search, or if we need to pause
the agent to wait for human approval before booking, the agent can resume exactly where it left off.
"""
import logging
from langgraph.graph import StateGraph, START, END
from src.state import AgentState
from src.nodes import gather_constraints_node, search_flights_node, trigger_booking_node
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)


def should_continue(state: AgentState) -> str:
    """Router function to decide the next step."""
    turns = state.get("turns", 0)

    if turns >= 3:
        logger.warning("Turn limit reached | turns=%d ending workflow", turns)
        return "end_due_to_max_turns"

    if not state.get("flight_options"):
        logger.info("No flights found | turn=%d replanning", turns)
        return "replan"

    max_budget = (state.get("constraints") or {}).get("max_budget") or float("inf")
    if all(f.get("price", float("inf")) > max_budget for f in state["flight_options"]):
        logger.info("All flights over budget=%s | turn=%d replanning", max_budget, turns)
        return "replan"

    logger.info("Flights available within budget | turn=%d proceeding to booking", turns)
    return "proceed"

# 1. Initialize the graph with our state schema
workflow = StateGraph(AgentState)

# 2. Add our nodes to the graph
workflow.add_node("gather_constraints", gather_constraints_node)
workflow.add_node("search_flights", search_flights_node)
workflow.add_node("trigger_booking", trigger_booking_node)

# When linking the graph:
workflow.add_conditional_edges(
    "search_flights", # 1. Start node
    should_continue, # 2. Router function
    { # 3. Path mapping: {router_output: destination_node}
        "replan": "gather_constraints",
        "proceed": "trigger_booking",
        "end_due_to_max_turns": END
    }
)

# 3. Connect the nodes with edges
workflow.add_edge(START, "gather_constraints")
workflow.add_edge("gather_constraints", "search_flights")
workflow.add_edge("trigger_booking", END)

# A. Initialize an in-memory checkpointer
memory = MemorySaver()

# 4. Compile the graph into an executable runnable
app = workflow.compile(
    checkpointer=memory, # Compile the graph with the checkpointer attached
    interrupt_before=["trigger_booking"] # LangGraph to halt right before running "trigger_booking"
)