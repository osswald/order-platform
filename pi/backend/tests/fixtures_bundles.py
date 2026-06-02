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


def voucher_bundle() -> dict[str, Any]:
    bundle = cash_register_bundle()
    event = bundle["events"][0]
    event["configuration"]["voucher_definitions"] = [
        {
            "uuid": "vd-20",
            "name": "20 CHF Gutschein",
            "kind": "fixed_amount",
            "value_cents": 2000,
            "allowed_article_ids": [],
            "include_additions": True,
        },
        {
            "uuid": "vd-drink",
            "name": "1 Getränk",
            "kind": "article_entitlement",
            "value_cents": None,
            "allowed_article_ids": [20],
            "include_additions": True,
        },
    ]
    event["configuration"]["app_layouts"][0]["cells"] = [
        {
            "row": 0,
            "col": 0,
            "label": "20.-",
            "color": "#fef08a",
            "article_ids": [],
            "voucher_definition_uuid": "vd-20",
        }
    ]
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
    event["configuration"]["voucher_definitions"] = []
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
            "pin": "0000",
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
                "printer_hosts": {"st-bar": "127.0.0.1:9100"},
                "articles": {
                    "10": {"id": 10, "name": "Burger", "price": 12.0, "additions": []},
                },
                "configuration": {
                    "stations": [
                        {
                            "uuid": "st-bar",
                            "name": "Bar",
                            "sort_order": 0,
                            "article_ids": [10],
                        }
                    ],
                    "event_waiters": [{"uuid": "w-1", "name": "Anna"}],
                },
            }
        ],
    }


def bundle_copy(data: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(data)
