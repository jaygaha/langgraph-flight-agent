from pydantic import BaseModel, Field, model_validator
from typing import Optional, Any

# Shared
"""
The mock data uses "from" and "to" as dict keys — but from is a reserved Python keyword
so you can't write flight.from. The Field(alias="from") lets Pydantic map the raw "from"
key from the agent's output into the origin field on the model.

model_config = {"populate_by_name": True} means you can construct a FlightOption using
either origin= or from= — useful when building test objects.
"""
class FlightOption(BaseModel):
    flight_id: str
    price: int
    airline: str
    origin: str
    destination: str

    @model_validator(mode="before")
    @classmethod
    def remap_keys(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            if "from" in data and "origin" not in data:
                data["origin"] = data.pop("from")
            if "to" in data and "destination" not in data:
                data["destination"] = data.pop("to")
        return data

# Request bodies
"""
min_length=5 rejects obviously empty requests at the API boundary before they ever reach the LLM.
"""
class SearchRequest(BaseModel):
    user_request: str = Field(
        min_length=5,
        examples=["Find a flight from KTM to NRT under 500 USD"]
    )

"""
Both fields are Optional — the human can override one, both, or neither before approving. The route handler will merge 
whatever is provided with the existing state.
"""
class ApproveRequest(BaseModel):
    destination: Optional[str] = Field(None, description="Override destination before booking")
    max_budget: Optional[int] = Field(None, description="Override budget before booking")

# Responses
"""
Returns the session_id the client needs to call /approve later. Without it, the client has no way to resume 
the workflow.
"""
class SearchResponse(BaseModel):
    session_id: str
    flights_found: list[FlightOption]
    current_status: str

class ApproveResponse(BaseModel):
    booked_flight: Optional[FlightOption]
    current_status: str

class SessionResponse(BaseModel):
    session_id: str
    constraints: dict
    flight_options: list[FlightOption]
    current_status: str
    turns: int

