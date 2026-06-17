import uuid
import logging
from fastapi import APIRouter, HTTPException
from api.schemas import (
    SearchRequest, SearchResponse,
    ApproveRequest, ApproveResponse,
    SessionResponse, FlightOption,
)
from src.graph import app as agent

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/flights",
    tags=["flights"],
)

# Routes

@router.post("/search", response_model=SearchResponse)
def search(request: SearchRequest):
  session_id = str(uuid.uuid4())
  config = {"configurable": {"thread_id": session_id}}

  initial_input = {
      "user_request": request.user_request,
      "flight_options": [],
      "constraints": {},
      "current_status": "Starting",
      "turns": 0,
      "booked_flight": None,
  }

  logger.info("Search started | session=%s", session_id)

  for event in agent.stream(initial_input, config=config):
      if "__interrupt__" in event:
          break

  state = agent.get_state(config).values
  flights = [FlightOption.model_validate(f) for f in state.get("flight_options", [])]

  logger.info("Search complete | session=%s flights=%d", session_id, len(flights))

  return SearchResponse(
      session_id=session_id,
      flights_found=flights,
      current_status=state.get("current_status", ""),
  )


@router.post("/approve/{session_id}", response_model=ApproveResponse)
def approve(session_id: str, request: ApproveRequest):
    config = {"configurable": {"thread_id": session_id}}

    snapshot = agent.get_state(config)
    if not snapshot.values:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    # Merge human overrides into existing constraints
    if request.destination or request.max_budget:
        current = snapshot.values.get("constraints", {})
        updated = {**current}
        if request.destination:
            updated["destination"] = request.destination
        if request.max_budget:
            updated["max_budget"] = request.max_budget

        logger.info("Constraint override | session=%s updated=%s", session_id, updated)
        agent.update_state(config, {"constraints": updated}, as_node="gather_constraints")

        # Re-run search with updated constraints, stop at interrupt again
        for event in agent.stream(None, config=config):
            if "__interrupt__" in event:
                break

    # Resume past the interrupt: executes trigger_booking
    logger.info("Booking approved | session=%s", session_id)
    for event in agent.stream(None, config=config):
        pass

    final = agent.get_state(config).values
    raw = final.get("booked_flight")

    return ApproveResponse(
        booked_flight=FlightOption.model_validate(raw) if raw else None,
        current_status=final.get("current_status", ""),
    )

@router.get("/session/{session_id}", response_model=SessionResponse)
def get_session(session_id: str):
  config = {"configurable": {"thread_id": session_id}}

  snapshot = agent.get_state(config)
  if not snapshot.values:
      raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

  if not snapshot.values:
      raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

  state = snapshot.values
  flights = [FlightOption.model_validate(f) for f in state.get("flight_options", [])]

  return SessionResponse(
      session_id=session_id,
      constraints=state.get("constraints", {}),
      flight_options=flights,
      current_status=state.get("current_status", ""),
      turns=state.get("turns", 0),
  )