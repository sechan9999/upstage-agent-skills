#!/usr/bin/env python3
"""analyze_excel.py -- deterministic Excel/CSV structure & quality diagnostic.

Usage:
    python analyze_excel.py FILE.xlsx [--sheet NAME] [--json] [--out-dir DIR]
    python analyze_excel.py FILE.csv  [--json]

Dependencies: pandas, openpyxl (pip install pandas openpyxl).

What this computes (see skills/excel-analyzer/SKILL.md for how the assistant
should turn this into a report -- this docstring only covers what the code
actually does):

1. Header / data-region detection (per sheet)
   Raw sheet is read with no assumed header (header=None). The first 15 rows
   are scored as header candidates: a row scores higher when more of its
   cells are non-null, unique strings, and when the rows immediately below it
   contain at least one numeric-looking cell in the same columns.
   The highest-scoring row becomes the header; rows above it are kept as
   "preamble" (titles, or summary blocks). Trailing blank rows are stripped,
   and mid-table blank rows do NOT cause premature truncation.

2. Footer total row detection & isolation
   If the bottom row of the data region matches a total/summary label
   (합계/총계/total/sum etc.), it is separated from the data rows to prevent
   skewing mean, max, and variance, and is routed to cross-validation.

3. Column profiling
   For every column: inferred type (numeric / categorical / date-like),
   missing count and percentage, format errors (non-numeric values in mostly
   numeric columns), and identification of ID-like columns.

4. Duplicates
   Full-row duplicates (`DataFrame.duplicated()`), plus duplicates on the
   best identifier column.

5. Summary statistics
   count, mean, std, min, q1, median, q3, max for every numeric metric column.

6. 4-Quartile distribution analysis (Q1 ~ Q4)
   For up to 3 numeric metric columns (highest coefficient of variation,
   excluding pure IDs/years), full 4-quartile division is computed:
   - Q1: Bottom 25% (min to Q1)
   - Q2: Lower-Middle 25% (Q1 to Median)
   - Q3: Upper-Middle 25% (Median to Q3)
   - Q4: Top 25% (Q3 to max)
   With boundary ranges, record counts, and sample row identifiers.

7. Group comparison (부서/기간/항목별 비교)
   Categorical columns with 2-20 unique values grouped with up to 3 numeric metrics.

8. Outlier / anomaly detection
   Standard IQR rule (Q1 - 1.5*IQR, Q3 + 1.5*IQR).

9. Summary-vs-raw cross-validation
   Both preamble totals (top) and footer totals (bottom) are cross-checked
   against computed column sums.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

MAX_HEADER_SCAN_ROWS = 15
MAX_QUARTILE_COLUMNS = 3
MAX_GROUPBY_CATEGORICAL_COLUMNS = 2
MAX_GROUPBY_NUMERIC_COLUMNS = 3
GROUPBY_MIN_UNIQUE = 2
GROUPBY_MAX_UNIQUE = 20
ID_COLUMN_UNIQUE_RATIO = 0.9

TOTAL_LABEL_RE = re.compile(
    r"^\\s*(합계|총계|총합|소계|전체합계|누계|total|sum|grand total|subtotal)\\s*[:：]?\\s*$",
    re.IGNORECASE,
)

ID_NAME_PATTERNS = re.compile(
    r"(id|코드|사번|고객번호|순번|번호|no|주민|사업자|일련번호)",
    re.IGNORECASE,
)

ID_SAMPLE_NAME_PATTERNS = re.compile(
    r"(성명|이름|고객명|사원명|직원명|담당자|업체명|품목명|상품명|회사명|항목명|name|title)",
    re.IGNORECASE,
)


def read_sheets(path: str, sheet: Optional[str]) -> Dict[str, pd.DataFrame]:
    if path.lower().endswith(".csv"):
        return {"Sheet1": pd.read_csv(path, header=None, dtype=object)}
    xls = pd.ExcelFile(path)
    names = [sheet] if sheet else xls.sheet_names
    return {name: xls.parse(name, header=None, dtype=object) for name in names}


def _is_numeric_like(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return not pd.isna(value)
    s = str(value).strip().replace(",", "")
    if s == "":
        return False
    try:
        float(s)
        return True
    except ValueError:
        return False


def score_header_candidate(raw: pd.DataFrame, row_idx: int) -> float:
    row = raw.iloc[row_idx]
    non_null = row.dropna()
    if len(non_null) == 0:
        return -1.0
    non_null_str = [v for v in non_null if isinstance(v, str) and v.strip()]
    uniqueness = len(set(non_null_str)) / max(1, len(non_null_str))
    string_ratio = len(non_null_str) / len(non_null)

    below = raw.iloc[row_idx + 1: row_idx + 4]
    numeric_below = 0
    if not below.empty:
        for col in row.index:
            col_vals = below[col].dropna()
            if any(_is_numeric_like(v) for v in col_vals):
                numeric_below += 1
    numeric_signal = min(1.0, numeric_below / max(1, len(row.index)))

    return len(non_null) * (0.5 + 0.3 * string_ratio + 0.2 * uniqueness) + numeric_signal * 5


def detect_header_and_data(raw: pd.DataFrame) -> Tuple[int, int, int]:
    """Returns (header_row_idx, data_start_idx, data_end_idx_exclusive)."""
    n_scan = min(MAX_HEADER_SCAN_ROWS, len(raw))
    if n_scan == 0:
        return 0, 0, 0
    scores = [score_header_candidate(raw, i) for i in range(n_scan)]
    header_idx = max(range(n_scan), key=lambda i: scores[i]) if scores else 0

    data_start = header_idx + 1
    # Strip trailing completely blank rows from the end, but do NOT truncate on a single mid-table blank row!
    last_idx = len(raw)
    while last_idx > data_start and raw.iloc[last_idx - 1].isna().all():
        last_idx -= 1
    data_end = last_idx

    return header_idx, data_start, data_end


def build_dataframe(raw: pd.DataFrame, header_idx: int, data_start: int, data_end: int) -> Tuple[pd.DataFrame, Optional[pd.Series]]:
    header = raw.iloc[header_idx].tolist()
    header = [str(h).strip() if h is not None and str(h).strip() else f"col_{i}" for i, h in enumerate(header)]
    seen: Dict[str, int] = {}
    deduped = []
    for h in header:
        if h in seen:
            seen[h] += 1
            deduped.append(f"{h}_{seen[h]}")
        else:
            seen[h] = 0
            deduped.append(h)

    data = raw.iloc[data_start:data_end].copy()
    data.columns = deduped

    # Drop completely blank rows in the middle
    data = data.dropna(how="all").reset_index(drop=True)

    # Check for footer total row at the bottom
    footer_row = None
    if len(data) > 0:
        last_row = data.iloc[-1]
        for val in last_row.dropna()[:2]: # check first or second cell
            val_str = str(val).strip()
            if TOTAL_LABEL_RE.match(val_str):
                footer_row = last_row
                data = data.iloc[:-1].reset_index(drop=True)
                break

    return data, footer_row


def coerce_numeric(series: pd.Series) -> pd.Series:
    cleaned = series.astype(str).str.replace(",", "", regex=False).str.strip()
    return pd.to_numeric(cleaned, errors="coerce")


def profile_columns(df: pd.DataFrame) -> Dict[str, dict]:
    profile = {}
    n = len(df)
    for col in df.columns:
        series = df[col]
        non_null = series.dropna()
        missing = n - len(non_null)
        numeric = coerce_numeric(series)
        numeric_non_null = numeric.dropna()
        is_mostly_numeric = len(non_null) > 0 and len(numeric_non_null) / len(non_null) > 0.5

        format_errors = []
        if is_mostly_numeric:
            bad_values = non_null[~non_null.index.isin(numeric_non_null.index)]
            format_errors = [str(v) for v in bad_values.tolist()][:20]

        is_id_like = False
        if len(non_null) > 0:
            if ID_NAME_PATTERNS.search(str(col)) or (non_null.nunique() / len(non_null) >= ID_COLUMN_UNIQUE_RATIO and len(non_null) > 10):
                is_id_like = True

        col_type = "numeric" if is_mostly_numeric else "categorical"

        profile[col] = {
            "type": col_type,
            "is_id_like": is_id_like,
            "unique_count": int(non_null.nunique()),
            "missing_count": int(missing),
            "missing_pct": round(missing / n * 100, 1) if n else 0.0,
            "format_error_count": len(format_errors),
            "format_error_samples": format_errors,
        }
    return profile


def find_duplicates(df: pd.DataFrame, profile: Dict[str, dict]) -> dict:
    full_dup = int(df.duplicated().sum())
    id_col_dup = None

    # Search for candidate ID column
    candidate_id = None
    for col, info in profile.items():
        if info["is_id_like"]:
            candidate_id = col
            break
    if not candidate_id and len(df.columns) > 0:
        candidate_id = df.columns[0]

    if candidate_id:
        non_null = df[candidate_id].dropna()
        if len(non_null) > 0 and (non_null.nunique() / len(non_null)) >= 0.8:
            id_col_dup = {
                "column": candidate_id,
                "duplicate_count": int(non_null.duplicated().sum()),
            }

    return {"full_row_duplicates": full_dup, "id_like_column_duplicates": id_col_dup}


def summary_statistics(df: pd.DataFrame, profile: Dict[str, dict]) -> Dict[str, dict]:
    stats = {}
    for col, info in profile.items():
        if info["type"] != "numeric":
            continue
        numeric = coerce_numeric(df[col]).dropna()
        if numeric.empty:
            continue
        stats[col] = {
            "count": int(numeric.count()),
            "mean": round(float(numeric.mean()), 2),
            "std": round(float(numeric.std()), 2) if numeric.count() > 1 else 0.0,
            "min": round(float(numeric.min()), 2),
            "q1": round(float(numeric.quantile(0.25)), 2),
            "median": round(float(numeric.median()), 2),
            "q3": round(float(numeric.quantile(0.75)), 2),
            "max": round(float(numeric.max()), 2),
            "is_id_like": info.get("is_id_like", False),
        }
    return stats


def _identifier_column(df: pd.DataFrame, profile: Dict[str, dict]) -> Optional[str]:
    # Priority 1: High uniqueness column with name matching ID_SAMPLE_NAME_PATTERNS
    for col in df.columns:
        if ID_SAMPLE_NAME_PATTERNS.search(str(col)):
            return col

    # Priority 2: High uniqueness categorical or ID-like column (0.5 <= ratio <= 1.0)
    for col, info in profile.items():
        n = len(df)
        ratio = (info["unique_count"] / n) if n else 0
        if 0.5 <= ratio <= 1.0:
            return col

    # Priority 3: First categorical column
    for col, info in profile.items():
        if info["type"] == "categorical":
            return col
    return None


def quartile_analysis(df: pd.DataFrame, profile: Dict[str, dict], stats: Dict[str, dict]) -> Dict[str, dict]:
    # Filter out pure ID columns and year columns from quartile analysis
    candidate_cols = [
        col for col, s in stats.items()
        if not s.get("is_id_like", False) and not (s["min"] >= 1950 and s["max"] <= 2100 and s["std"] < 30)
    ]
    if not candidate_cols:
        candidate_cols = list(stats.keys())

    id_col = _identifier_column(df, profile)

    def cv(col: str) -> float:
        s = stats[col]
        return abs(s["std"] / s["mean"]) if s["mean"] else 0.0

    candidate_cols.sort(key=cv, reverse=True)
    chosen = candidate_cols[:MAX_QUARTILE_COLUMNS]

    result = {}
    for col in chosen:
        numeric = coerce_numeric(df[col])
        s = stats[col]
        min_v = s["min"]
        q1 = s["q1"]
        median = s["median"]
        q3 = s["q3"]
        max_v = s["max"]

        mask_q1 = numeric <= q1
        mask_q2 = (numeric > q1) & (numeric <= median)
        mask_q3 = (numeric > median) & (numeric <= q3)
        mask_q4 = numeric > q3

        def get_sample_ids(mask: pd.Series) -> List[str]:
            if id_col:
                return df.loc[mask, id_col].dropna().astype(str).tolist()[:10]
            return [f"row_{i}" for i in df.index[mask]][:10]

        result[col] = {
            "metric_column": col,
            "identifier_column": id_col or "row_index",
            "quartiles": {
                "Q1_bottom": {
                    "range": f"{min_v} ~ {q1}",
                    "min": min_v,
                    "max": q1,
                    "count": int(mask_q1.sum()),
                    "pct": round(mask_q1.sum() / max(1, len(numeric.dropna())) * 100, 1),
                    "samples": get_sample_ids(mask_q1),
                },
                "Q2_lower_mid": {
                    "range": f"{q1} ~ {median}",
                    "min": q1,
                    "max": median,
                    "count": int(mask_q2.sum()),
                    "pct": round(mask_q2.sum() / max(1, len(numeric.dropna())) * 100, 1),
                    "samples": get_sample_ids(mask_q2),
                },
                "Q3_upper_mid": {
                    "range": f"{median} ~ {q3}",
                    "min": median,
                    "max": q3,
                    "count": int(mask_q3.sum()),
                    "pct": round(mask_q3.sum() / max(1, len(numeric.dropna())) * 100, 1),
                    "samples": get_sample_ids(mask_q3),
                },
                "Q4_top": {
                    "range": f"{q3} ~ {max_v}",
                    "min": q3,
                    "max": max_v,
                    "count": int(mask_q4.sum()),
                    "pct": round(mask_q4.sum() / max(1, len(numeric.dropna())) * 100, 1),
                    "samples": get_sample_ids(mask_q4),
                },
            },
            "boundaries": {"min": min_v, "q1": q1, "median": median, "q3": q3, "max": max_v},
        }
    return result


def group_comparison(df: pd.DataFrame, profile: Dict[str, dict]) -> Dict[str, dict]:
    categorical_cols = []
    for col, info in profile.items():
        if info["type"] != "categorical" or info.get("is_id_like", False):
            continue
        nunique = df[col].dropna().nunique()
        if GROUPBY_MIN_UNIQUE <= nunique <= GROUPBY_MAX_UNIQUE:
            categorical_cols.append((col, nunique))
    categorical_cols.sort(key=lambda x: x[1])
    categorical_cols = [c for c, _ in categorical_cols[:MAX_GROUPBY_CATEGORICAL_COLUMNS]]

    numeric_cols = [
        c for c, info in profile.items()
        if info["type"] == "numeric" and not info.get("is_id_like", False)
    ][:MAX_GROUPBY_NUMERIC_COLUMNS]

    result = {}
    for cat_col in categorical_cols:
        group_result = {}
        working = df[[cat_col] + numeric_cols].copy()
        for ncol in numeric_cols:
            working[ncol] = coerce_numeric(working[ncol])
        grouped = working.groupby(cat_col, dropna=True)
        for ncol in numeric_cols:
            agg = grouped[ncol].agg(["sum", "mean", "count"])
            group_result[ncol] = {
                str(idx): {
                    "sum": round(float(row["sum"]), 2) if pd.notna(row["sum"]) and row["count"] > 0 else None,
                    "mean": round(float(row["mean"]), 2) if pd.notna(row["mean"]) else None,
                    "count": int(row["count"]),
                }
                for idx, row in agg.iterrows()
            }
        result[cat_col] = group_result
    return result


def detect_outliers(df: pd.DataFrame, profile: Dict[str, dict]) -> Dict[str, list]:
    id_col = _identifier_column(df, profile)
    outliers = {}
    for col, info in profile.items():
        if info["type"] != "numeric" or info.get("is_id_like", False):
            continue
        numeric = coerce_numeric(df[col])
        non_null = numeric.dropna()
        if len(non_null) < 4:
            continue
        q1 = non_null.quantile(0.25)
        q3 = non_null.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        mask = (numeric < lower) | (numeric > upper)
        flagged = df.index[mask.fillna(False)]
        items = []
        for idx in flagged[:20]:
            label = str(df.loc[idx, id_col]) if id_col else f"row_{idx}"
            items.append({"row": label, "value": round(float(numeric.loc[idx]), 2)})
        if items:
            outliers[col] = items
    return outliers


def cross_validate_totals(
    raw: pd.DataFrame,
    header_idx: int,
    df: pd.DataFrame,
    profile: Dict[str, dict],
    footer_row: Optional[pd.Series]
) -> List[dict]:
    checks = []

    # 1. Check Preamble Totals (above header)
    preamble = raw.iloc[:header_idx]
    for i in range(len(preamble)):
        row = preamble.iloc[i]
        first_cell = row.iloc[0] if len(row) else None
        if not isinstance(first_cell, str) or not TOTAL_LABEL_RE.match(first_cell):
            continue
        for col_idx in range(1, len(row)):
            stated = row.iloc[col_idx]
            if not _is_numeric_like(stated):
                continue
            stated_val = float(str(stated).replace(",", ""))
            if col_idx < len(df.columns):
                target_col = df.columns[col_idx]
                if profile.get(target_col, {}).get("type") == "numeric":
                    computed = coerce_numeric(df[target_col]).sum()
                    delta = round(float(computed) - stated_val, 2)
                    checks.append({
                        "location": "preamble_top",
                        "label": first_cell.strip(),
                        "column": target_col,
                        "stated_total": stated_val,
                        "computed_total": round(float(computed), 2),
                        "delta": delta,
                        "match": abs(delta) < 0.01,
                    })

    # 2. Check Footer Total Row (bottom)
    if footer_row is not None:
        label = "합계(하단)"
        for val in footer_row.dropna()[:2]:
            if TOTAL_LABEL_RE.match(str(val).strip()):
                label = str(val).strip()
                break
        for col in df.columns:
            if profile.get(col, {}).get("type") == "numeric":
                stated = footer_row.get(col)
                if _is_numeric_like(stated):
                    stated_val = float(str(stated).replace(",", ""))
                    computed = coerce_numeric(df[col]).sum()
                    delta = round(float(computed) - stated_val, 2)
                    checks.append({
                        "location": "footer_bottom",
                        "label": label,
                        "column": col,
                        "stated_total": stated_val,
                        "computed_total": round(float(computed), 2),
                        "delta": delta,
                        "match": abs(delta) < 0.01,
                    })

    return checks


def analyze_sheet(name: str, raw: pd.DataFrame) -> dict:
    header_idx, data_start, data_end = detect_header_and_data(raw)
    df, footer_row = build_dataframe(raw, header_idx, data_start, data_end)
    profile = profile_columns(df)
    duplicates = find_duplicates(df, profile)
    stats = summary_statistics(df, profile)
    quartiles = quartile_analysis(df, profile, stats)
    groups = group_comparison(df, profile)
    outliers = detect_outliers(df, profile)
    cross_checks = cross_validate_totals(raw, header_idx, df, profile, footer_row)

    return {
        "sheet": name,
        "header_row": header_idx,
        "data_rows": len(df),
        "data_columns": len(df.columns),
        "has_footer_total_isolated": footer_row is not None,
        "columns": profile,
        "duplicates": duplicates,
        "summary_statistics": stats,
        "quartile_analysis": quartiles,
        "group_comparison": groups,
        "outliers": outliers,
        "summary_vs_raw_cross_check": cross_checks,
    }


def analyze(path: str, sheet: Optional[str]) -> dict:
    sheets = read_sheets(path, sheet)
    results = [analyze_sheet(name, raw) for name, raw in sheets.items()]
    return {"file": path, "sheets": results}


def format_report(result: dict) -> str:
    lines = [f"=== Excel Analysis Report: {result['file']} ==="]
    for sheet in result["sheets"]:
        lines.append("")
        lines.append(f"--- Sheet: {sheet['sheet']} ---")
        footer_info = " (하단 합계행 분리됨)" if sheet.get("has_footer_total_isolated") else ""
        lines.append(f"Header row: {sheet['header_row']} | Data rows: {sheet['data_rows']} | Columns: {sheet['data_columns']}{footer_info}")

        lines.append("")
        lines.append("Columns:")
        for col, info in sheet["columns"].items():
            id_flag = " [ID-like]" if info.get("is_id_like") else ""
            lines.append(
                f"  - {col}: {info['type']}{id_flag}, missing {info['missing_count']} ({info['missing_pct']}%), "
                f"unique {info['unique_count']}, format errors {info['format_error_count']}"
            )
            if info["format_error_samples"]:
                lines.append(f"      format error samples: {info['format_error_samples']}")

        dup = sheet["duplicates"]
        lines.append("")
        lines.append(f"Duplicates: full-row={dup['full_row_duplicates']}"
                      + (f", id-column({dup['id_like_column_duplicates']['column']})={dup['id_like_column_duplicates']['duplicate_count']}"
                         if dup["id_like_column_duplicates"] else ""))

        lines.append("")
        lines.append("Summary statistics:")
        for col, s in sheet["summary_statistics"].items():
            lines.append(f"  - {col}: count={s['count']} mean={s['mean']} std={s['std']} min={s['min']} "
                         f"q1={s['q1']} median={s['median']} q3={s['q3']} max={s['max']}")

        lines.append("")
        lines.append("Quartile analysis (4-Quartile Q1~Q4 Distribution):")
        for col, qdata in sheet["quartile_analysis"].items():
            lines.append(f"  [Metric: {col} | Ref ID: {qdata['identifier_column']}]")
            for q_name, q in qdata["quartiles"].items():
                lines.append(f"    - {q_name:13s} ({q['range']}): {q['count']} rows ({q['pct']}%) | samples: {q['samples']}")

        lines.append("")
        lines.append("Group comparison:")
        for cat_col, ncols in sheet["group_comparison"].items():
            lines.append(f"  by {cat_col}:")
            for ncol, groups in ncols.items():
                lines.append(f"    {ncol}: {groups}")

        lines.append("")
        lines.append("Outliers (IQR rule):")
        for col, items in sheet["outliers"].items():
            lines.append(f"  - {col}: {items}")

        lines.append("")
        lines.append("Summary-vs-raw cross-check:")
        if not sheet["summary_vs_raw_cross_check"]:
            lines.append("  (no summary/total row detected)")
        for check in sheet["summary_vs_raw_cross_check"]:
            status = "OK" if check["match"] else "MISMATCH"
            loc = f"[{check['location']}]"
            lines.append(
                f"  - [{status}] {loc} '{check['label']}' {check['column']}: "
                f"stated={check['stated_total']} computed={check['computed_total']} delta={check['delta']}"
            )
    return "\\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", help="Path to .xlsx/.xls/.csv file")
    parser.add_argument("--sheet", help="Analyze only this sheet name (default: all sheets)")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of a text report")
    args = parser.parse_args(argv)

    result = analyze(args.file, args.sheet)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print(format_report(result))

    return 0


if __name__ == "__main__":
    sys.exit(main())
