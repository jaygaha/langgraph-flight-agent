import pytest
from unittest.mock import patch, MagicMock
from src.nodes import search_flights_node, trigger_booking_node

# search_flights_node
def test_search_returns_empty_when_origin_missing():
    state = {
        "constraints": {"origin": None, "destination": "HND", "max_budget": 500},
        "flight_options": [],
    }
    result = search_flights_node(state)

    assert result['flight_options'] == []
    assert "Missing" in result['current_status']

def test_search_filters_flight_over_budget():
    state = {
        "constraints": {"origin": "KTM", "destination": "HND", "max_budget": 500},
        "flight_options": [],
    }
    result = search_flights_node(state)

    prices = [f["price"] for f in result['flight_options']]
    assert all(p <= 500 for p in prices) # flights over budget should be removed
    assert 550 not in prices # RA-456 must be filterred out

# trigger_booking_node

def test_booking_picks_cheapest_flights():
    state = {
        "constraints": {"max_budget": None},
        "flight_options": [
            {"flight_id": "XA-987", "price": 899, "airline": "ABC", "from": "KTM", "to": "NRT"},
            {"flight_id": "JL-123", "price": 450, "airline": "JAL", "from": "KTM", "to": "NRT"},
            {"flight_id": "RA-456", "price": 550, "airline": "RNA", "from": "KTM", "to": "NRT"},
        ],
    }
    result = trigger_booking_node(state)

    assert "JL-123" in result['current_status']
    assert "450" in result['current_status']

def test_booking_fails_gracefully_when_no_afforable_flights():
    state = {
        "constraints": {"max_budget": 99},
        "flight_options": [
            {"flight_id": "JL-123", "price": 450, "airline": "JAL", "from": "KTM", "to": "NRT"},
        ],
    }
    result = trigger_booking_node(state)

    assert "No affordable" in result['current_status']