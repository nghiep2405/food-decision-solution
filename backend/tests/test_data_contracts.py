from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.data.contracts import SearchContext


def base_context() -> dict:
    return {
        "mode": "direct",
        "query": "cơm tấm",
        "searchCenter": {"lat": 10.7736, "lng": 106.6901},
        "searchArea": {"mode": "circle", "radiusKm": 5},
        "filters": {"minRating": None, "openNow": False, "sortBy": "recommended"},
        "consent": {"locationGps": False, "preferences": False, "eatingHistory": False},
        "candidateSource": "local",
    }


def test_search_context_uses_camel_case_at_api_boundary():
    context = SearchContext.model_validate(base_context())
    dumped = context.model_dump(mode="json", by_alias=True)

    assert dumped["searchCenter"]["lat"] == pytest.approx(10.7736)
    assert dumped["searchArea"]["radiusKm"] == 5
    assert dumped["candidateSource"] == "local"


def test_bbox_requires_bounds():
    payload = base_context()
    payload["searchArea"] = {"mode": "bbox", "radiusKm": None, "bounds": None}
    with pytest.raises(ValidationError):
        SearchContext.model_validate(payload)


def test_gps_requires_explicit_consent():
    payload = base_context()
    payload["userLocation"] = {
        "source": "gps",
        "lat": 10.7736,
        "lng": 106.6901,
        "accuracyMeters": 20,
    }
    with pytest.raises(ValidationError):
        SearchContext.model_validate(payload)


def test_missing_optional_budget_is_valid_and_not_converted_to_zero():
    context = SearchContext.model_validate(base_context())
    assert context.budget is None
