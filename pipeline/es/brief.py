"""Fail-closed brief boundary: deterministic statistics plus cited prose.

The validator checks provenance and numeric boundaries. The truth of a free
narrative claim still requires a person's comparison with the cited source.
"""
import math
import re
from datetime import date
from .privacy import privacy_matches

CITATION=re.compile(r"#(\d+)")
UNSUPPORTED=re.compile(r"결함|원인(?:은|이|으로)|때문|초래|리콜(?:될|된다|됩니다)|확정|원인\s*규명")
CATEGORY_KO={"fire_thermal":"화재·과열","electrical_failure":"전기 계통","loss_of_power":"동력 상실","engine_stall":"엔진 정지","engine_failure":"엔진 파손","airbag":"에어백","brakes":"제동","steering":"조향","seat_belt":"안전벨트","fuel_leak":"연료 누출","transmission":"변속기","lighting":"등화","suspension":"현가장치","structure_body":"차체","tires_wheels":"타이어·휠","other":"기타"}

def cited_ids(text):
    return list(dict.fromkeys(CITATION.findall(text or "")))

def statistics_sentence(grp,category,expected_counts):
    n=expected_counts["n"]
    baseline=float(expected_counts["baseline"])
    ratio=float(expected_counts["ratio"])
    streak=expected_counts["streak"]
    if not (math.isfinite(baseline) and baseline>0 and math.isfinite(ratio)) or abs(ratio-n/baseline)>1e-9:
        raise ValueError("invalid_statistics")
    return f"{grp.replace('|',' ')} · {CATEGORY_KO[category]} 신고 {n}건(평소 월 {baseline:.1f}건, {ratio:.1f}배, 연속 경보 {streak}개월)."

def validate_brief(text,evidence,complaints,*,grp,category,month,expected_counts,excluded=()):
    if not isinstance(text,str) or not text.strip():
        raise ValueError("empty_brief")
    if privacy_matches(text):
        raise ValueError("sensitive_brief")
    if UNSUPPORTED.search(text):
        raise ValueError("unsupported_conclusion")
    ids=cited_ids(text)
    if not ids or not set(ids).issubset(set(evidence["ids"])):
        raise ValueError("outside_evidence_citation")
    if set(ids)&set(excluded):
        raise ValueError("excluded_evidence_citation")
    for odino in evidence["ids"]:
        item=complaints.get(odino)
        if item is None or item["grp"]!=grp or item["month"]!=month or category not in item["categories"]:
            raise ValueError("evidence_scope_mismatch")
        received=date.fromisoformat(item["ldate"])
        boundary=date.fromisoformat(month)
        if (received.year,received.month)>(boundary.year,boundary.month):
            raise ValueError("future_evidence")
        if (received.year,received.month)!=(boundary.year,boundary.month):
            raise ValueError("outside_month_evidence")
    if evidence["n"]!=len(set(evidence["ids"])) or expected_counts["n"]!=evidence["n"]:
        raise ValueError("evidence_count_mismatch")
    statistics=statistics_sentence(grp,category,expected_counts)
    if not text.startswith(statistics):
        raise ValueError("statistics_template_mismatch")
    narrative=text[len(statistics):].strip()
    without_ids=CITATION.sub("",narrative)
    # A number belonging to another metric can never justify a prose claim.
    if re.search(r"\d",without_ids) or re.search(r"(?<![가-힣])(?:한|두|세|네|다섯|여섯|일곱|여덟|아홉|열)\s*(?:명|건|배|개월|일)",without_ids):
        raise ValueError("unsupported_narrative_number")
    if not narrative or not cited_ids(narrative):
        raise ValueError("uncited_narrative")
    return text.strip()

def compose_brief(narrative,evidence,complaints,*,grp,category,month,expected_counts,excluded=()):
    text=statistics_sentence(grp,category,expected_counts)+" "+narrative.strip()
    return validate_brief(text,evidence,complaints,grp=grp,category=category,month=month,expected_counts=expected_counts,excluded=excluded)
