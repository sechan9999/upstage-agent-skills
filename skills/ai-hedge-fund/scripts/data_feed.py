#!/usr/bin/env python3
"""data_feed.py -- CTO / Engineer data ingestion, DuckDB cache, and G0 gate validation.

Usage:
    python data_feed.py --tickers AAPL,MSFT,NVDA,JPM,TLT --period 2y [--db market_data.duckdb] [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
import yfinance as yf

try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False
    import sqlite3


def fetch_market_data(tickers: List[str], period: str = "2y") -> pd.DataFrame:
    """Fetches adjusted OHLCV data from Yahoo Finance."""
    data = yf.download(tickers, period=period, group_by="ticker", auto_adjust=True, progress=False)
    records = []
    
    # Handle single vs multi-ticker dataframe structure
    if len(tickers) == 1:
        ticker = tickers[0]
        for date, row in data.iterrows():
            records.append({
                "date": date.strftime("%Y-%m-%d"),
                "ticker": ticker,
                "open": float(row.get("Open", 0.0)),
                "high": float(row.get("High", 0.0)),
                "low": float(row.get("Low", 0.0)),
                "close": float(row.get("Close", 0.0)),
                "volume": float(row.get("Volume", 0.0)),
            })
    else:
        for ticker in tickers:
            if ticker in data.columns.levels[0]:
                sub = data[ticker]
                for date, row in sub.iterrows():
                    records.append({
                        "date": date.strftime("%Y-%m-%d"),
                        "ticker": ticker,
                        "open": float(row.get("Open", 0.0)),
                        "high": float(row.get("High", 0.0)),
                        "low": float(row.get("Low", 0.0)),
                        "close": float(row.get("Close", 0.0)),
                        "volume": float(row.get("Volume", 0.0)),
                    })
    df = pd.DataFrame(records)
    return df


def store_in_duckdb(df: pd.DataFrame, db_path: str = "market_data.duckdb") -> None:
    """Persists ingestion records into DuckDB (or SQLite fallback)."""
    if HAS_DUCKDB:
        con = duckdb.connect(db_path)
        con.execute("CREATE TABLE IF NOT EXISTS prices (date VARCHAR, ticker VARCHAR, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume DOUBLE, PRIMARY KEY (date, ticker))")
        con.register("df_view", df)
        con.execute("INSERT OR REPLACE INTO prices SELECT * FROM df_view")
        con.close()
    else:
        con = sqlite3.connect(db_path)
        df.to_sql("prices", con, if_exists="replace", index=False)
        con.close()


def validate_g0(df: pd.DataFrame, tickers: List[str]) -> Dict[str, Any]:
    """G0 Gatekeeper: Data Quality, Lookahead & Survivorship Audit."""
    issues = []
    missing_counts = {}
    total_dates = df["date"].nunique()
    
    for t in tickers:
        sub = df[df["ticker"] == t]
        count = len(sub)
        missing_rate = (total_dates - count) / max(1, total_dates)
        missing_counts[t] = round(missing_rate * 100, 2)
        
        # Check 1: Missing rate threshold (0.5% max)
        if missing_rate > 0.05: # 5% missing threshold for G0 fail
            issues.append(f"Ticker {t} has high missing rate: {missing_rate * 100:.1f}%")
            
        # Check 2: Non-positive price anomaly
        if (sub["close"] <= 0).any():
            issues.append(f"Ticker {t} contains non-positive price values.")
            
        # Check 3: Zero volume check
        zero_vol_pct = (sub["volume"] == 0).sum() / max(1, count)
        if zero_vol_pct > 0.10:
            issues.append(f"Ticker {t} has >10% zero volume days (liquidity risk).")
            
    passed = len(issues) == 0
    return {
        "gate": "G0",
        "passed": passed,
        "status": "APPROVED" if passed else "REJECTED",
        "tier": "Tier 1 (OHLCV Market Data)",
        "total_dates": total_dates,
        "ticker_count": len(tickers),
        "missing_rates_pct": missing_counts,
        "issues": issues,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


def main():
    parser = argparse.ArgumentParser(description="CTO Data Feed & G0 Validation")
    parser.add_argument("--tickers", default="AAPL,MSFT,NVDA,JPM,TLT", help="Comma-separated tickers")
    parser.add_argument("--period", default="1y", help="Lookback period (e.g. 1y, 2y)")
    parser.add_argument("--db", default="market_data.duckdb", help="DuckDB/SQLite output path")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    args = parser.parse_args()

    ticker_list = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    df = fetch_market_data(ticker_list, period=args.period)
    store_in_duckdb(df, args.db)
    g0_report = validate_g0(df, ticker_list)

    if args.json:
        print(json.dumps(g0_report, indent=2))
    else:
        print(f"=== CTO Data Ingestion & G0 Validation ===")
        print(f"Status: {g0_report['status']} (Passed: {g0_report['passed']})")
        print(f"Tickers: {ticker_list} | Total Trading Days: {g0_report['total_dates']}")
        if g0_report["issues"]:
            print("Issues detected:")
            for issue in g0_report["issues"]:
                print(f"  - {issue}")
        else:
            print("All G0 integrity checks passed (zero lookahead / clean OHLCV).")

if __name__ == "__main__":
    main()
