import logging
from src.graph import app
from src.config import settings
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

def _log_events(stream) -> None:
    """Stream graph events and log each one cleanly."""
    for event in stream:
        if "__interrupt__" in event:
            logger.info("Graph paused: awaiting human review before trigger_booking")
        else:
            node, output = next(iter(event.items()))
            logger.info("[%s] %s", node, output.get("current_status", output))


def run_agent_workflow() -> None:
    config = {"configurable": {"thread_id": "session_123"}}

    initial_input = {
        "user_request": "Find a flight from KTM to HND under $500.",
        "flight_options": [],
        "current_status": "Starting",
        "turns": 0,
    }

    logger.info("Part 1: Initial gathering & search")
    _log_events(app.stream(initial_input, config=config))

    logger.info("Simulating human review: updating destination to NRT")
    current_constraints = app.get_state(config).values.get("constraints", {})
    updated_constraints = {**current_constraints, "destination": "NRT"}
    app.update_state(config, {"constraints": updated_constraints}, as_node="gather_constraints")
    logger.info("State updated: destination=%s", updated_constraints.get("destination"))

    logger.info("Part 2: Resuming with updated destination")
    _log_events(app.stream(None, config=config))

    logger.info("Part 3: Human approved; executing booking")
    _log_events(app.stream(None, config=config))

    final = app.get_state(config).values
    logger.info("Workflow complete | status=%s", final.get("current_status"))


if __name__ == "__main__":
    run_agent_workflow()