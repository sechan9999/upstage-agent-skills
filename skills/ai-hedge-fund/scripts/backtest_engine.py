#!/usr/bin/env python3
"""backtest_engine.py -- Vectorized multi-factor backtest engine & G1 gatekeeper.

Computes cross-sectional signals (Momentum, Volatility, Mean Reversion),
applies vectorized transaction costs and slippage, and audits for overfitting.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


def compute_factors(prices_df: pd.DataFrame) -> pd.DataFrame:
    """Calculates cross-sectional factors: Momentum, Short-term Reversal, Volatility."""
    pvt = prices_df.pivot(index="date", columns="ticker", values="close").sort_index()
    returns = pvt.pct_change()

    # Factor 1: 12-1 Momentum (12-month minus 1-month momentum to avoid short-term reversal)
    mom = pvt.pct_change(periods=min(120, len(pvt)-2)) - returns

    # Factor 2: Low-Volatility anomaly (inverse of 60-day rolling vol)
    roll_vol = returns.rolling(window=min(60, len(pvt)-1)).std()
    low_vol = -1.0 * roll_vol

    # Factor 3: Short-term reversal (1-month inverse return)
    reversal = -1.0 * pvt.pct_change(periods=min(20, len(pvt)-2))

    # Composite signal: Z-score blend (AQR Style)
    def zscore(df: pd.DataFrame) -> pd.DataFrame:
        return df.sub(df.mean(axis=1), axis=0).div(df.std(axis=1) + 1e-8, axis=0)

    combined_signal = 0.5 * zscore(mom) + 0.3 * zscore(low_vol) + 0.2 * zscore(reversal)
    return combined_signal


def run_vectorized_backtest(
    prices_df: pd.DataFrame,
    fee_bps: float = 10.0,
    max_weight_per_asset: float = 0.25
) -> Dict[str, Any]:
    """Runs vectorized daily cross-sectional rebalancing backtest."""
    pvt = prices_df.pivot(index="date", columns="ticker", values="close").sort_index()
    daily_returns = pvt.pct_change().fillna(0.0)
    
    signals = compute_factors(prices_df).fillna(0.0)
    
    # Dollar-neutral weights: Long top half, Short bottom half
    weights = signals.sub(signals.mean(axis=1), axis=0)
    # Scale gross leverage to 1.0 (50% long, 50% short)
    gross_exposure = weights.abs().sum(axis=1) + 1e-8
    target_weights = weights.div(gross_exposure, axis=0)
    
    # Clip extreme single-asset weights
    target_weights = target_weights.clip(-max_weight_per_asset, max_weight_per_asset)

    # Shift weights by 1 day to strictly prevent lookahead bias (execute at t, return at t+1)
    actual_weights = target_weights.shift(1).fillna(0.0)

    # Gross daily portfolio returns
    gross_returns = (actual_weights * daily_returns).sum(axis=1)

    # Turnover & Transaction Costs
    turnover = (actual_weights - actual_weights.shift(1).fillna(0.0)).abs().sum(axis=1)
    cost_drag = turnover * (fee_bps / 10000.0)

    # Net daily portfolio returns
    net_returns = gross_returns - cost_drag

    # Performance Metrics
    ann_factor = 252.0
    cum_returns = (1.0 + net_returns).cumprod()
    total_ret = float(cum_returns.iloc[-1] - 1.0) if len(cum_returns) > 0 else 0.0
    ann_ret = float(net_returns.mean() * ann_factor)
    ann_vol = float(net_returns.std() * np.sqrt(ann_factor)) if net_returns.std() > 0 else 1e-5
    sharpe = float(ann_ret / ann_vol)
    
    # Maximum Drawdown (MDD)
    running_max = cum_returns.cummax()
    drawdowns = (cum_returns - running_max) / running_max
    mdd = float(abs(drawdowns.min())) if len(drawdowns) > 0 else 0.0

    # t-statistic on daily alpha
    t_stat = float(net_returns.mean() / (net_returns.std() / np.sqrt(max(1, len(net_returns))))) if net_returns.std() > 0 else 0.0
    ann_turnover = float(turnover.mean() * ann_factor)

    # G1 Gatekeeper Decision Rules
    rejection_reasons = []
    if sharpe > 3.5:
        rejection_reasons.append(f"Overfitting Alert: Unrealistically high Sharpe ({sharpe:.2f} > 3.5).")
    if t_stat < 1.8:
        rejection_reasons.append(f"Statistically Insignificant Alpha (t-stat {t_stat:.2f} < 1.8).")
    if mdd > 0.25:
        rejection_reasons.append(f"Excessive Drawdown Risk (MDD {mdd*100:.1f}% > 25%).")
    if ann_turnover > 6.0: # 600% annual turnover
        rejection_reasons.append(f"Excessive Turnover ({ann_turnover*100:.1f}% > 600%), eaten by fees.")

    g1_passed = len(rejection_reasons) == 0

    return {
        "gate": "G1",
        "passed": g1_passed,
        "status": "APPROVED" if g1_passed else "REJECTED",
        "metrics": {
            "total_return_pct": round(total_ret * 100, 2),
            "annualized_return_pct": round(ann_ret * 100, 2),
            "annualized_volatility_pct": round(ann_vol * 100, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown_pct": round(mdd * 100, 2),
            "t_statistic": round(t_stat, 2),
            "annualized_turnover_pct": round(ann_turnover * 100, 1),
            "fee_drag_bps": fee_bps,
        },
        "latest_target_weights": target_weights.iloc[-1].round(4).to_dict() if len(target_weights) else {},
        "rejection_reasons": rejection_reasons,
    }


def main():
    parser = argparse.ArgumentParser(description="Vectorized Backtest Engine & G1 Gatekeeper")
    parser.add_argument("--prices_csv", help="Path to pre-ingested prices CSV (date, ticker, close)")
    parser.add_argument("--fee_bps", type=float, default=10.0, help="Slippage and transaction fee in bps")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    args = parser.parse_args()

    if args.prices_csv:
        df = pd.read_csv(args.prices_csv)
    else:
        # Default run using sample data
        from data_feed import fetch_market_data
        df = fetch_market_data(["AAPL", "MSFT", "NVDA", "JPM", "TLT", "AMZN", "GOOGL"], period="1y")

    res = run_vectorized_backtest(df, fee_bps=args.fee_bps)

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print(f"=== Senior Researcher Vectorized Backtest (G1 Gate) ===")
        print(f"Status: {res['status']} (Passed: {res['passed']})")
        for k, v in res["metrics"].items():
            print(f"  - {k}: {v}")
        if res["rejection_reasons"]:
            print("G1 Rejection Reasons:")
            for r in res["rejection_reasons"]:
                print(f"  [REJECT] {r}")
        else:
            print("G1 Strategy Approved for PM Allocation.")

if __name__ == "__main__":
    main()
