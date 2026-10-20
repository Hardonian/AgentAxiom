import json

import pytest

from agentaxiom.pricing import ModelPricing, PricingCatalog


def test_from_json_round_trip(tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text(
        json.dumps(
            {
                "version": "2026-10-20-draft",
                "effective_date": "2026-10-20",
                "approval_status": "draft-pending-owner-approval",
                "rates": {
                    "gemini-2.5-flash": {
                        "input_per_million_usd": 0.30,
                        "output_per_million_usd": 2.50,
                        "effective_date": "2026-10-20",
                        "source": "https://ai.google.dev/gemini-api/docs/pricing",
                    }
                },
            }
        )
    )
    catalog = PricingCatalog.from_json(path)
    assert catalog.version == "2026-10-20-draft"
    assert catalog.effective_date == "2026-10-20"
    assert catalog.approval_status == "draft-pending-owner-approval"
    assert catalog.rates["gemini-2.5-flash"].source.endswith("/pricing")
    assert catalog.estimate("gemini-2.5-flash", {"input": 1_000_000, "output": 100_000}) == pytest.approx(0.55)


def test_from_json_rejects_unknown_rate_keys(tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps({"rates": {"gemini-2.5-flash": {"input_per_million_usd": 1.0, "bogus_key": 2.0}}}))
    with pytest.raises(TypeError):
        PricingCatalog.from_json(path)


def test_shipped_draft_catalog_loads_and_is_marked_unapproved():
    catalog = PricingCatalog.from_json("pricing/gemini-catalog-2026-10.json")
    assert catalog.approval_status == "draft-pending-owner-approval"
    assert catalog.rates, "catalog must contain at least one verified rate"
    for rate in catalog.rates.values():
        assert rate.effective_date and rate.source


def test_unknown_model_estimates_zero():
    catalog = PricingCatalog(rates={"known": ModelPricing(1.0, 2.0)})
    assert catalog.estimate("unknown", {"input": 1000, "output": 1000}) == 0.0
