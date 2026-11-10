import pytest

from research_engine.contract_identity import audit_contract_identity


def test_tmfr1_product_id_is_not_misrepresented_as_contract_month():
    result = audit_contract_identity([
        {"product_id": "TMFR1", "datetime": "2025-01-01 08:45:00", "close": 22000},
        {"product_id": "TMFR1", "datetime": "2025-01-01 08:46:00", "close": 22001},
    ])
    assert result.product_ids == ("TMFR1",)
    assert result.identity_level == "continuous_or_unidentified"
    assert result.individual_contract_month_available is False
    assert result.missing_contract_fields == ("contract_month", "contract_code")
    assert len(result.warnings) == 2


def test_individual_contract_requires_both_month_and_contract_code():
    result = audit_contract_identity([
        {"product_id": "TMF", "contract_month": "202501", "contract_code": "TMF202501"},
    ])
    assert result.identity_level == "individual_contract_identified"
    assert result.individual_contract_month_available is True


def test_empty_rows_are_rejected():
    with pytest.raises(ValueError, match="empty dataset"):
        audit_contract_identity([])
