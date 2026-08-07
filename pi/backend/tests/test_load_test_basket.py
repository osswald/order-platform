"""Unit tests for load-test basket generation."""

from __future__ import annotations

import random

import pytest
from app.load_test_basket import (
    ADDITION_ATTACH_PROBABILITY,
    PRESELECTED_WEIGHT,
    build_station_pools,
    generate_basket_lines,
)


def _event_with_stations(**overrides):
    event = {
        "id": 1,
        "status": "test",
        "articles": {
            "10": {
                "id": 10,
                "name": "Burger",
                "price": 12.0,
                "sellable": True,
                "additions": [
                    {"article_id": 99, "name": "Sauce", "price": 1.0, "preselected": True},
                    {"article_id": 98, "name": "Käse", "price": 2.0, "preselected": False},
                    {"article_id": 97, "name": "Bacon", "price": 3.0, "preselected": False},
                ],
            },
            "20": {"id": 20, "name": "Bier", "price": 5.0, "sellable": True, "additions": []},
            "30": {"id": 30, "name": "Cola", "price": 4.0, "sellable": True, "additions": []},
            "40": {"id": 40, "name": "Hidden", "price": 1.0, "sellable": False, "additions": []},
            "99": {"id": 99, "name": "Sauce", "price": 1.0, "sellable": True, "additions": []},
            "98": {"id": 98, "name": "Käse", "price": 2.0, "sellable": True, "additions": []},
            "97": {"id": 97, "name": "Bacon", "price": 3.0, "sellable": True, "additions": []},
        },
        "configuration": {
            "stations": [
                {"uuid": "st-kitchen", "name": "Grill", "article_ids": [10, 40]},
                {"uuid": "st-bar", "name": "Bar", "article_ids": [20, 30]},
            ]
        },
    }
    event.update(overrides)
    return event


def test_build_station_pools_skips_unsellable_and_empty():
    pools = build_station_pools(_event_with_stations())
    assert set(pools.keys()) == {"st-kitchen", "st-bar"}
    assert pools["st-kitchen"] == [10]
    assert set(pools["st-bar"]) == {20, 30}


def test_build_station_pools_empty_when_no_sellable():
    event = _event_with_stations()
    event["articles"] = {
        "40": {"id": 40, "name": "Hidden", "price": 1.0, "sellable": False, "additions": []},
    }
    assert build_station_pools(event) == {}


def test_generate_basket_people_between_1_and_8():
    event = _event_with_stations()
    for seed in range(20):
        lines = generate_basket_lines(event, rng=random.Random(seed))
        assert lines
        total_qty = sum(int(line["qty"]) for line in lines)
        # each person contributes at least 1 unit; people 1..8
        assert 1 <= total_qty <= 64  # upper bound loose (people*articles)
        # Must use real article ids from pools
        for line in lines:
            assert line["article_id"] in {10, 20, 30}


def test_generate_basket_uses_station_subset():
    event = _event_with_stations()
    # Force single station by removing bar articles
    event["configuration"]["stations"] = [
        {"uuid": "st-kitchen", "name": "Grill", "article_ids": [10]},
    ]
    lines = generate_basket_lines(event, rng=random.Random(1))
    assert all(line["article_id"] == 10 for line in lines)


def test_generate_basket_raises_without_pools():
    event = _event_with_stations()
    event["configuration"]["stations"] = []
    with pytest.raises(ValueError, match="No sellable"):
        generate_basket_lines(event, rng=random.Random(0))


def test_additions_sometimes_attached_and_weighted():
    event = _event_with_stations()
    # Only kitchen so base article always has additions
    event["configuration"]["stations"] = [
        {"uuid": "st-kitchen", "name": "Grill", "article_ids": [10]},
    ]
    with_adds = 0
    preselected_hits = 0
    addition_picks = 0
    trials = 200
    for seed in range(trials):
        lines = generate_basket_lines(event, rng=random.Random(seed), people=1)
        assert len(lines) >= 1
        line = lines[0]
        adds = line.get("additions") or []
        if adds:
            with_adds += 1
            assert 1 <= len(adds) <= 3
            for add in adds:
                addition_picks += 1
                if add["article_id"] == 99:
                    preselected_hits += 1
    # ~50% attach rate — allow wide band
    assert 0.25 * trials < with_adds < 0.75 * trials
    # Preselected (weight 3) should appear more often than each non-preselected (weight 1)
    assert preselected_hits > addition_picks * 0.35


def test_additions_empty_when_article_has_none():
    event = _event_with_stations()
    event["configuration"]["stations"] = [
        {"uuid": "st-bar", "name": "Bar", "article_ids": [20]},
    ]
    lines = generate_basket_lines(event, rng=random.Random(7), people=3)
    assert all(not (line.get("additions") or []) for line in lines)


def test_constants_match_design():
    assert ADDITION_ATTACH_PROBABILITY == 0.5
    assert PRESELECTED_WEIGHT == 3
