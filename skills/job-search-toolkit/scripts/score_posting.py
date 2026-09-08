#!/usr/bin/env python3
"""score_posting.py -- deterministic resume/posting coverage scorer.

Usage:
    python score_posting.py RESUME.txt POSTING.txt [--lexicon LEXICON.txt] [--json]

Computes deterministic keyword & requirement coverage between a resume and job posting.
Supports English (Latin tokens), Korean, and Japanese (surface chunking & lexicon matching).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

PROXIMITY_WINDOW = 250  # chars, each side, for required/preferred marker matching

REQUIRED_MARKERS = [
    "required", "require", "requires", "must", "mandatory", "essential",
    "minimum qualification", "minimum qualifications", "need to have",
    "필수", "필수사항", "필수요건", "필수조건",
    "必須", "必須事項", "必須要件", "必須条件", "必須スキル",
    "求めるスキル", "求めるスキル・経験", "応募要件", "応募資格", "必要条件",
]

PREFERRED_MARKERS = [
    "preferred", "prefer", "nice to have", "nice-to-have", "bonus",
    "plus", "a plus", "desirable", "advantageous",
    "우대", "우대사항", "우대조건", "선호",
    "歓迎", "歓迎要件", "歓迎条件", "歓迎スキル", "あれば尚可",
    "尚可", "求める人物像", "優遇", "歓迎する経験・スキル",
]

MARKER_WORDS = set(REQUIRED_MARKERS) | set(PREFERRED_MARKERS)

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "of", "to", "in",
    "on", "at", "for", "with", "by", "as", "is", "are", "was", "were", "be",
    "been", "being", "this", "that", "these", "those", "it", "its", "we",
    "you", "your", "our", "their", "will", "would", "should", "can", "could",
    "may", "might", "must", "have", "has", "had", "do", "does", "did",
    "not", "no", "yes", "from", "into", "about", "than", "so", "such",
    "who", "whom", "which", "what", "when", "where", "why", "how",
    "all", "any", "each", "other", "some", "more", "most", "own", "same",
    "job", "role", "position", "team", "company", "work", "working",
}

COMMON_ACRONYMS = {
    "API", "SQL", "AWS", "GCP", "ML", "AI", "UI", "UX", "CSS", "HTML",
    "REST", "CI", "CD", "QA", "PM", "HR", "IT", "OOP", "SDK", "CLI", "JSON",
    "XML", "HTTP", "HTTPS", "SaaS", "PaaS", "IaaS", "ETL", "NLP", "CRM",
    "ERP", "KPI", "ROI", "B2B", "B2C", "MVP", "SRE", "DBA", "OS", "IDE",
    "NOSQL", "SQL", "GPU", "CPU", "RAM", "URL", "URI", "USA", "UK", "EU",
    "LLM", "LLMS", "RAG", "NLU", "GPT", "AGI", "MLOPS", "LLMOPS",
}

WORK_ARRANGEMENT_TERMS = {
    "remote": "remote",
    "원격": "remote",
    "재택": "remote",
    "재택근무": "remote",
    "在宅": "remote",
    "在宅勤務": "remote",
    "フルリモート": "remote",
    "リモート": "remote",
    "リモートワーク": "remote",
    "hybrid": "hybrid",
    "하이브리드": "hybrid",
    "ハイブリッド": "hybrid",
    "onsite": "onsite",
    "on-site": "onsite",
    "in-office": "onsite",
    "출근": "onsite",
    "사무실 출근": "onsite",
    "出社": "onsite",
    "常駐": "onsite",
    "オフィス出社": "onsite",
}

WORK_ARRANGEMENT_DISQUALIFIERS = {
    "retrieval", "search", "cloud", "engine", "encryption", "vehicle",
    "algorithm", "database", "architecture", "model", "index", "query",
    "검색", "클라우드", "엔진", "암호화", "차량", "알고리즘", "데이터베이스",
    "아키텍처", "모델", "인덱스", "쿼리",
    "検索", "クラウド", "暗号化", "車両", "クエリ",
}
WORK_ARRANGEMENT_GUARD_WINDOW = 30  # chars, each side

HANGUL_RE = re.compile(r"[가-힣]")
JAPANESE_RE = re.compile(r"[぀-ゟ゠-ヿ一-鿿]")
LATIN_TOKEN_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9+#./-]*\b")
CJK_SPLIT_RE = re.compile(r'[\s,;:!?()\[\]{}`~/|·•\-–—、。「」『』【】・"\']+')
ALLCAPS_RE = re.compile(r"^[A-Z]{2,6}$")

SALARY_RE = re.compile(
    r"(\$\s?\d[\d,]*(?:\.\d+)?\s?(?:-|~|to)\s?\$?\s?\d[\d,]*(?:\.\d+)?"
    r"|\$\s?\d[\d,]*(?:\.\d+)?k?\+?"
    r"|₩\s?\d[\d,]*"
    r"|연봉\s?\d[\d,]*\s?만\s?원?(?:\s?(?:-|~)\s?\d[\d,]*\s?만\s?원?)?"
    r"|\d[\d,]*\s?만\s?원"
    r"|¥\s?\d[\d,]*(?:\.\d+)?"
    r"|年収\s?\d[\d,]*\s?万\s?円?(?:\s?(?:-|~|〜)\s?\d[\d,]*\s?万\s?円?)?"
    r"|\d[\d,]*\s?万\s?円"
    r"|月給\s?\d[\d,]*\s?万\s?円?)",
    re.IGNORECASE,
)

YEARS_EXPERIENCE_RE = re.compile(
    r"(\d+\+?\s?(?:-|~)?\s?\d*\+?\s?(?:years?|yrs?)\s?(?:of\s?)?(?:experience)?"
    r"|\d+\+?\s?년\s?(?:이상)?\s?(?:경력)?"
    r"|\d+\+?\s?年\s?(?:以上)?\s?(?:の\s?)?(?:実務経験|経験)?)",
    re.IGNORECASE,
)


@dataclass
class TermOccurrence:
    term: str
    positions: List[int] = field(default_factory=list)


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_lexicon(path: Optional[str]) -> List[str]:
    if not path:
        return []
    phrases = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            phrases.append(line)
    return phrases


def contains_cjk(text: str) -> bool:
    return bool(HANGUL_RE.search(text) or JAPANESE_RE.search(text))


def extract_english_tokens(text: str) -> Dict[str, List[int]]:
    occ: Dict[str, List[int]] = {}
    for m in LATIN_TOKEN_RE.finditer(text):
        raw = m.group(0)
        if ALLCAPS_RE.match(raw) and raw.upper() not in COMMON_ACRONYMS:
            continue  # handled separately as unrecognized
        term = raw.lower()
        if term in STOPWORDS or term in MARKER_WORDS:
            continue
        if len(term) < 2:
            continue
        occ.setdefault(term, []).append(m.start())
    return occ


def extract_cjk_chunks(text: str) -> Dict[str, List[int]]:
    occ: Dict[str, List[int]] = {}
    pos = 0
    for chunk in CJK_SPLIT_RE.split(text):
        idx = text.find(chunk, pos) if chunk else -1
        if chunk:
            pos = idx + len(chunk)
        if not chunk:
            continue
        if not contains_cjk(chunk):
            continue
        if chunk in MARKER_WORDS:
            continue
        if len(chunk) < 2:
            continue
        occ.setdefault(chunk, []).append(idx if idx >= 0 else 0)
    return occ


def extract_lexicon_matches(text: str, lexicon: List[str]) -> Dict[str, List[int]]:
    occ: Dict[str, List[int]] = {}
    for phrase in lexicon:
        if contains_cjk(phrase):
            search_text = text
            needle = phrase
            positions = []
            start = 0
            while True:
                idx = search_text.find(needle, start)
                if idx == -1:
                    break
                positions.append(idx)
                start = idx + len(needle)
        else:
            positions = []
            start = 0
            lower_text = text.lower()
            needle = phrase.lower()
            while True:
                idx = lower_text.find(needle, start)
                if idx == -1:
                    break
                positions.append(idx)
                start = idx + len(needle)
        if positions:
            occ[phrase if contains_cjk(phrase) else phrase.lower()] = positions
    return occ


def extract_unrecognized(text: str, lexicon: List[str]) -> Set[str]:
    lexicon_upper = {p.upper() for p in lexicon}
    unrecognized = set()
    for m in LATIN_TOKEN_RE.finditer(text):
        raw = m.group(0)
        if ALLCAPS_RE.match(raw) and raw.upper() not in COMMON_ACRONYMS and raw.upper() not in lexicon_upper:
            unrecognized.add(raw)
    return unrecognized


def extract_terms(text: str, lexicon: List[str]) -> Dict[str, List[int]]:
    terms: Dict[str, List[int]] = {}
    terms.update(extract_english_tokens(text))
    if contains_cjk(text):
        for k, v in extract_cjk_chunks(text).items():
            terms.setdefault(k, []).extend(v)
    for k, v in extract_lexicon_matches(text, lexicon).items():
        terms.setdefault(k, []).extend(v)
    return terms


_MARKER_PATTERN_CACHE: Dict[str, "re.Pattern[str]"] = {}


def _marker_pattern(marker: str) -> "re.Pattern[str]":
    # Word-boundary anchored so a bare marker like "require" doesn't false-match
    # inside an unrelated word like "requirements" (a normal noun in flowing
    # job-description prose, not a "Required:" section signal). Multi-word/
    # glued Korean marker forms (필수사항, 필수요건, ...) are listed as their
    # own separate marker strings, so boundary-anchoring the shorter "필수"
    # form doesn't stop those from matching -- they match via their own entry.
    if marker not in _MARKER_PATTERN_CACHE:
        _MARKER_PATTERN_CACHE[marker] = re.compile(r"\b" + re.escape(marker.lower()) + r"\b")
    return _MARKER_PATTERN_CACHE[marker]


def find_marker_positions(lower_text: str, markers: List[str]) -> List[int]:
    positions = []
    for marker in markers:
        for m in _marker_pattern(marker).finditer(lower_text):
            positions.append(m.start())
    return positions


def _nearest_distance(term_positions: List[int], marker_positions: List[int]) -> Optional[int]:
    if not marker_positions:
        return None
    best = None
    for tp in term_positions:
        for mp in marker_positions:
            d = abs(tp - mp)
            if best is None or d < best:
                best = d
    return best


def classify_category(
    term_positions: List[int],
    required_positions: List[int],
    preferred_positions: List[int],
) -> str:
    req_dist = _nearest_distance(term_positions, required_positions)
    pref_dist = _nearest_distance(term_positions, preferred_positions)

    req_in_window = req_dist is not None and req_dist <= PROXIMITY_WINDOW
    pref_in_window = pref_dist is not None and pref_dist <= PROXIMITY_WINDOW

    if req_in_window and pref_in_window:
        return "required" if req_dist <= pref_dist else "preferred"
    if req_in_window:
        return "required"
    if pref_in_window:
        return "preferred"
    return "unmarked"


def parse_salary(text: str) -> Optional[str]:
    m = SALARY_RE.search(text)
    return m.group(0).strip() if m else None


def parse_years_experience(text: str) -> Optional[str]:
    m = YEARS_EXPERIENCE_RE.search(text)
    return m.group(0).strip() if m else None


def parse_work_arrangement(text: str) -> Optional[str]:
    lower = text.lower()
    for term, normalized in WORK_ARRANGEMENT_TERMS.items():
        start = 0
        term_l = term.lower()
        while True:
            idx = lower.find(term_l, start)
            if idx == -1:
                break
            window = lower[max(0, idx - WORK_ARRANGEMENT_GUARD_WINDOW): idx + len(term_l) + WORK_ARRANGEMENT_GUARD_WINDOW]
            if not any(dq in window for dq in WORK_ARRANGEMENT_DISQUALIFIERS):
                context = text[max(0, idx - 20): idx + len(term) + 20].strip()
                return f"{normalized} (matched \"{term}\", context: \"{context}\")"
            start = idx + len(term_l)
    return None


def score(resume_text: str, posting_text: str, lexicon: List[str]) -> dict:
    posting_terms = extract_terms(posting_text, lexicon)
    resume_terms = extract_terms(resume_text, lexicon)

    posting_set = set(posting_terms.keys())
    resume_set = set(resume_terms.keys())

    matched = sorted(posting_set & resume_set)
    gap = sorted(posting_set - resume_set)

    lower_posting = posting_text.lower()
    required_positions = find_marker_positions(lower_posting, REQUIRED_MARKERS)
    preferred_positions = find_marker_positions(lower_posting, PREFERRED_MARKERS)

    categories: Dict[str, str] = {}
    for term, positions in posting_terms.items():
        categories[term] = classify_category(positions, required_positions, preferred_positions)

    category_totals = {"required": 0, "preferred": 0, "unmarked": 0}
    category_matched = {"required": 0, "preferred": 0, "unmarked": 0}
    for term in posting_set:
        cat = categories[term]
        category_totals[cat] += 1
        if term in resume_set:
            category_matched[cat] += 1

    overall_total = len(posting_set)
    overall_matched = len(matched)
    overall_pct = (overall_matched / overall_total * 100) if overall_total else 0.0

    category_report = {}
    for cat in ("required", "preferred", "unmarked"):
        total = category_totals[cat]
        m = category_matched[cat]
        pct = (m / total * 100) if total else 0.0
        category_report[cat] = {"matched": m, "total": total, "pct": round(pct, 1)}

    gap_by_category = {"required": [], "preferred": [], "unmarked": []}
    for term in gap:
        gap_by_category[categories[term]].append(term)
    for cat in gap_by_category:
        gap_by_category[cat].sort()

    unrecognized = sorted(extract_unrecognized(posting_text, lexicon))

    constraints = {
        "salary": parse_salary(posting_text) or "NOT STATED",
        "work_arrangement": parse_work_arrangement(posting_text) or "NOT STATED",
        "years_experience": parse_years_experience(posting_text) or "NOT STATED",
    }

    return {
        "overall_coverage_pct": round(overall_pct, 1),
        "overall_matched": overall_matched,
        "overall_total": overall_total,
        "category_coverage": category_report,
        "matched_terms": matched,
        "gap_terms": gap,
        "gap_terms_by_category": gap_by_category,
        "constraints": constraints,
        "unrecognized_posting_language": unrecognized,
    }


def format_report(result: dict) -> str:
    lines = []
    lines.append("=== Posting Score Report ===")
    lines.append(
        f"Overall coverage: {result['overall_coverage_pct']}% "
        f"({result['overall_matched']}/{result['overall_total']} matched)"
    )
    lines.append("")
    lines.append("Category coverage:")
    for cat in ("required", "preferred", "unmarked"):
        c = result["category_coverage"][cat]
        lines.append(f"  {cat:10s} {c['matched']}/{c['total']} ({c['pct']}%)")
    lines.append("")
    lines.append(f"Matched terms ({len(result['matched_terms'])}):")
    for t in result["matched_terms"]:
        lines.append(f"  - {t}")
    lines.append("")
    lines.append(f"Gap terms ({len(result['gap_terms'])}):")
    for cat in ("required", "preferred", "unmarked"):
        terms = result["gap_terms_by_category"][cat]
        if not terms:
            continue
        lines.append(f"  {cat}:")
        for t in terms:
            lines.append(f"    - {t}")
    lines.append("")
    lines.append("Constraints:")
    for k, v in result["constraints"].items():
        lines.append(f"  {k}: {v}")
    lines.append("")
    lines.append(
        f"Unrecognized posting language ({len(result['unrecognized_posting_language'])}, "
        f"not scored):"
    )
    for t in result["unrecognized_posting_language"]:
        lines.append(f"  - {t}")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("resume", help="Path to resume/CV plain text file")
    parser.add_argument("posting", help="Path to job posting plain text file")
    parser.add_argument("--lexicon", help="Path to lexicon file (one phrase per line)")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of a text report")
    args = parser.parse_args(argv)

    resume_text = read_text(args.resume)
    posting_text = read_text(args.posting)
    lexicon = load_lexicon(args.lexicon)

    result = score(resume_text, posting_text, lexicon)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_report(result))

    return 0


if __name__ == "__main__":
    sys.exit(main())
