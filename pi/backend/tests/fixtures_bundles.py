"""Synced bundle payloads for pi backend API tests."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def default_bundle() -> dict[str, Any]:
    return {
        "organisation_id": 1,
        "events": [
            {
                "id": 1,
                "name": "Test",
                "currency": "CHF",
                "payment_mode": "pay_later",
                "payment_types": ["cash"],
                "articles": {
                    "10": {"id": 10, "name": "Bier", "price": 5.0, "additions": []},
                },
                "configuration": {"stations": []},
            }
        ],
    }


def admin_bundle(*, pin_hashes: list[str]) -> dict[str, Any]:
    return {
        "organisation_id": 1,
        "admin_pin_hashes": list(pin_hashes),
        "events": [],
    }


def kitchen_monitor_bundle() -> dict[str, Any]:
    bundle = default_bundle()
    event = bundle["events"][0]
    event["printer_hosts"] = {
        "st-kitchen": "127.0.0.1:9100",
        "st-bar": "127.0.0.1:9100",
    }
    event["articles"] = {
        "10": {"id": 10, "name": "Burger", "price": 12.0, "additions": []},
        "20": {"id": 20, "name": "Bier", "price": 5.0, "additions": []},
    }
    event["configuration"] = {
        "stations": [
            {
                "uuid": "st-kitchen",
                "name": "Grill",
                "sort_order": 0,
                "kitchen_monitor_enabled": True,
                "article_ids": [10],
            },
            {
                "uuid": "st-bar",
                "name": "Bar",
                "sort_order": 1,
                "kitchen_monitor_enabled": False,
                "article_ids": [20],
            },
        ],
        "event_waiters": [{"uuid": "w-1", "name": "Anna"}],
    }
    return bundle


def cash_register_bundle() -> dict[str, Any]:
    bundle = kitchen_monitor_bundle()
    event = bundle["events"][0]
    event["printer_hosts"] = {
        "reg-1": "127.0.0.1:9100",
        "st-kitchen": "127.0.0.1:9100",
        "st-bar": "127.0.0.1:9100",
    }
    event["configuration"]["event_waiters"] = []
    event["configuration"]["app_layouts"] = [
        {
            "uuid": "layout-1",
            "name": "Kasse",
            "is_default": True,
            "grid_width": 1,
            "grid_height": 1,
            "cells": [],
        }
    ]
    event["configuration"]["cash_registers"] = [
        {
            "uuid": "reg-1",
            "name": "Hauptkasse",
            "sort_order": 0,
            "pickup_code_prefix": "A",
            "layout_uuid": "layout-1",
        }
    ]
    return bundle


def order_fiscal_bundle() -> dict[str, Any]:
    bundle = default_bundle()
    bundle["events"][0]["configuration"] = {
        "stations": [],
        "waiters": [{"uuid": "w-1", "name": "Anna"}],
    }
    return bundle


def payment_receipts_bundle() -> dict[str, Any]:
    return {
        "organisation_id": 1,
        "events": [
            {
                "id": 1,
                "name": "Receipt Test",
                "currency": "CHF",
                "payment_mode": "pay_now",
                "payment_types": ["cash"],
                "printer_hosts": {},
                "articles": {
                    "10": {"id": 10, "name": "Burger", "price": 12.0, "additions": []},
                },
                "configuration": {
                    "stations": [],
                    "event_waiters": [{"uuid": "w-1", "name": "Anna"}],
                },
            }
        ],
    }


def bundle_copy(data: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(data)
