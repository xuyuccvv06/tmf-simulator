"""Conservative contract-identity checks for futures datasets.

A continuous symbol such as TMFR1 is not an individual expiry-month contract.
This module refuses to infer a contract month from dates or price behaviour.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ContractIdentityAudit:
    product_ids: tuple[str, ...]
    identity_level: str
    individual_contract_month_available: bool
    missing_contract_fields: tuple[str, ...]
    warnings: tuple[str, ...]


CONTRACT_LEVEL_FIELDS = ("contract_month", "contract_code")


def audit_contract_identity(
    rows: Iterable[dict[str, object]],
    *,
    product_field: str = "product_id",
) -> ContractIdentityAudit:
    materialized = list(rows)
    if not materialized:
        raise ValueError("cannot audit contract identity from an empty dataset")

    product_ids = tuple(sorted({
        str(row[product_field]).strip()
        for row in materialized
        if row.get(product_field) is not None and str(row[product_field]).strip()
    }))
    if not product_ids:
        raise ValueError(f"no usable {product_field!r} values")

    present = set.intersection(*[
        {key for key, value in row.items() if value is not None and str(value).strip()}
        for row in materialized
    ])
    missing = tuple(field for field in CONTRACT_LEVEL_FIELDS if field not in present)

    has_month = "contract_month" in present
    has_code = "contract_code" in present
    if has_month and has_code:
        level = "individual_contract_identified"
        warnings: tuple[str, ...] = ()
    else:
        level = "continuous_or_unidentified"
        warnings = (
            "Individual expiry-month attribution is unavailable; do not infer roll dates from price jumps.",
            "Do not report contract-specific roll spread, expiry settlement, or roll execution performance.",
        )

    return ContractIdentityAudit(
        product_ids=product_ids,
        identity_level=level,
        individual_contract_month_available=has_month and has_code,
        missing_contract_fields=missing,
        warnings=warnings,
    )
