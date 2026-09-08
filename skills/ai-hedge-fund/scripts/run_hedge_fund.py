#!/usr/bin/env python3
"""run_hedge_fund.py -- Complete End-to-End Autonomous AI Hedge Fund Pipeline Orchestrator.

Wires:
  CTO (Data Ingestion & G0)
  -> Senior Quant Researcher (Factor Computation & G1 Backtest)
  -> PM Desks (Quant PM & Macro PM)
  -> CRO (G2 Two-Tier Individual + Firm-wide Risk Audit)
  -> CIO (G3 Final Capital Allocation)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime

from data_feed import fetch_market_data, store_in_duckdb, validate_g0
from backtest_engine import run_vectorized_backtest
from risk_engine import evaluate_g2_risk


def run_pipeline(tickers: list[str], period: str = "1y", db_path: str = "market_data.duckdb") -> dict:
    audit_log = []
    
    # 1. CTO Ingestion & G0 Gate
    audit_log.append("[Step 1] CTO Data Ingestion from yfinance into DuckDB...")
    df = fetch_market_data(tickers, period=period)
    store_in_duckdb(df, db_path)
    g0 = validate_g0(df, tickers)
    audit_log.append(f"[Gate G0] Result: {g0['status']} (Passed: {g0['passed']})")
    if not g0["passed"]:
        return {"pipeline_status": "HALTED_AT_G0", "error": g0["issues"], "audit_log": audit_log}

    # 2. Senior Quant Researcher & G1 Gate
    audit_log.append("[Step 2] Senior Researcher Factor Calculation & Vectorized Backtest...")
    g1 = run_vectorized_backtest(df, fee_bps=10.0)
    audit_log.append(f"[Gate G1] Result: {g1['status']} (Sharpe: {g1['metrics']['sharpe_ratio']}, MDD: {g1['metrics']['max_drawdown_pct']}%)")
    if not g1["passed"]:
        return {"pipeline_status": "REJECTED_AT_G1", "reasons": g1["rejection_reasons"], "audit_log": audit_log}

    # 3. Portfolio Managers (Quant PM + Macro PM)
    audit_log.append("[Step 3] PM Desks constructing target allocations...")
    quant_pm_weights = g1["latest_target_weights"]
    macro_pm_weights = {"TLT": 0.15, "IEF": 0.10, "GLD": 0.05}

    # 4. CRO Two-Tier G2 Gate
    audit_log.append("[Step 4] CRO Auditing Desk Limits & Firm-Wide Exposure Aggregation...")
    g2 = evaluate_g2_risk(quant_pm_weights, macro_pm_weights)
    audit_log.append(f"[Gate G2] Result: {g2['status']} (Firm Rate Sensitivity: {g2['tier2_firmwide_check']['firm_rate_sensitivity']})")
    if not g2["passed"]:
        return {"pipeline_status": "REJECTED_AT_G2", "breaches": g2["issues"], "audit_log": audit_log}

    # 5. CIO G3 Final Gate
    audit_log.append("[Step 5] CIO Final Allocation & Mandate Sign-Off...")
    final_allocation = {
        "Quant_PM_Desk": {"allocation_pct": 60.0, "weights": quant_pm_weights},
        "Macro_PM_Desk": {"allocation_pct": 40.0, "weights": macro_pm_weights},
        "Firm_Aggregated_Weights": g2["tier2_firmwide_check"]["firm_weights"],
        "Expected_Sharpe": g1["metrics"]["sharpe_ratio"],
        "G3_Approval": "APPROVED_FOR_PAPER_TRADING"
    }
    audit_log.append("[Gate G3] Final Portfolio Mandate Released.")

    return {
        "pipeline_status": "SUCCESS_COMPLETED",
        "g0_data_gate": g0,
        "g1_alpha_gate": g1,
        "g2_risk_gate": g2,
        "g3_final_allocation": final_allocation,
        "audit_log": audit_log
    }


def main():
    parser = argparse.ArgumentParser(description="AI Hedge Fund Autonomous Pipeline")
    parser.add_argument("--tickers", default="AAPL,MSFT,NVDA,JPM,TLT,AMZN,GOOGL", help="Universe tickers")
    parser.add_argument("--period", default="1y", help="Historical window")
    parser.add_argument("--db", default="market_data.duckdb", help="DuckDB path")
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    args = parser.parse_args()

    ticker_list = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    result = run_pipeline(ticker_list, period=args.period, db_path=args.db)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("==========================================================")
        print("          AI HEDGE FUND ORCHESTRATION PIPELINE            ")
        print("==========================================================")
        for log in result["audit_log"]:
            print(log)
        print("----------------------------------------------------------")
        print(f"Status: {result['pipeline_status']}")
        if result["pipeline_status"] == "SUCCESS_COMPLETED":
            alloc = result["g3_final_allocation"]
            print(f"Expected Sharpe: {alloc['Expected_Sharpe']}")
            print("Firm Aggregated Weights:")
            for t, w in alloc["Firm_Aggregated_Weights"].items():
                print(f"  - {t:6s}: {w*100:+.2f}%")

if __name__ == "__main__":
    main()
