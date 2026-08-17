"""SumUp transaction → receipt_info normalization for payment slips."""

from app.sumup_receipt_info import receipt_info_from_transaction


def test_receipt_info_from_transaction_extracts_card_fields():
    info = receipt_info_from_transaction(
        {
            "id": "410fc44a-5956-44e1-b5cc-19c6f8d727a4",
            "transaction_code": "TEENSK4W2K",
            "auth_code": "053201",
            "entry_mode": "CONTACTLESS",
            "card": {"last_4_digits": "3456", "type": "MASTERCARD"},
            "timestamp": "2020-02-29T10:56:56.876Z",
            "merchant_code": "MH4H92C7",
        }
    )
    assert info == {
        "transaction_code": "TEENSK4W2K",
        "auth_code": "053201",
        "card_last_4": "3456",
        "card_type": "MASTERCARD",
        "entry_mode": "CONTACTLESS",
        "timestamp": "2020-02-29T10:56:56.876Z",
        "merchant_code": "MH4H92C7",
    }


def test_receipt_info_from_transaction_skips_empty_fields():
    info = receipt_info_from_transaction(
        {
            "transaction_code": "ABC",
            "auth_code": "",
            "card": {"last_4_digits": None, "type": "VISA"},
        }
    )
    assert info == {"transaction_code": "ABC", "card_type": "VISA"}


def test_receipt_info_from_transaction_empty_payload():
    assert receipt_info_from_transaction({}) == {}
    assert receipt_info_from_transaction(None) == {}
