"""Permit Clock: what a month of waiting costs. Prototype only. Not financial advice.

Carrying cost per month while a project waits for permits or construction:

    loan balance x interest rate / 12
  + assessed value x property tax rate / 12
  + construction budget not yet built x cost escalation / 12
  + insurance, staff and other fixed costs per month

The rates below are sourced (see SOURCES). The dollar amounts are from the SYNTHETIC one-home
example in lanes/3-fund-it/data/synthetic-example-deal.json and are ASSUMPTIONS: the user
replaces them with their own project.
"""
from __future__ import annotations

# Sourced rates. Each entry: value in percent per year, where it came from, date checked.
SOURCES = {
    "interest_rate_pct": {
        "value": 7.00,
        "name": "Bank prime loan rate (Federal Reserve H.15, via FRED series DPRIME)",
        "url": "https://fred.stlouisfed.org/series/DPRIME",
        "observed": "2026-10-27",
        "checked": "2026-11-08",
        "note": "A nonprofit's acquisition loan may price above or below prime. Replace with "
                "your lender's rate.",
    },
    "property_tax_pct": {
        "value": 1.1,
        "name": "Proposition 13 limit of 1% of assessed value plus about 0.1% in voter-approved "
                "debt rates (Legislative Analyst's Office, Understanding California's Property "
                "Taxes)",
        "url": "https://lao.ca.gov/reports/2012/tax/property-tax-primer-112912.aspx",
        "observed": "2012-11-29",
        "checked": "2026-11-08",
        "note": "Statewide typical total. Local debt rates differ by city; check the bill. "
                "Some nonprofits qualify for the welfare exemption, which would lower this.",
    },
    "escalation_pct": {
        "value": 5.5,
        "name": "Turner Building Cost Index, Q3 2026 (1575) against Q3 2025 (1493), a 5.5% rise "
                "in a year",
        "url": "https://turnerconstruction.com/uploads/cost-index-Q3-2026.pdf",
        "observed": "2026-Q3",
        "checked": "2026-11-08",
        "note": "National index, not Orange County. Construction you have not yet bought gets "
                "more expensive while you wait.",
    },
}

# ASSUMPTION: dollar defaults from the SYNTHETIC example deal (not a real project).
EXAMPLE = {
    "loan_balance": 360_000,        # land_and_building_purchase in the synthetic deal
    "assessed_value": 360_000,      # same purchase price, ASSUMPTION: assessed at purchase
    "construction_budget": 40_000,  # construction_and_repairs in the synthetic deal
    "fixed_monthly": 0,             # insurance, staff, other: unknown, user fills in
}


def monthly_cost(loan_balance: float, interest_rate_pct: float, assessed_value: float,
                 property_tax_pct: float, construction_budget: float, escalation_pct: float,
                 fixed_monthly: float) -> dict[str, float]:
    """Dollars per month of waiting, by part and in total."""
    parts = {
        "Loan interest": loan_balance * interest_rate_pct / 100 / 12,
        "Property tax": assessed_value * property_tax_pct / 100 / 12,
        "Construction cost rising": construction_budget * escalation_pct / 100 / 12,
        "Insurance, staff, other": fixed_monthly,
    }
    parts["total"] = sum(parts.values())
    return parts


def example_monthly_cost() -> dict[str, float]:
    """The default shown before the user enters anything (EXAMPLE amounts, sourced rates)."""
    return monthly_cost(EXAMPLE["loan_balance"], SOURCES["interest_rate_pct"]["value"],
                        EXAMPLE["assessed_value"], SOURCES["property_tax_pct"]["value"],
                        EXAMPLE["construction_budget"], SOURCES["escalation_pct"]["value"],
                        EXAMPLE["fixed_monthly"])
