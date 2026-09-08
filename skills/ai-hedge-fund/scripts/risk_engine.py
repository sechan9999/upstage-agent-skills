#!/usr/bin/env python3
"""risk_engine.py -- CRO / Risk Model Agent (Two-Tier G2 Gatekeeper).

Evaluates:
  Tier 1: PM Individual Desk limits (Quant PM, Macro PM, Arb PM)
  Tier 2: Firm-Wide Aggregated Exposure & Correlation Collision
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


SECTOR_MAP = {
    "AAPL": "Technology", "MSFT": "Technology", "NVDA": "Technology", "GOOGL": "Technology", "AMZN": "Consumer Discretionary",
    "JPM": "Financials", "GS": "Financials", "TLT": "Fixed_Income", "IEF": "Fixed_Income", "GLD": "Commodities"
}

# Interest rate duration sensitivity proxy
RATE_SENSITIVITY_MAP = {
    "TLT": 1.8, "IEF": 0.9, "JPM": -0.4, "AAPL": 0.3, "MSFT": 0.3, "NVDA": 0.5, "GLD": 0.2
}


def evaluate_g2_risk(
    quant_pm_weights: Dict[str, float],
    macro_pm_weights: Dict[str, float],
    max_firm_sector_exposure: float = 0.35,
    max_firm_rate_sensitivity: float = 0.60
) -> Dict[str, Any]:
    """CRO Two-Tier G2 Gatekeeper: Individual Desk + Firm-wide combined check."""
    issues = []
    
    # -------------------------------------------------------------
    # Tier 1: Individual PM Desk Limit Verification
    # -------------------------------------------------------------
    desk_reports = {}
    for desk_name, w_dict in [("Quant_PM", quant_pm_weights), ("Macro_PM", macro_pm_weights)]:
        series = pd.Series(w_dict)
        gross_lev = float(series.abs().sum())
        net_exp = float(series.sum())
        max_single = float(series.abs().max()) if len(series) else 0.0
        
        passed = True
        desk_issues = []
        if max_single > 0.25:
            desk_issues.append(f"Single asset concentration breach: {max_single*100:.1f}% > 25%")
            passed = False
        if abs(net_exp) > 0.30 and desk_name == "Quant_PM":
            desk_issues.append(f"Quant PM market-neutrality breach: net {net_exp*100:.1f}% > 30%")
            passed = False
            
        desk_reports[desk_name] = {
            "passed": passed,
            "gross_leverage": round(gross_lev, 3),
            "net_exposure": round(net_exp, 3),
            "max_single_asset": round(max_single, 3),
            "issues": desk_issues
        }
        if not passed:
            issues.extend([f"[{desk_name}] {iss}" for iss in desk_issues])

    # -------------------------------------------------------------
    # Tier 2: Firm-Wide Aggregated Exposure Check (CRO Core Mandate)
    # -------------------------------------------------------------
    all_tickers = sorted(set(list(quant_pm_weights.keys()) + list(macro_pm_weights.keys())))
    firm_weights = pd.Series(0.0, index=all_tickers)
    
    for t, w in quant_pm_weights.items():
        firm_weights[t] += w * 0.60 # 60% capital weight to Quant PM
    for t, w in macro_pm_weights.items():
        firm_weights[t] += w * 0.40 # 40% capital weight to Macro PM

    # 1. Firm-wide Sector Aggregation
    sector_exposure = {}
    for t, w in firm_weights.items():
        sec = SECTOR_MAP.get(t, "Other")
        sector_exposure[sec] = sector_exposure.get(sec, 0.0) + abs(w)

    for sec, exp in sector_exposure.items():
        if exp > max_firm_sector_exposure:
            issues.append(f"[Firm-wide Collision] Sector '{sec}' exposure {exp*100:.1f}% exceeds limit of {max_firm_sector_exposure*100:.1f}%.")

    # 2. Firm-wide Macro Interest Rate Sensitivity Collision Detection
    # Detects if Quant PM tech longs + Macro PM duration longs accumulate dangerous rate sensitivity
    total_rate_sens = 0.0
    for t, w in firm_weights.items():
        sens = RATE_SENSITIVITY_MAP.get(t, 0.0)
        total_rate_sens += w * sens

    if abs(total_rate_sens) > max_firm_rate_sensitivity:
        issues.append(
            f"[Firm-wide Rate Collision] Net combined interest rate sensitivity ({total_rate_sens:.2f}) "
            f"exceeds firm risk budget ({max_firm_rate_sensitivity:.2f}). Quant PM and Macro PM are piling into the same macro bet."
        )

    g2_passed = len(issues) == 0

    return {
        "gate": "G2",
        "passed": g2_passed,
        "status": "APPROVED" if g2_passed else "REJECTED",
        "tier1_desk_checks": desk_reports,
        "tier2_firmwide_check": {
            "passed": len(issues) == 0,
            "firm_gross_leverage": round(float(firm_weights.abs().sum()), 3),
            "firm_net_exposure": round(float(firm_weights.sum()), 3),
            "firm_rate_sensitivity": round(float(total_rate_sens), 2),
            "sector_exposures": {k: round(v, 3) for k, v in sector_exposure.items()},
            "firm_weights": firm_weights.round(4).to_dict()
        },
        "issues": issues,
        "required_action": "Proceed to CIO G3 Final Approval" if g2_passed else "Reject to PM desks for position downscaling."
    }


def main():
    parser = argparse.ArgumentParser(description="CRO Risk Engine & Two-Tier G2 Gatekeeper")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    args = parser.parse_args()

    # Sample PM positions demonstrating collision detection
    quant_pm = {"AAPL": 0.15, "MSFT": 0.15, "NVDA": 0.12, "JPM": -0.15, "AMZN": -0.10}
    macro_pm = {"TLT": 0.20, "IEF": 0.15, "GLD": 0.10, "NVDA": 0.05}

    report = evaluate_g2_risk(quant_pm, macro_pm)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"=== CRO Risk Evaluation & Two-Tier G2 Gate ===")
        print(f"Status: {report['status']} (Passed: {report['passed']})")
        print(f"Firm Rate Sensitivity: {report['tier2_firmwide_check']['firm_rate_sensitivity']}")
        print(f"Sector Exposures: {report['tier2_firmwide_check']['sector_exposures']}")
        if report["issues"]:
            print("G2 Breaches Detected:")
            for iss in report["issues"]:
                print(f"  [BREACH] {iss}")
        else:
            print("All Tier 1 (Desk) and Tier 2 (Firm-wide) risk checks cleared.")

if __name__ == "__main__":
    main()
