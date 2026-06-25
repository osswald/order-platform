"""Edge bundle contract tests."""

import pytest
from app.edge_bundle import edge_bundle_payload, validate_edge_bundle_payload
from vendiqo_shared.bundle_contract import EdgeBundleContract


def test_edge_bundle_contract_accepts_minimal_payload():
    payload = {
        "organisation_id": 1,
        "events": [],
        "admin_pin_hashes": [],
        "position_comments_enabled": False,
        "position_comment_presets": [],
    }
    model = EdgeBundleContract.model_validate(payload)
    assert model.organisation_id == 1
    assert model.events == []


def test_edge_bundle_contract_accepts_typed_event():
    payload = {
        "organisation_id": 1,
        "events": [
            {
                "id": 1,
                "name": "Live",
                "currency": "CHF",
                "articles": {"10": {"id": 10, "name": "Bier", "price": 5.0, "additions": []}},
                "configuration": {"stations": []},
            }
        ],
    }
    model = EdgeBundleContract.model_validate(payload)
    assert model.events[0].name == "Live"
    assert model.events[0].articles["10"].price == 5.0


def test_edge_bundle_payload_builds_valid_dict():
    payload = edge_bundle_payload(
        organisation_id=1,
        events=[{"id": 1, "name": "Live"}],
        admin_pin_hashes=["hash"],
        position_comments_enabled=True,
        position_comment_presets=[{"id": 1, "text": "Ohne"}],
    )
    assert payload["organisation_id"] == 1
    assert payload["events"][0]["name"] == "Live"


def test_validate_edge_bundle_payload_rejects_missing_keys():
    with pytest.raises(ValueError, match="missing required keys"):
        validate_edge_bundle_payload({"organisation_id": 1})
