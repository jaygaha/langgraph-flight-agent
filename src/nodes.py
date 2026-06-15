"""
In LangGraph, these actions are called Graph Nodes.

Architectural Concept: A node is simply a Python function. It receives the current AgentState as an argument,
performs some business logic (like calling an LLM or an API), and returns a dictionary containing the specific keys
it wants to update in the state.

Our first node needs to take the unstructured user_request (e.g., "I need a flight to Tokyo under $800 next week")
and populate the constraints dictionary we just created.
"""
import logging
from pydantic import BaseModel, Field
from typing import Optional
from src.state import AgentState
from src.llm import get_llm
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)


class FlightConstraints(BaseModel):
    origin: Optional[str] = Field(None, description="The departure city or airport code")
    destination: Optional[str] = Field(None, description="The arrival city or airport code")
    max_budget: Optional[int] = Field(None, description="Maximum budget in USD, or None if not mentioned")


def gather_constraints_node(state: AgentState) -> dict:
    llm = get_llm().with_structured_output(FlightConstraints)

    messages = [
        SystemMessage(content=(
            "You are a flight data extractor. "
            "Extract the origin airport code, destination airport code, and max budget from the user message. "
            "Return only IATA codes (e.g. NRT, HND, KTM). "
            "If a field is not mentioned, return null for that field."
        )),
        HumanMessage(content=state["user_request"]),
    ]

    extracted_constraints = llm.invoke(messages)
    current_turns = state.get("turns", 0) + 1

    logger.info(
        "Constraints extracted | origin=%s destination=%s max_budget=%s turn=%d",
        extracted_constraints.origin,
        extracted_constraints.destination,
        extracted_constraints.max_budget,
        current_turns,
    )

    return {
        "constraints": extracted_constraints.model_dump(),
        "current_status": "Constraints gathered",
        "turns": current_turns,
    }


def fetch_live_flights(origin: str, destination: str, max_budget: float = float("inf")) -> list:
    """Simulated external API client wrapper that filters by budget."""
    mock_database = [
        {"flight_id": "AA-123", "price": 450, "airline": "American", "from": origin, "to": destination},
        {"flight_id": "DL-456", "price": 550, "airline": "Delta",    "from": origin, "to": destination},
    ]
    return [f for f in mock_database if f["price"] <= max_budget]


def search_flights_node(state: AgentState) -> dict:
    constraints = state.get("constraints", {})
    origin = constraints.get("origin")
    destination = constraints.get("destination")
    max_budget = constraints.get("max_budget") or float("inf")

    if not origin or not destination:
        logger.warning("Search aborted; missing origin or destination | constraints=%s", constraints)
        return {
            "current_status": "Missing necessary details. Please specify both locations.",
            "flight_options": [],
        }

    try:
        flights = fetch_live_flights(origin, destination, max_budget)
        logger.info(
            "Flight search complete | route=%s->%s budget=%s found=%d",
            origin, destination, max_budget, len(flights),
        )
        status = f"Found {len(flights)} flights matching constraints."
    except Exception:
        logger.exception("Flight search API error | route=%s->%s", origin, destination)
        flights = []
        status = "Flight search failed due to an API error."

    return {"flight_options": flights, "current_status": status}


def trigger_booking_node(state: AgentState) -> dict:
    max_budget = (state.get("constraints") or {}).get("max_budget") or float("inf")
    valid_flights = [f for f in state.get("flight_options", []) if f.get("price", float("inf")) <= max_budget]

    if not valid_flights:
        logger.warning("Booking failed; no affordable flights | max_budget=%s", max_budget)
        return {
            "current_status": "No affordable flights found. Please check constraints.",
        }

    best_flight = min(valid_flights, key=lambda f: f["price"])
    logger.info(
        "Booking confirmed | flight=%s airline=%s price=%s route=%s->%s",
        best_flight["flight_id"],
        best_flight["airline"],
        best_flight["price"],
        best_flight["from"],
        best_flight["to"],
    )

    return {
        "current_status": f"Successfully selected flight {best_flight['flight_id']} for ${best_flight['price']}",
    }
